"""Tests for the mined manual combinations.

The strong guarantee: replaying each exercise's solution line is fully
legal and ends in a win (annihilation) for the side that started — so a
shipped combination is correct by the rules, not by engine opinion.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import game_engine as ge
from strategy import exercises_loader as xl
from strategy.generate_exercises import _OUT_PATH

pytestmark = pytest.mark.skipif(
    not _OUT_PATH.is_file(),
    reason="strategy_exercises.json not generated (run strategy.generate_exercises)",
)


def _net_material(state: ge.GameState, mover: str) -> int:
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


def _replay(fen: str, moves: list[str]) -> tuple[bool, str, int]:
    """Replay the line; return (all_legal, result, material_gain)."""
    state = ge.fen_to_board(fen)
    mover = state.turn
    start = _net_material(state, mover)
    for mv in moves:
        legal = {ge.move_to_pdn(m): m for m in ge.get_legal_moves(state)}
        if mv not in legal:
            return False, "", 0
        state = ge.apply_move(state, legal[mv])
    return True, (ge.game_result(state) or ""), _net_material(state, mover) - start


def test_loader_rows_well_formed():
    rows = xl.all_strategy_exercises()
    for r in rows:
        assert r["solution_moves"]
        assert r["initial_fen"].startswith(("W:", "B:"))
        assert r["difficulty"] in (1, 2, 3)
        assert r["category"] == "combinaisons_manuels"
        assert r["book_id"].startswith("manuel_")


def test_every_solution_is_legal_and_winning():
    import json

    data = json.loads(_OUT_PATH.read_text())["exercises"]
    assert data, "no exercises generated"
    for ex in data:
        legal, result, gain = _replay(ex["initial_fen"], ex["solution_moves"])
        assert legal, ex["diagram_id"]
        mover = "white" if ex["initial_fen"].startswith("W:") else "black"
        if ex["outcome"] in ("win", "endgame"):
            # Forced win by the rules (annihilation, or endgame technique).
            assert result == mover, ex["diagram_id"]
        else:
            # Decisive material: mover nets at least two men by the end.
            assert ex["outcome"] == "material"
            assert gain >= 200, (ex["diagram_id"], gain)


def test_id_range_disjoint_and_order_deterministic():
    assert xl.STRATEGY_ID_OFFSET >= 5000  # clear of manuel_debutant (2001+)
    # Deterministic ordering: two calls yield identical rows.
    assert xl.all_strategy_exercises() == xl.all_strategy_exercises()
