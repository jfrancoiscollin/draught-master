"""In-process state for live games — the J3 game-state machine.

A :class:`LiveGameSession` holds the engine state of one in-progress
game between two users. The :class:`LiveGameManager` singleton owns
all sessions plus the reverse index ``user_id -> game_id`` used to
route incoming WebSocket frames to the right session.

Design choices:
  - State is in-memory. A redeploy drops every live game; the
    cadrage (``docs/PVP_LIVE.md``) calls that out as a v1 accepted risk.
  - Each move triggers an atomic DB UPDATE on the ``games`` row so
    a game in progress can be **resumed** from the DB if we ever
    swap the in-memory dict for a Redis-backed one in v2.
  - All mutations of the dicts are awaited under a single
    :class:`asyncio.Lock` — concurrency is low enough that finer-grained
    locking buys nothing.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import aiosqlite

# game_engine lives in backend/ which is on sys.path in production; tests
# add the same. Absolute import keeps us decoupled from the package layout
# that pedagogy / live use for their relative imports.
from game_engine import (
    GameState,
    Move,
    apply_move,
    game_result,
    get_legal_moves,
    initial_state,
    move_to_pdn,
)

_log = logging.getLogger(__name__)


@dataclass
class LiveGameSession:
    """Holds the engine state for one in-progress live game.

    ``status`` mirrors the value written to ``games.status`` so consumers
    don't have to re-parse the DB to know whether the game is still
    playable. ``result`` is one of ``'white' | 'black' | 'draw' | None``
    matching :func:`game_engine.game_result`.
    """

    game_id: str
    white_user_id: int
    black_user_id: int
    state: GameState
    status: str = "in_progress"          # | 'finished' | 'abandoned_white' | 'abandoned_black'
    result: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)

    def user_side(self, user_id: int) -> Optional[str]:
        """``'white'`` / ``'black'`` / ``None`` (spectator — shouldn't happen)."""
        if user_id == self.white_user_id:
            return "white"
        if user_id == self.black_user_id:
            return "black"
        return None

    def to_dict(self) -> dict[str, Any]:
        """Wire-shape used in game_started / game_ended frames."""
        return {
            "game_id":        self.game_id,
            "white_user_id":  self.white_user_id,
            "black_user_id":  self.black_user_id,
            "turn":           self.state.turn,
            "status":         self.status,
            "result":         self.result,
            "pdn":            _state_to_pdn(self.state),
        }


def _state_to_pdn(state: GameState) -> str:
    """Re-emit the move_history as a flat PDN string ('32-28 19-23 ...').

    Matches the format the `/api/pedagogy/analyze-game` endpoint already
    consumes, so finished live games are analysable through the same
    pipeline without conversion."""
    out: list[str] = []
    for i, m in enumerate(state.move_history):
        if i % 2 == 0:
            out.append(f"{i // 2 + 1}. {move_to_pdn(m)}")
        else:
            out[-1] += f" {move_to_pdn(m)}"
    return " ".join(out)


def _assign_colors(
    challenger_id: int, opponent_id: int, preferred_color: str
) -> tuple[int, int]:
    """Return ``(white_user_id, black_user_id)`` honoring the challenger's
    preference. ``random`` uses a fresh CSPRNG draw per game."""
    if preferred_color == "white":
        return challenger_id, opponent_id
    if preferred_color == "black":
        return opponent_id, challenger_id
    # random
    if secrets.choice([True, False]):
        return challenger_id, opponent_id
    return opponent_id, challenger_id


class LiveGameManager:
    """Singleton owning every in-progress :class:`LiveGameSession`."""

    def __init__(self) -> None:
        self._games: dict[str, LiveGameSession] = {}
        # Reverse index so a WS frame from user X can be routed to the
        # right session without a linear scan. A user can be in at most
        # one live game at a time in v1.
        self._user_to_game: dict[int, str] = {}
        # J4 — pending forfeit asyncio.Tasks keyed by user_id. Scheduled
        # when a player drops their WebSocket in the middle of an
        # in_progress game; cancelled if they reconnect inside the
        # grace window. The task body itself is owned by api.py — the
        # manager just holds the handle for cancellation.
        self._forfeit_tasks: dict[int, "asyncio.Task[Any]"] = {}
        self._lock = asyncio.Lock()

    async def start_game(
        self,
        conn: aiosqlite.Connection,
        *,
        challenger_id: int,
        opponent_id: int,
        preferred_color: str,
    ) -> LiveGameSession:
        """Persist a new ``kind='live'`` Game row, register the session,
        and return it. Caller is responsible for linking the challenge
        to ``session.game_id`` and broadcasting ``game_started``."""
        white_id, black_id = _assign_colors(challenger_id, opponent_id, preferred_color)
        gid = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO games
                (id, kind, white_user_id, black_user_id, turn, status,
                 user_id, user_side, pdn, date)
            VALUES (?, 'live', ?, ?, 'white', 'in_progress',
                    ?, 'white', '', CURRENT_TIMESTAMP)
            """,
            (gid, white_id, black_id, challenger_id),
        )
        await conn.commit()
        session = LiveGameSession(
            game_id=gid,
            white_user_id=white_id,
            black_user_id=black_id,
            state=initial_state(),
        )
        async with self._lock:
            self._games[gid] = session
            self._user_to_game[white_id] = gid
            self._user_to_game[black_id] = gid
        return session

    def session_for(self, user_id: int) -> Optional[LiveGameSession]:
        gid = self._user_to_game.get(user_id)
        if gid is None:
            return None
        return self._games.get(gid)

    def session_by_id(self, game_id: str) -> Optional[LiveGameSession]:
        return self._games.get(game_id)

    async def apply_move(
        self,
        conn: aiosqlite.Connection,
        *,
        user_id: int,
        move_pdn: str,
    ) -> dict[str, Any]:
        """Validate and apply one half-move for ``user_id``.

        Returns a result dict suitable for shipping back over WS:
          - ``{"ok": True, "move": "32-28", "session": {...}}`` on success
          - ``{"ok": False, "reason": "..."}`` on any validation error

        The reason taxonomy is stable: ``not_in_game`` / ``not_your_turn``
        / ``game_over`` / ``unknown_move`` / ``illegal_move``. Frontends
        can branch on these strings without parsing free text.
        """
        sess = self.session_for(user_id)
        if sess is None:
            return {"ok": False, "reason": "not_in_game"}
        if sess.status != "in_progress":
            return {"ok": False, "reason": "game_over"}
        side = sess.user_side(user_id)
        if side != sess.state.turn:
            return {"ok": False, "reason": "not_your_turn"}

        legal = get_legal_moves(sess.state)
        chosen = _find_move_by_pdn(move_pdn, legal)
        if chosen is None:
            # Distinguish "I don't recognise that notation" from "you
            # tried to play a move that exists but isn't legal here".
            # All non-matches end up here today because matching is
            # done by string equality on the PDN form; refine once we
            # accept multiple input formats.
            return {"ok": False, "reason": "unknown_move"}

        sess.state = apply_move(sess.state, chosen)

        # Game-over check: if the side now to move has no legal moves,
        # the previous mover wins (mate/blockage).
        result = game_result(sess.state)
        if result is not None:
            sess.result = result
            sess.status = "finished"

        # Persist incrementally so a crash / redeploy doesn't lose the
        # game. pdn is rebuilt from the in-memory history — cheaper than
        # an append because game_engine emits canonical notation per move.
        await conn.execute(
            """
            UPDATE games SET pdn = ?, turn = ?, status = ?
             WHERE id = ?
            """,
            (_state_to_pdn(sess.state), sess.state.turn, sess.status, sess.game_id),
        )
        await conn.commit()

        return {
            "ok": True,
            "move": move_to_pdn(chosen),
            "by": side,
            "session": sess.to_dict(),
        }

    async def resign(
        self, conn: aiosqlite.Connection, *, user_id: int,
    ) -> dict[str, Any]:
        """Mark the resigning side as abandoned. Returns the standard
        result dict; reasons mirror :meth:`apply_move`."""
        sess = self.session_for(user_id)
        if sess is None:
            return {"ok": False, "reason": "not_in_game"}
        if sess.status != "in_progress":
            return {"ok": False, "reason": "game_over"}
        side = sess.user_side(user_id)
        sess.status = f"abandoned_{side}"
        sess.result = "black" if side == "white" else "white"
        await conn.execute(
            "UPDATE games SET status = ? WHERE id = ?",
            (sess.status, sess.game_id),
        )
        await conn.commit()
        return {"ok": True, "by": side, "session": sess.to_dict()}

    async def evict(self, game_id: str) -> None:
        """Drop a finished session from memory. Tests + future cleanup
        loop call this; production-side, end-of-game eviction is handled
        by J4 (grace period) so we don't hold onto state forever."""
        async with self._lock:
            sess = self._games.pop(game_id, None)
            if sess is None:
                return
            for uid in (sess.white_user_id, sess.black_user_id):
                if self._user_to_game.get(uid) == game_id:
                    del self._user_to_game[uid]

    # ── Forfeit task tracking (J4) ──────────────────────────────────────

    def schedule_forfeit(self, user_id: int, task: "asyncio.Task[Any]") -> None:
        """Register a pending forfeit timer for ``user_id``.

        If a previous timer was already in flight (e.g. the user
        reconnected then re-disconnected before the first timer
        expired), it's cancelled here so only one timer can race to
        completion per user.
        """
        old = self._forfeit_tasks.get(user_id)
        if old is not None and not old.done():
            old.cancel()
        self._forfeit_tasks[user_id] = task

    def cancel_forfeit(self, user_id: int) -> bool:
        """Cancel the pending forfeit for ``user_id`` if any.

        Returns True iff a timer was actually cancelled — the caller
        uses that to decide whether to push an ``opponent_reconnected``
        notification or stay quiet (first connect of the session).
        """
        task = self._forfeit_tasks.pop(user_id, None)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    def clear_forfeit(self, user_id: int) -> None:
        """Drop the timer handle without cancelling — used after the
        timer body has run to completion and marked the user
        abandoned, so the dict doesn't keep a stale reference."""
        self._forfeit_tasks.pop(user_id, None)

    async def reset(self) -> None:
        """Test-only — wipes all sessions. Production should never call
        this; survives only because pytest fixtures need it."""
        async with self._lock:
            self._games.clear()
            self._user_to_game.clear()
            for task in self._forfeit_tasks.values():
                if not task.done():
                    task.cancel()
            self._forfeit_tasks.clear()


def _find_move_by_pdn(pdn: str, legal_moves: list[Move]) -> Optional[Move]:
    """Match ``pdn`` (e.g. ``'32-28'`` or ``'31x22'``) against the engine's
    canonical notation. Stripped of any leading ``K`` so we tolerate the
    king-prefix variant some PDN dialects use."""
    pdn_norm = pdn.strip().lstrip("K")
    for move in legal_moves:
        if move_to_pdn(move) == pdn_norm:
            return move
    return None


# Module-level singleton.
manager = LiveGameManager()
