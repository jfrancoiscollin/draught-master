"""Background job: fetch Lidraughts games, extract opening positions, evaluate with Scan."""
from __future__ import annotations
import logging
import re
import threading
import time
from typing import Optional

from game_engine import (
    initial_state, apply_move, board_to_fen, get_legal_moves, move_to_pdn,
)

logger = logging.getLogger(__name__)

# ── Job state (shared, protected by _lock) ────────────────────────────────────

_lock = threading.Lock()
_job: dict = {
    "status": "idle",   # idle | running | done | error
    "message": "",
    "fetched_games": 0,
    "unique_positions": 0,
    "computed": 0,
    "skipped": 0,
    "total_to_compute": 0,
    "errors": 0,
}


def get_status() -> dict:
    with _lock:
        return dict(_job)


def _set(**kwargs) -> None:
    with _lock:
        _job.update(kwargs)


def _inc(key: str, by: int = 1) -> None:
    with _lock:
        _job[key] = _job.get(key, 0) + by


# ── PDN helpers (self-contained, no circular imports) ────────────────────────

_RESULT_TOKENS = {'1-0', '0-1', '1/2-1/2', '*', '2-0', '0-2', '1-1'}


def _find_move(pdn_str: str, legal_moves) -> Optional[object]:
    """Match PDN notation to a legal Move object."""
    pdn_norm = pdn_str.strip()
    for m in legal_moves:
        if move_to_pdn(m) == pdn_norm:
            return m
    try:
        if 'x' in pdn_norm:
            parts = [int(p) for p in pdn_norm.split('x') if p]
        elif '-' in pdn_norm:
            parts = [int(p) for p in pdn_norm.split('-') if p]
        else:
            return None
        start, end = parts[0], parts[-1]
    except (ValueError, IndexError):
        return None
    for m in legal_moves:
        if m.path[0] == start and m.path[-1] == end:
            return m
    return None


def extract_fens(pdn_text: str, max_moves: int) -> list[str]:
    """Replay a single-game PDN and return FENs for positions 0..max_moves."""
    text = re.sub(r'\[.*?\]', '', pdn_text, flags=re.DOTALL)
    text = re.sub(r'\{[^}]*\}', '', text)
    text = re.sub(r';[^\n]*', '', text)

    tokens: list[str] = []
    for tok in text.split():
        if re.match(r'^\d+\.+$', tok):
            continue
        if tok in _RESULT_TOKENS:
            continue
        if re.match(r'^\d+[-x]\d', tok):
            tokens.append(tok)

    if not tokens:
        return []

    state = initial_state()
    fens = [board_to_fen(state)]
    for tok in tokens[:max_moves]:
        legal = get_legal_moves(state)
        move = _find_move(tok, legal)
        if move is None:
            break
        state = apply_move(state, move)
        fens.append(board_to_fen(state))
    return fens


# ── Background task ────────────────────────────────────────────────────────────

def run_build(
    usernames: list[str],
    max_games_per_user: int,
    max_moves: int,
    ms_per_position: int,
) -> None:
    """Entry point for the background thread."""
    from lidraughts_fetcher import fetch_user_games_pdn, split_pdn_games
    from opening_eval_db import lookup as db_lookup, store as db_store
    from scan_engine import _get_engine, _build_pos
    from game_engine import fen_to_board

    _set(status="running", message="Démarrage…",
         fetched_games=0, unique_positions=0, computed=0,
         skipped=0, total_to_compute=0, errors=0)

    movetime_s = ms_per_position / 1000.0

    try:
        # ── Phase 1: collect unique FENs from all users ────────────────────
        _set(message="Téléchargement des parties depuis Lidraughts…")
        all_fens: set[str] = set()
        total_games = 0

        for i, username in enumerate(usernames):
            pdn_bulk = fetch_user_games_pdn(username.strip(), max_games_per_user)
            if not pdn_bulk:
                logger.warning("No games fetched for user '%s'", username)
                _inc("errors")
                continue
            games = split_pdn_games(pdn_bulk)
            total_games += len(games)
            _set(fetched_games=total_games,
                 message=f"{total_games} parties chargées ({i+1}/{len(usernames)} joueurs)…")

            for game_pdn in games:
                try:
                    fens = extract_fens(game_pdn, max_moves)
                    all_fens.update(fens)
                except Exception:
                    _inc("errors")

            # Be polite to Lidraughts API between users
            if i < len(usernames) - 1:
                time.sleep(2)

        # ── Phase 2: filter already-cached positions ───────────────────────
        new_fens = [f for f in all_fens if not db_lookup(f)]
        _set(
            unique_positions=len(all_fens),
            skipped=len(all_fens) - len(new_fens),
            total_to_compute=len(new_fens),
            message=f"{len(all_fens)} positions uniques · {len(new_fens)} à calculer · {len(all_fens)-len(new_fens)} déjà en cache",
        )
        logger.info("cache_builder: %d unique FENs, %d new to compute", len(all_fens), len(new_fens))

        if not new_fens:
            _set(status="done", message="Toutes les positions étaient déjà en cache !")
            return

        # ── Phase 3: evaluate with Scan ────────────────────────────────────
        engine = _get_engine()
        if engine is None:
            _set(status="error", message="Moteur Scan non disponible")
            return

        batch: list[dict] = []
        for i, fen in enumerate(new_fens):
            try:
                state = fen_to_board(fen)
                hub_pos = _build_pos(state)
                ev = engine.evaluate_pos(hub_pos, movetime_s) or {"score": 0, "bestMove": None}
                batch.append({"fen": fen, "score": ev["score"], "bestMove": ev["bestMove"]})
            except Exception as exc:
                logger.warning("Eval error for pos %d: %s", i, exc)
                _inc("errors")

            _set(computed=i + 1,
                 message=f"Évaluation {i+1}/{len(new_fens)} positions…")

            # Flush to disk every 50 entries
            if len(batch) >= 50:
                db_store(batch)
                batch.clear()

        if batch:
            db_store(batch)

        total_in_cache = len(all_fens)
        _set(
            status="done",
            message=f"Terminé ! {len(new_fens)} nouvelles positions · {total_in_cache} au total en cache.",
        )
        logger.info("cache_builder: done, %d new entries added", len(new_fens))

    except Exception as exc:
        logger.exception("cache_builder fatal error")
        _set(status="error", message=f"Erreur : {exc}")


def start(
    usernames: list[str],
    max_games_per_user: int = 100,
    max_moves: int = 12,
    ms_per_position: int = 5000,
) -> bool:
    """Start the background build job. Returns False if already running."""
    with _lock:
        if _job.get("status") == "running":
            return False

    t = threading.Thread(
        target=run_build,
        args=(usernames, max_games_per_user, max_moves, ms_per_position),
        daemon=True,
    )
    t.start()
    return True
