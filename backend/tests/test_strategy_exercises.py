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


def _replay_wins(fen: str, moves: list[str]) -> bool:
    state = ge.fen_to_board(fen)
    mover = state.turn
    for mv in moves:
        legal = {ge.move_to_pdn(m): m for m in ge.get_legal_moves(state)}
        if mv not in legal:
            return False
        state = ge.apply_move(state, legal[mv])
    return ge.game_result(state) == mover


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
        assert _replay_wins(ex["initial_fen"], ex["solution_moves"]), ex["diagram_id"]


def test_id_range_disjoint_and_order_deterministic():
    assert xl.STRATEGY_ID_OFFSET >= 5000  # clear of manuel_debutant (2001+)
    # Deterministic ordering: two calls yield identical rows.
    assert xl.all_strategy_exercises() == xl.all_strategy_exercises()
