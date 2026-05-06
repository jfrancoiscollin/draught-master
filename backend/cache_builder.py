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
    pdn_texts: list[str] | None = None,
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
        # ── Phase 1: collect unique FENs ──────────────────────────────────────
        all_fens: set[str] = set()
        total_games = 0

        if pdn_texts:
            # Data already downloaded by the browser — parse PDN or NDJSON
            from lidraughts_fetcher import _ndjson_to_pdn
            _set(message=f"Analyse de {len(pdn_texts)} lot(s) de parties…")
            for i, raw in enumerate(pdn_texts):
                if not raw or not raw.strip():
                    continue
                # Auto-detect format: NDJSON lines start with '{', PDN with '['
                pdn_bulk = raw if raw.lstrip().startswith('[') else _ndjson_to_pdn(raw)
                games = split_pdn_games(pdn_bulk)
                logger.info("cache_builder: lot %d → %d games (format=%s)",
                            i, len(games), "PDN" if raw.lstrip().startswith('[') else "NDJSON")
                total_games += len(games)
                _set(fetched_games=total_games,
                     message=f"{total_games} parties reçues ({i+1}/{len(pdn_texts)} joueurs)…")
                for game_pdn in games:
                    try:
                        fens = extract_fens(game_pdn, max_moves)
                        all_fens.update(fens)
                    except Exception:
                        _inc("errors")
        else:
            # Fetch from Lidraughts server-side (may fail due to allowlist)
            _set(message="Téléchargement des parties depuis Lidraughts…")
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
            if len(all_fens) == 0:
                _set(status="error", message="Aucune partie trouvée — vérifiez les pseudos ou réessayez.")
            else:
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


# ── Incremental ingest (one player at a time) ─────────────────────────────────

_pending_fens: set = set()
_pending_games: int = 0


def ingest_raw(raw: str, max_moves: int) -> dict:
    """Parse one player's raw PDN or NDJSON text. Adds extracted FENs to the
    pending pool. Returns {games: N, fens_added: N, format: str}."""
    global _pending_fens, _pending_games
    from lidraughts_fetcher import _ndjson_to_pdn, split_pdn_games

    if not raw or not raw.strip():
        return {"games": 0, "fens_added": 0, "format": "empty"}

    stripped = raw.lstrip()
    if stripped.startswith('{'):
        fmt = "ndjson"
        pdn_bulk = _ndjson_to_pdn(raw)
    else:
        fmt = "pdn"
        pdn_bulk = raw

    games = split_pdn_games(pdn_bulk)
    new_fens: set = set()
    for game_pdn in games:
        try:
            fens = extract_fens(game_pdn, max_moves)
            new_fens.update(fens)
        except Exception:
            pass

    with _lock:
        before = len(_pending_fens)
        _pending_fens.update(new_fens)
        _pending_games += len(games)
        added = len(_pending_fens) - before

    logger.info("ingest_raw: fmt=%s games=%d fens=%d added=%d pending_total=%d",
                fmt, len(games), len(new_fens), added, len(_pending_fens))
    return {"games": len(games), "fens_added": added, "format": fmt}


def start_eval(ms_per_position: int) -> bool:
    """Start Scan evaluation on all pending FENs. Returns False if already running."""
    global _pending_fens, _pending_games

    with _lock:
        if _job.get("status") == "running":
            return False
        fens = list(_pending_fens)
        games = _pending_games
        _pending_fens = set()
        _pending_games = 0

    if not fens:
        return False

    t = threading.Thread(
        target=_run_eval_only,
        args=(fens, games, ms_per_position),
        daemon=True,
    )
    t.start()
    return True


def _run_eval_only(fens: list, total_games: int, ms_per_position: int) -> None:
    """Background thread: evaluate a list of FENs with Scan."""
    from opening_eval_db import lookup as db_lookup, store as db_store
    from scan_engine import _get_engine, _build_pos
    from game_engine import fen_to_board

    _set(status="running",
         fetched_games=total_games,
         unique_positions=len(fens),
         computed=0, skipped=0, errors=0,
         message=f"{total_games} parties · {len(fens)} positions à évaluer…")

    new_fens = [f for f in fens if not db_lookup(f)]
    skipped = len(fens) - len(new_fens)
    _set(skipped=skipped, total_to_compute=len(new_fens),
         message=f"{len(fens)} positions · {len(new_fens)} à calculer · {skipped} en cache")

    if not new_fens:
        _set(status="done", message="Toutes les positions étaient déjà en cache !")
        return

    engine = _get_engine()
    if engine is None:
        _set(status="error", message="Moteur Scan non disponible")
        return

    movetime_s = ms_per_position / 1000.0
    batch: list[dict] = []
    for i, fen in enumerate(new_fens):
        try:
            state = fen_to_board(fen)
            hub_pos = _build_pos(state)
            ev = engine.evaluate_pos(hub_pos, movetime_s) or {"score": 0, "bestMove": None}
            batch.append({"fen": fen, "score": ev["score"], "bestMove": ev["bestMove"]})
        except Exception as exc:
            logger.warning("Eval error pos %d: %s", i, exc)
            _inc("errors")
        _set(computed=i + 1, message=f"Évaluation {i+1}/{len(new_fens)}…")
        if len(batch) >= 50:
            db_store(batch)
            batch.clear()

    if batch:
        db_store(batch)

    from opening_eval_db import size as cache_size
    _set(status="done",
         message=f"Terminé ! {len(new_fens)} nouvelles positions ajoutées. Cache : {cache_size()} total.")
    logger.info("_run_eval_only: done, %d new entries", len(new_fens))


def start(
    usernames: list[str],
    max_games_per_user: int = 100,
    max_moves: int = 12,
    ms_per_position: int = 5000,
    pdn_texts: list[str] | None = None,
) -> bool:
    """Start the background build job. Returns False if already running."""
    with _lock:
        if _job.get("status") == "running":
            return False

    t = threading.Thread(
        target=run_build,
        args=(usernames, max_games_per_user, max_moves, ms_per_position, pdn_texts),
        daemon=True,
    )
    t.start()
    return True
