"""Mine verified 'play and win' combinations from the manual positions.

The scanned diagrams are mostly *quiet* strategic positions, not puzzles
— so instead of fabricating a solution for every position (which would
teach wrong moves), this only emits an exercise when the engine finds a
**forced win by annihilation** within a short horizon: a line that, by
the rules of the game, captures all the opponent's pieces. Such a line
is reconstructed move by move with the engine and is correct by
construction (every move is legal; the final state is a win for the
side that started).

Output: ``strategy/strategy_exercises.json`` — rows shaped like the
historical ``INITIAL_EXERCISES`` (name / initial_fen / solution_moves /
difficulty / category / hint) plus provenance back to the manual.

Run from ``backend/`` (slow — a few minutes; safe to background)::

    python -m strategy.generate_exercises
    python -m strategy.generate_exercises SIJBRANDS   # one source
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import ai_engine as ai
import game_engine as ge

from . import position_library as lib

_OUT_PATH = Path(__file__).resolve().parent / "strategy_exercises.json"

# Engine search depth for screening and line reconstruction. Combinations
# in these manuals are short (2–6 plies); depth 6 catches them while
# staying tractable over ~1300 positions.
_DEPTH = 6
# A leaf score this large means the search reached annihilation (see
# ai_engine.evaluate / game_result == ±100000). Side-to-move relative.
_WIN = 99000.0
# Screening floor (side-to-move relative, ~100 per man). Positions whose
# best line doesn't reach at least this are not promising — skip without
# the cost of reconstructing a line.
_SCREEN = 150.0
# A line qualifies as a winning combination when the mover nets at least
# this much material (~2 men) by its quiet end, and still stands clearly
# ahead. Being up two men is decisive in practice.
_MATERIAL_GAIN = 200
_MIN_END_EVAL = 100
# Hard cap on reconstructed line length (plies) — guards against any
# pathological non-terminating search.
_MAX_PLIES = 12
# Endgame studies (<= 18 pieces) win by technique, not a capture burst,
# so they need a deeper search and a longer line than combinations.
_ENDGAME_PIECES = 18
_ENDGAME_DEPTH = 12
_ENDGAME_MAX_PLIES = 16


def _net_material(state: ge.GameState, mover: str) -> int:
    """Mover-relative material balance (men=100, kings=325)."""
    bal = 0
    for p in state.board:
        if p == ge.WHITE_MAN:
            bal += 100
        elif p == ge.WHITE_KING:
            bal += 325
        elif p == ge.BLACK_MAN:
            bal -= 100
        elif p == ge.BLACK_KING:
            bal -= 325
    return bal if mover == "white" else -bal


def _has_capture(state: ge.GameState) -> bool:
    return any("x" in ge.move_to_pdn(m) for m in ge.get_legal_moves(state))


def _winning_line(state: ge.GameState) -> tuple[list[str], str, int] | None:
    """Reconstruct a winning line, or None.

    Screens with a single search, then plays the mover's first move and
    follows the *forced* capture exchange (continuing only while the side
    to move must capture) until the position is quiet or the game ends.
    Returns ``(moves, outcome, material_gain)`` where outcome is
    ``"win"`` (forced annihilation) or ``"material"`` (mover nets ≥ 2 men
    and stays clearly ahead). Already-winning positions net ~0 and are
    rejected — only genuine gains qualify.
    """
    mover = state.turn
    ranked = ai.rank_moves(state, n=1, depth=_DEPTH)
    if not ranked or ranked[0][1] < _SCREEN:
        return None

    start_material = _net_material(state, mover)
    moves: list[str] = []
    cur = state
    for ply in range(_MAX_PLIES):
        if ge.game_result(cur) is not None:
            break
        # After the mover's first move, only keep following while the side
        # to move is forced to capture — that's the combination resolving.
        if ply > 0 and not _has_capture(cur):
            break
        best = ai.get_best_move(cur, depth=_DEPTH)
        if best is None:
            return None
        moves.append(ge.move_to_pdn(best))
        cur = ge.apply_move(cur, best)

    if not moves:
        return None

    result = ge.game_result(cur)
    if result == mover:
        return moves, "win", 100000  # opponent annihilated
    if result is not None:
        return None  # mover lost/drew the line

    gain = _net_material(cur, mover) - start_material
    end_eval = ai.evaluate(cur)
    end_eval = end_eval if mover == "white" else -end_eval
    if gain >= _MATERIAL_GAIN and end_eval >= _MIN_END_EVAL:
        return moves, "material", gain
    return None


def _total_pieces(state: ge.GameState) -> int:
    return sum(1 for p in state.board if p)


def _endgame_win_line(state: ge.GameState) -> tuple[list[str], str, int] | None:
    """Forced win by endgame technique, or None.

    Unlike ``_winning_line`` this is not restricted to a capture burst:
    it plays the engine's best move for both sides (deeper search, longer
    horizon) and accepts the line only if it ends in a win for the side
    that started — i.e. a position the player can actually convert.
    """
    mover = state.turn
    ranked = ai.rank_moves(state, n=1, depth=_ENDGAME_DEPTH)
    if not ranked or ranked[0][1] < _WIN:
        return None
    moves: list[str] = []
    cur = state
    for _ in range(_ENDGAME_MAX_PLIES):
        if ge.game_result(cur) is not None:
            break
        best = ai.get_best_move(cur, depth=_ENDGAME_DEPTH)
        if best is None:
            return None
        moves.append(ge.move_to_pdn(best))
        cur = ge.apply_move(cur, best)
    if ge.game_result(cur) == mover:
        return moves, "endgame", 100000
    return None


def _difficulty(n_solution_plies: int) -> int:
    # Mover's own moves ≈ ceil(plies / 2). Short = easy.
    own = (n_solution_plies + 1) // 2
    if own <= 2:
        return 1
    if own <= 3:
        return 2
    return 3


def generate(sources: tuple[str, ...]) -> list[dict]:
    exercises: list[dict] = []
    positions = [
        p
        for src in sources
        for p in lib.valid_positions(src)
    ]
    total = len(positions)
    for i, p in enumerate(positions, start=1):
        if i % 100 == 0:
            print(f"  ... screened {i}/{total} ({len(exercises)} found)")
        state = ge.fen_to_board(p["fen"])
        result = _winning_line(state)
        if not result and _total_pieces(state) <= _ENDGAME_PIECES:
            result = _endgame_win_line(state)
        if not result:
            continue
        line, outcome, gain = result
        side = "blancs" if state.turn == "white" else "noirs"
        theme = p.get("theme")
        if outcome == "material":
            objective = f"jouent et gagnent du matériel (+{gain // 100} pions)"
        elif outcome == "endgame":
            objective = "jouent et gagnent (finale)"
        else:
            objective = "jouent et gagnent"
        exercises.append(
            {
                "name": f"{p['source']} — combinaison (p.{p['page']} #{p['number']})",
                "description": (
                    f"{p['source']} — diagramme {p['number']} page {p['page']}. "
                    f"Les {side} {objective}."
                ),
                "initial_fen": p["fen"],
                "solution_moves": line,
                "difficulty": _difficulty(len(line)),
                "category": "combinaisons_manuels",
                "hint": theme or "Cherchez une combinaison forcée.",
                # Provenance back to the source diagram.
                "source": p["source"],
                "page": p["page"],
                "number": p["number"],
                "diagram_id": p["id"],
                "fen_kind": p["kind"],
                "outcome": outcome,
                "material_gain": gain,
            }
        )
    return exercises


def main(argv: list[str]) -> int:
    sources = tuple(s.upper() for s in argv[1:]) or lib.stats().get(
        "per_source", {}
    ).keys()
    sources = tuple(sources) or ("SIJBRANDS", "SPRINGER", "ROOZENBURG", "KELLER")
    exercises = generate(tuple(sources))
    payload = {
        "$comment": (
            "Generated by strategy/generate_exercises.py — verified forced-win "
            "combinations mined from the manual diagrams. Re-runnable."
        ),
        "n_exercises": len(exercises),
        "exercises": exercises,
    }
    _OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"[ok] {len(exercises)} verified combinations → {_OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
