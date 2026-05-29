"""Tests for the consolidated strategic position library.

Covers the runtime accessor (``position_library``) and a freshness
check that the committed JSON matches what the builder produces from the
source diagram files — so a stale library fails CI instead of silently
serving outdated positions.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import game_engine as ge
from strategy import build_position_library as build
from strategy import position_library as lib


def test_library_not_empty():
    positions = lib.all_positions()
    assert len(positions) > 1000  # ~1369 diagrams across four manuals
    assert len(lib.valid_positions()) > 1000


def test_every_valid_fen_parses_and_has_legal_move():
    for p in lib.valid_positions():
        st = ge.fen_to_board(p["fen"])
        assert ge.get_legal_moves(st), p["id"]
        assert 1 <= p["n_white"] <= 20
        assert 1 <= p["n_black"] <= 20


def test_source_filter_and_lookup():
    sij = lib.valid_positions("SIJBRANDS")
    assert sij and all(p["source"] == "SIJBRANDS" for p in sij)
    first = sij[0]
    got = lib.get_position("SIJBRANDS", first["page"], first["number"])
    assert got is not None and got["id"] == first["id"]


def test_themes_group_positions():
    grouped = lib.themes("SIJBRANDS")
    assert grouped
    # Every grouped position carries the theme it's filed under.
    for theme, items in grouped.items():
        assert items
        assert all(p["theme"] == theme for p in items)


def test_human_provenance_takes_precedence():
    # At least the hand-verified SIJBRANDS FENs are tagged "human".
    assert any(p["kind"] == "human" for p in lib.all_positions())


def test_committed_library_is_fresh():
    """The committed JSON must equal a fresh rebuild from the sources."""
    rebuilt = build.build()
    committed = lib._payload()
    # ``generated_on`` is a timestamp; compare the substantive payload.
    assert rebuilt["positions"] == committed["positions"], (
        "position_library.json is stale — re-run "
        "`python -m strategy.build_position_library`"
    )
    assert rebuilt["stats"] == committed["stats"]
