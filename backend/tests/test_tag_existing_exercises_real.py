"""Real-detector path for ``tag_existing_exercises._detect_tags``.

The existing ``test_tag_existing_exercises.py`` monkeypatches
``_detect_tags`` so it never exercises the real geometry. This file
fills that gap: feed a hand-curated Dubois position with its known
solution and assert that capture-based motifs actually fire.

Closes the verification side of the "missing apply_move /
parse_move_notation helpers" item tracked in INTEROP.md / dilf
ROADMAP — the helpers exist (at ``pedagogy.notation.dubois`` and via
``GameEngineAdapter`` respectively), and this test pins the
end-to-end path so the doc gap won't reopen.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pedagogy.game import state_to_fen  # noqa: E402

from manuels.fixtures_debutant import BEG_CH03_001, BEG_CH03_002  # noqa: E402
from pedagogy.scripts.tag_existing_exercises import _detect_tags  # noqa: E402


def test_detect_tags_fires_capture_based_motifs() -> None:
    """The classical 2-temps "contact-prise-rafle" should produce a tag
    set that includes at least ``sacrifice`` (white's quiet sac on 21
    loses 3 pieces on black's forced rafle) — proving the engine_adapter
    apply_move path resolves on real geometry."""
    fen = state_to_fen(BEG_CH03_001.state)
    moves = ["26-21", "17x28", "43x3"]

    tags = _detect_tags(fen, moves)

    assert "sacrifice" in tags, (
        f"Expected `sacrifice` in {tags}. If empty, the script's "
        f"apply_move path is broken end-to-end; if other slugs only, "
        f"the sacrifice detector regressed."
    )


def test_detect_tags_picks_up_rafle_endgame_motifs() -> None:
    """The coup de mazette ends on a 3-capture rafle (32x23x14x5) that
    crosses the great diagonal and promotes. We expect at least one
    capture-based slug (sacrifice from the quiet 28-22 sac, plus one
    of envoi_a_dame / coup_express depending on the geometry)."""
    fen = state_to_fen(BEG_CH03_002.state)
    moves = ["28-22", "17x28", "32x5"]

    tags = _detect_tags(fen, moves)

    assert tags, "Expected at least one motif to fire — got an empty set."
    # The 32→23→14→5 rafle lands on white's promotion row (5 is
    # in 1..5); envoi_a_dame should fire whenever a capture chain
    # ends with a man landing on its promotion row.
    assert "envoi_a_dame" in tags or "sacrifice" in tags, (
        f"Expected at least one of envoi_a_dame / sacrifice — got {tags}."
    )
