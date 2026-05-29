"""Legality gate over the consolidated position library.

A man can never sit on its own promotion row (it would already be a
king): a white man on squares 1-5 or a black man on 46-50 is a sure
detector misread. The library flags such positions invalid; this test
guarantees none ever leaks into the "valid" set the prose panel,
knowledge base and exercises draw from.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import game_engine as ge
from strategy import position_library as lib


def _illegal_men(fen: str) -> int:
    st = ge.fen_to_board(fen)
    return sum(1 for sq in range(1, 6) if st.board[sq] == ge.WHITE_MAN) + sum(
        1 for sq in range(46, 51) if st.board[sq] == ge.BLACK_MAN
    )


def test_no_valid_position_has_a_man_on_its_promotion_row():
    for p in lib.valid_positions():
        assert _illegal_men(p["fen"]) == 0, p["id"]


def test_illegal_men_field_present_and_consistent():
    for p in lib.all_positions():
        if not p.get("fen"):
            continue
        assert "illegal_men" in p, p["id"]
        assert p["illegal_men"] == _illegal_men(p["fen"]), p["id"]
        if p["illegal_men"] > 0:
            assert p["valid"] is False, p["id"]
