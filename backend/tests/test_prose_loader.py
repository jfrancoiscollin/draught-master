"""Metadata parsing in `manuels/prose_loader.py`.

The narrative chips on the review board deep-link to chapters via
``<!-- pedagogy-motifs: ... -->`` and ``<!-- pedagogy-weaknesses: ... -->``
blocks placed in the manuel markdown. These tests pin the parser
contract (so a typo in a comment fails loud instead of silently
breaking the link) and the inverted-index helpers used by the
``/api/lessons/by-motif`` / ``/by-weakness`` endpoints.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_load_debutant_chapters_carries_metadata_fields():
    from manuels.prose_loader import load_debutant_chapters
    chapters = load_debutant_chapters()
    assert chapters, "manuel_debutant.md must produce at least one chapter"
    for ch in chapters.values():
        assert "motifs" in ch and isinstance(ch["motifs"], list)
        assert "weaknesses" in ch and isinstance(ch["weaknesses"], list)


def test_chapter_5_declares_envoi_a_dame():
    from manuels.prose_loader import load_debutant_chapters
    assert "envoi_a_dame" in load_debutant_chapters()["5"]["motifs"]


def test_chapter_6_declares_isolated_and_backward():
    from manuels.prose_loader import load_debutant_chapters
    weaknesses = load_debutant_chapters()["6"]["weaknesses"]
    assert "isolated" in weaknesses
    assert "backward" in weaknesses


def test_lessons_by_motif_returns_chapters_in_source_order():
    from manuels.prose_loader import lessons_by_motif
    idx = lessons_by_motif()
    # envoi_a_dame appears in chapter 4 and chapter 5, in that order.
    assert idx.get("envoi_a_dame") == ["4", "5"]
    assert idx.get("coup_napoleon") == ["13"]


def test_lessons_by_weakness_index():
    from manuels.prose_loader import lessons_by_weakness
    idx = lessons_by_weakness()
    # `holes` covered both by ch.7 and ch.8.
    assert idx.get("holes") == ["7", "8"]
    assert idx.get("isolated") == ["6"]


def test_unknown_motif_returns_empty():
    from manuels.prose_loader import lessons_by_motif
    assert lessons_by_motif().get("nope") is None


def test_metadata_block_does_not_pollute_diagrams():
    """The metadata comment lines must not be mistaken for fixture refs."""
    from manuels.prose_loader import load_debutant_chapters
    ch5 = load_debutant_chapters()["5"]
    for d in ch5["diagrams"]:
        assert not d["ref"].startswith("pedagogy")
