"""Pin the metadata-reapply contract of `sync_dilf_corpus.py`.

The sync script resets our local manuel copy to dilf's content and then
re-injects ``<!-- pedagogy-* -->`` annotations under each chapter
header. If that step ever silently broke, the lesson↔motif links would
disappear from the frontend — these tests catch that regression.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "sync_dilf_corpus.py"
_spec = importlib.util.spec_from_file_location("sync_dilf_corpus", _SCRIPT)
sync_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync_mod)


def test_reapply_inserts_metadata_after_chapter_header():
    md = (
        "## Chapitre 5 — L'envoi à dame\n"
        "\n"
        "Body of chapter 5.\n"
    )
    out = sync_mod.reapply_metadata(md)
    lines = out.split("\n")
    assert lines[0] == "## Chapitre 5 — L'envoi à dame"
    assert lines[1] == "<!-- pedagogy-motifs: envoi_a_dame -->"


def test_reapply_replaces_existing_metadata_not_stacks():
    md = (
        "## Chapitre 5 — L'envoi à dame\n"
        "<!-- pedagogy-motifs: stale_slug -->\n"
        "Body.\n"
    )
    out = sync_mod.reapply_metadata(md)
    assert "stale_slug" not in out
    assert out.count("<!-- pedagogy-motifs: envoi_a_dame -->") == 1


def test_reapply_skips_chapters_without_mapping():
    md = (
        "## Chapitre 1 — La notation des cases\n"
        "\n"
        "Body of chapter 1.\n"
    )
    out = sync_mod.reapply_metadata(md)
    assert "<!-- pedagogy-" not in out


def test_reapply_handles_chapter_7_double_block():
    md = "## Chapitre 7 — Les temps de repos créés par une attaque\n\nBody.\n"
    out = sync_mod.reapply_metadata(md)
    assert "<!-- pedagogy-motifs: sacrifice -->" in out
    assert "<!-- pedagogy-weaknesses: holes -->" in out


def test_reapply_preserves_existing_correct_metadata_idempotent():
    """Running sync twice in a row must not drift the file."""
    md = (
        "## Chapitre 5 — L'envoi à dame\n"
        "<!-- pedagogy-motifs: envoi_a_dame -->\n"
        "Body.\n"
    )
    once = sync_mod.reapply_metadata(md)
    twice = sync_mod.reapply_metadata(once)
    assert once == twice
