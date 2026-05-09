"""
Background exercise verification job.

Checks every stored exercise solution for:
  1. Legality — is the stored first move legal in the given FEN?
  2. Scan agreement — does Scan's best move match our stored first move?
     (only when Scan is available)

Follows the same singleton/threading pattern as cache_builder.py.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from game_engine import (
    fen_to_board, get_legal_moves,
    EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING,
)


# ── State ─────────────────────────────────────────────────────────────────────

_lock = threading.Lock()
_state: Dict[str, Any] = {
    "status": "idle",       # idle | running | done
    "total": 0,
    "done": 0,
    "ok": 0,
    "illegal": 0,
    "scan_mismatch": 0,
    "issues": [],
    "scan_available": False,
    "error": None,
}


def get_status() -> Dict[str, Any]:
    with _lock:
        return dict(_state)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_move(mv: str) -> tuple[int, int, str]:
    """Return (from_sq, to_sq, separator) for a stored move."""
    sep = 'x' if 'x' in mv else '-'
    parts = mv.split(sep)
    try:
        return int(parts[0]), int(parts[-1]), sep
    except (ValueError, IndexError):
        return -1, -1, sep


def _check_legality(fen: str, sol: List[str]) -> Dict[str, Any]:
    if not sol:
        return {"legal": False, "source_occupied": False, "legal_moves": []}

    state = fen_to_board(fen)
    legal = get_legal_moves(state)
    legal_strs = {
        f"{m.path[0]}{'x' if m.captures else '-'}{m.path[-1]}"
        for m in legal
    }

    frm, to, sep = _normalise_move(sol[0])
    normalised = f"{frm}{sep}{to}" if frm > 0 else sol[0]

    source_occupied = False
    if 1 <= frm <= 50:
        piece = state.board[frm]
        if state.turn == 'white':
            source_occupied = piece in (WHITE_MAN, WHITE_KING)
        else:
            source_occupied = piece in (BLACK_MAN, BLACK_KING)

    return {
        "legal": normalised in legal_strs,
        "source_occupied": source_occupied,
        "legal_moves": sorted(legal_strs),
    }


def _fen_to_hub(fen: str) -> str:
    """Convert FEN to 51-char Scan Hub position string."""
    _PIECE = {
        EMPTY: 'e', WHITE_MAN: 'w', WHITE_KING: 'W',
        BLACK_MAN: 'b', BLACK_KING: 'B',
    }
    state = fen_to_board(fen)
    turn = 'W' if state.turn == 'white' else 'B'
    return turn + ''.join(_PIECE[state.board[sq]] for sq in range(1, 51))


# ── Background worker ─────────────────────────────────────────────────────────

def _run(exercises: List[Dict[str, Any]], use_scan: bool, movetime: float) -> None:
    engine = None
    scan_ok = False

    if use_scan:
        try:
            from scan_engine import _get_engine
            engine = _get_engine(use_book=False)
            scan_ok = engine is not None and engine.alive()
        except Exception:
            scan_ok = False

    with _lock:
        _state.update({
            "status": "running",
            "total": len(exercises),
            "done": 0,
            "ok": 0,
            "illegal": 0,
            "scan_mismatch": 0,
            "issues": [],
            "scan_available": scan_ok,
            "error": None,
        })

    issues: List[Dict[str, Any]] = []
    ok = illegal = mismatch = 0

    for ex in exercises:
        name = ex.get("name", "?")
        fen = ex.get("initial_fen", "")
        sol = ex.get("solution_moves", [])

        leg = _check_legality(fen, sol)
        issue: Optional[Dict[str, Any]] = None

        if not leg["legal"]:
            illegal += 1
            reason = (
                "case source vide" if not leg["source_occupied"]
                else "coup absent de la liste légale"
            )
            issue = {
                "name": name,
                "fen": fen,
                "stored_move": sol[0] if sol else "",
                "status": "ILLEGAL",
                "reason": reason,
                "legal_moves": leg["legal_moves"][:8],
                "scan_move": None,
            }
        elif scan_ok and engine and sol:
            hub = _fen_to_hub(fen)
            scan_move = engine.best_move(hub, movetime)
            if scan_move:
                stored_pair = _normalise_move(sol[0])[:2]
                scan_pair = _normalise_move(scan_move)[:2]
                if stored_pair != scan_pair:
                    mismatch += 1
                    issue = {
                        "name": name,
                        "fen": fen,
                        "stored_move": sol[0],
                        "status": "SCAN_MISMATCH",
                        "reason": f"Scan joue {scan_move!r}",
                        "legal_moves": leg["legal_moves"][:8],
                        "scan_move": scan_move,
                    }
                else:
                    ok += 1
            else:
                ok += 1
        else:
            ok += 1

        if issue:
            issues.append(issue)

        with _lock:
            _state["done"] += 1
            _state["ok"] = ok
            _state["illegal"] = illegal
            _state["scan_mismatch"] = mismatch

    with _lock:
        _state["status"] = "done"
        _state["issues"] = issues


def start(use_scan: bool = False, movetime: float = 0.3) -> bool:
    """Start verification job in background thread.  Returns False if already running."""
    with _lock:
        if _state["status"] == "running":
            return False

    from db.sens_du_jeu_exercises import SENS_DU_JEU_EXERCISES
    t = threading.Thread(
        target=_run,
        args=(list(SENS_DU_JEU_EXERCISES), use_scan, movetime),
        daemon=True,
    )
    t.start()
    return True
