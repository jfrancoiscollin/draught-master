"""FastAPI router for the live PvP module.

J1: REST queue for challenges (create / list / respond / cancel).
J2: WebSocket transport + presence-driven challenge push notifications.

The in-flight game state machine + move broadcasting land on J3 and
will live alongside this router. See ``docs/PVP_LIVE.md``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

try:
    from auth import _decode_token, current_user  # absolute when backend/ is on sys.path
except ImportError:
    from ..auth import _decode_token, current_user  # type: ignore[assignment]

from . import storage
from .models import (
    ChallengeCreateRequest,
    ChallengeOut,
    ChallengeRespondRequest,
    PendingChallengesResponse,
)
from .presence import manager

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/live", tags=["live"])

# How long the client has to send the auth frame after the WS upgrade
# before we close the socket. Real clients send it immediately; this
# is a defence against half-open sockets, not a UX timer.
_AUTH_TIMEOUT_S = 10.0


def _db_path() -> str:
    """Same lookup as pedagogy/api.py — keeps the live module
    decoupled from the rest of the import graph."""
    try:
        from db.config import DB_PATH  # absolute (backend/ on sys.path)
        return DB_PATH
    except ImportError:
        from ..db.config import DB_PATH  # type: ignore[assignment]
        return DB_PATH


def _row_to_out(row: dict[str, Any]) -> ChallengeOut:
    return ChallengeOut(**row)


# ---------------------------------------------------------------------------
# POST /api/live/challenge
# ---------------------------------------------------------------------------


@router.post("/challenge", response_model=ChallengeOut)
async def create_challenge(
    req: ChallengeCreateRequest,
    user: Any = Depends(current_user),
) -> ChallengeOut:
    """Issue a challenge to ``opponent_username``.

    Rejects:
      - opponent doesn't exist (404)
      - opponent is the caller themself (422)
      - caller already has a pending challenge to the same opponent (409)
    """
    challenger_id = int(user["id"])

    async with aiosqlite.connect(_db_path()) as conn:
        opp = await storage.find_user_by_username(conn, req.opponent_username)
        if opp is None:
            raise HTTPException(404, f"Aucun joueur ne s'appelle {req.opponent_username!r}")
        if opp["id"] == challenger_id:
            raise HTTPException(422, "On ne peut pas se défier soi-même")

        # Prevent duplicate-pending: spamming "Défier" would otherwise
        # let one user clutter another's inbox.
        dup_cur = await conn.execute(
            """
            SELECT id FROM live_challenges
             WHERE challenger_id = ? AND opponent_id = ? AND status = 'pending'
             LIMIT 1
            """,
            (challenger_id, opp["id"]),
        )
        if await dup_cur.fetchone() is not None:
            raise HTTPException(409, "Tu as déjà un défi en attente vers ce joueur")

        cid = await storage.insert_challenge(
            conn,
            challenger_id=challenger_id,
            opponent_id=opp["id"],
            preferred_color=req.preferred_color,
        )
        row = await storage.fetch_challenge(conn, cid)
        assert row is not None

    # Push to the opponent's WebSocket if they're online. Best-effort:
    # if not connected, they'll fetch the pending list on next login.
    await manager.send_to(opp["id"], {
        "type": "challenge_received",
        "challenge": _row_to_out(row).model_dump(),
    })
    return _row_to_out(row)


# ---------------------------------------------------------------------------
# GET /api/live/challenges/pending
# ---------------------------------------------------------------------------


@router.get("/challenges/pending", response_model=PendingChallengesResponse)
async def list_pending_challenges(
    user: Any = Depends(current_user),
) -> PendingChallengesResponse:
    """Bootstrap query for the live lobby UI: pending challenges I
    received + pending challenges I sent. Pruned to status='pending';
    accepted / declined / expired ones drop off the list automatically."""
    async with aiosqlite.connect(_db_path()) as conn:
        received, sent = await storage.fetch_pending_for_user(conn, int(user["id"]))
    return PendingChallengesResponse(
        received=[_row_to_out(r) for r in received],
        sent=[_row_to_out(r) for r in sent],
    )


# ---------------------------------------------------------------------------
# POST /api/live/challenge/{id}/respond
# ---------------------------------------------------------------------------


@router.post("/challenge/{challenge_id}/respond", response_model=ChallengeOut)
async def respond_challenge(
    challenge_id: str,
    req: ChallengeRespondRequest,
    user: Any = Depends(current_user),
) -> ChallengeOut:
    """Accept or decline a pending challenge.

    Only the opponent can respond. Acceptance transitions the challenge
    to 'accepted' and (in a later day) spawns a live game; for now we
    just stamp the status — the game-creation handshake comes with the
    WebSocket layer on J3. The `game_id` field of the response stays
    null until then.
    """
    user_id = int(user["id"])

    async with aiosqlite.connect(_db_path()) as conn:
        row = await storage.fetch_challenge(conn, challenge_id)
        if row is None:
            raise HTTPException(404, "Défi introuvable")
        if row["opponent_id"] != user_id:
            # Don't leak whether the challenge exists at all — same
            # response shape as a missing one. (Soft policy: 403 is
            # also fine, but 404 hides the existence.)
            raise HTTPException(404, "Défi introuvable")
        if row["status"] != "pending":
            raise HTTPException(409, f"Ce défi a déjà été {row['status']}")

        new_status = "accepted" if req.accept else "declined"
        await storage.update_status(conn, challenge_id, new_status)
        refreshed = await storage.fetch_challenge(conn, challenge_id)
        assert refreshed is not None

    # Notify the challenger of the outcome so they don't sit watching
    # a stale "en attente" indicator. Opponent doesn't need a push —
    # they triggered the action and already see the result.
    await manager.send_to(refreshed["challenger_id"], {
        "type": "challenge_resolved",
        "challenge": _row_to_out(refreshed).model_dump(),
    })
    return _row_to_out(refreshed)


# ---------------------------------------------------------------------------
# POST /api/live/challenge/{id}/cancel
# ---------------------------------------------------------------------------


@router.post("/challenge/{challenge_id}/cancel", response_model=ChallengeOut)
async def cancel_challenge(
    challenge_id: str,
    user: Any = Depends(current_user),
) -> ChallengeOut:
    """Challenger withdraws a still-pending challenge. Mirror of
    /respond but reserved to the challenger; the opponent must use
    /respond with accept=false to decline."""
    user_id = int(user["id"])

    async with aiosqlite.connect(_db_path()) as conn:
        row = await storage.fetch_challenge(conn, challenge_id)
        if row is None:
            raise HTTPException(404, "Défi introuvable")
        if row["challenger_id"] != user_id:
            raise HTTPException(404, "Défi introuvable")
        if row["status"] != "pending":
            raise HTTPException(409, f"Ce défi a déjà été {row['status']}")
        await storage.update_status(conn, challenge_id, "cancelled")
        refreshed = await storage.fetch_challenge(conn, challenge_id)
        assert refreshed is not None

    # Notify the opponent so they can drop the "Alice te défie" toast
    # without waiting for a refresh.
    await manager.send_to(refreshed["opponent_id"], {
        "type": "challenge_cancelled",
        "challenge": _row_to_out(refreshed).model_dump(),
    })
    return _row_to_out(refreshed)


# ---------------------------------------------------------------------------
# WS /api/live/ws
# ---------------------------------------------------------------------------


async def _authenticate_ws(ws: WebSocket) -> int | None:
    """Run the first-frame auth handshake.

    Returns the authenticated user_id on success, or ``None`` after
    closing the socket on any failure. We expect a single JSON frame
    of shape ``{"type": "auth", "token": "<jwt>"}`` within
    :data:`_AUTH_TIMEOUT_S` seconds of accepting the connection.

    Auth errors (missing frame, malformed shape, invalid/expired token)
    all close the socket with an explanatory frame first, so a
    misconfigured client sees a real error rather than a blank
    disconnect.
    """
    try:
        first = await asyncio.wait_for(ws.receive_json(), timeout=_AUTH_TIMEOUT_S)
    except (asyncio.TimeoutError, WebSocketDisconnect):
        await _safe_close(ws)
        return None
    except Exception as exc:  # noqa: BLE001 — payload could be anything
        _log.info("WS auth handshake malformed: %s", exc)
        await _safe_send(ws, {"type": "auth_error", "reason": "malformed auth frame"})
        await _safe_close(ws)
        return None

    if not isinstance(first, dict) or first.get("type") != "auth":
        await _safe_send(ws, {"type": "auth_error", "reason": "auth frame required"})
        await _safe_close(ws)
        return None
    token = first.get("token")
    if not isinstance(token, str) or not token:
        await _safe_send(ws, {"type": "auth_error", "reason": "token missing"})
        await _safe_close(ws)
        return None

    try:
        data = _decode_token(token)
        user_id = int(data["sub"])
    except Exception:  # noqa: BLE001 — _decode_token raises HTTPException
        await _safe_send(ws, {"type": "auth_error", "reason": "invalid or expired token"})
        await _safe_close(ws)
        return None
    return user_id


async def _safe_send(ws: WebSocket, msg: dict[str, Any]) -> None:
    """Best-effort JSON send; swallow connection errors so the
    handshake-error path never raises out of the WS handler."""
    try:
        await ws.send_json(msg)
    except Exception:  # noqa: BLE001
        pass


async def _safe_close(ws: WebSocket) -> None:
    try:
        await ws.close()
    except Exception:  # noqa: BLE001
        pass


@router.websocket("/ws")
async def live_ws(ws: WebSocket) -> None:
    """Single endpoint serving the entire live PvP channel.

    Lifecycle:
      1. Accept the connection.
      2. Wait for an ``{type: 'auth', token}`` frame within
         :data:`_AUTH_TIMEOUT_S`.
      3. On success: register in :data:`presence.manager`. If the user
         already had an open socket (other tab / device), kick it with
         a ``kicked_by_other_session`` frame — single connection per
         user is enforced.
      4. Send ``{type: 'auth_ok'}`` so the client knows it can start.
      5. Loop reading frames. Currently supported types: ``ping``
         (replies with ``pong``). Unknown types receive an ``error``
         frame and the loop continues — strict-mode would risk
         disconnecting clients that send forward-compatible message
         types in a future release.
      6. On disconnect / unhandled exception: deregister from the
         manager (only if our socket is still the registered one).
    """
    await ws.accept()
    user_id = await _authenticate_ws(ws)
    if user_id is None:
        return

    # Single connection per user. The kick frame buys the previous
    # client a chance to display a sensible message instead of a
    # bare close code.
    old = await manager.connect(user_id, ws)
    if old is not None:
        await _safe_send(old, {"type": "kicked_by_other_session"})
        await _safe_close(old)

    await _safe_send(ws, {"type": "auth_ok", "user_id": user_id})

    try:
        while True:
            msg = await ws.receive_json()
            if not isinstance(msg, dict):
                await _safe_send(ws, {"type": "error", "reason": "non-object frame"})
                continue
            t = msg.get("type")
            if t == "ping":
                await _safe_send(ws, {"type": "pong"})
            else:
                # Unknown / not-yet-implemented (move, resign, etc. come
                # with J3). Don't disconnect — forward-compat matters
                # once the frontend ships ahead of the backend.
                await _safe_send(ws, {"type": "error", "reason": f"unknown type {t!r}"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001 — last-resort guard
        _log.warning("WS handler crashed for user_id=%s: %s", user_id, exc)
    finally:
        await manager.disconnect(user_id, ws)
