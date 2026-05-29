"""Tests for knowledge-base tip enrichment with manual example positions."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import scan_advisor as adv
from game_engine import fen_to_board, get_legal_moves
from strategy import enrich_tips as et

_KB = Path(__file__).resolve().parent.parent / "knowledge_base.json"


def _tips() -> list[dict]:
    return json.loads(_KB.read_text())["tips"]


def test_some_tips_have_examples():
    enriched = [t for t in _tips() if t.get("example_positions")]
    assert len(enriched) > 20


def test_every_example_actually_matches_its_tip():
    """Each attached position must genuinely satisfy the tip's pattern —
    same feature rules the in-game advisor uses to surface the tip."""
    for tip in _tips():
        for ex in tip.get("example_positions", []):
            st = fen_to_board(ex["fen"])
            counts = adv._piece_counts(st)
            phase = adv._phase(adv._total_pieces(counts))
            feats = adv._board_features(
                st, counts, phase, [], None, len(get_legal_moves(st))
            )
            assert et._matches(tip, feats, phase), f"{tip['id']} / {ex['id']}"


def test_examples_carry_provenance_and_dedup():
    for tip in _tips():
        exs = tip.get("example_positions", [])
        fens = [e["fen"] for e in exs]
        assert len(fens) == len(set(fens)), tip["id"]  # de-duplicated
        for e in exs:
            assert {"id", "source", "page", "number", "fen", "kind"} <= set(e)


def test_enrichment_is_idempotent_and_fresh():
    """A fresh dry-run must reproduce exactly the committed examples."""
    report = et.enrich(dry_run=True)
    committed = {
        t["id"]: len(t["example_positions"])
        for t in _tips()
        if t.get("example_positions")
    }
    assert report == committed, (
        "knowledge_base.json examples are stale — re-run "
        "`python -m strategy.enrich_tips`"
    )
