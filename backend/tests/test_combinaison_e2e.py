"""End-to-end check that ``combinaison_N_temps`` motifs fire on real
international-draughts positions from the Débutant manual.

The mock-engine tests in dilf (``test_motif_combinaisons_generiques``)
exercise the chain-walking bookkeeping but bypass FMJD geometry and
the Scan PV format. This module closes that gap: it pipes hand-curated
Dubois positions through the real :class:`GameEngineAdapter` (which
wraps the production ``game_engine`` with full FMJD rules) and the
real :func:`assemble_verdict`. The Scan call is short-circuited by
feeding the assembler a hand-built PV — what matters here is whether
the detectors fire on real geometry, not whether Scan finds the line.

If any of these tests goes red, the combinaison family has regressed
on the production path used by ``/api/pedagogy/analyze-game``.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pedagogy.game import Move
from pedagogy.verdicts.assembler import assemble_verdict

from manuels.fixtures_debutant import (
    BEG_CH03_001,
    BEG_CH03_002,
    BEG_CH04_001,
)
from pedagogy.engine_adapter import GameEngineAdapter  # noqa: E402


# ---------------------------------------------------------------------------
# Test cases — each tuple is (fixture, played_move, pv, expected_motif)
#
# ``pv`` mirrors what Scan emits in the Hub protocol (full-path "axbxc"
# for captures, "a-b" for quiet moves; documented in
# backend/scan_engine.py:171).
# ---------------------------------------------------------------------------

CASES = [
    pytest.param(
        BEG_CH03_001,
        Move(path=(26, 21)),
        ["26-21", "17x26x37x28", "43x32x23x14x3"],
        "combinaison_2_temps",
        id="BEG_CH03_001-contact-prise-rafle",
    ),
    pytest.param(
        BEG_CH03_002,
        Move(path=(28, 22)),
        ["28-22", "17x28", "32x23x14x5"],
        "combinaison_2_temps",
        id="BEG_CH03_002-coup-de-mazette",
    ),
    pytest.param(
        BEG_CH04_001,
        Move(path=(37, 31)),
        # 3-temps "collage": sac → forced rafle → quiet sac → forced rafle → final rafle
        ["37-31", "26x37x28x17", "39-34", "21x32x43", "34x23x12x3x14x5"],
        "combinaison_3_temps",
        id="BEG_CH04_001-collage-3-temps",
    ),
]


@pytest.mark.parametrize("fixture, played, pv, expected_motif", CASES)
def test_combinaison_fires_on_real_dubois_position(
    fixture, played: Move, pv: list[str], expected_motif: str,
) -> None:
    adapter = GameEngineAdapter()
    state_before = fixture.state
    state_after = adapter.apply_move(state_before, played)

    verdict = assemble_verdict(
        state_before,
        played,
        state_after,
        score_before=0.0,
        score_after=0.0,
        best_move=played,
        best_pv=pv,
        half_move_number=1,
        engine=adapter,
    )

    slugs = [m.motif for m in verdict.motifs]
    assert expected_motif in slugs, (
        f"{fixture.id}: expected {expected_motif} in detected motifs, got {slugs}. "
        f"This means dilf's combinaison detectors no longer fire on the production path."
    )


def test_sacrifice_and_combinaison_co_fire() -> None:
    """The "sacrifice never fires alone" regression check.

    Until commit 9fccc1f on dilf develop, the strict
    ``len(opp_legal) == 1`` guard in ``_walk_forced_chain`` killed
    combinaison detection on essentially every real-game combination,
    leaving ``sacrifice`` as the sole motif on the sacrifice move.
    Now both fire together: ``sacrifice`` captures the immediate
    material loss + score recovery, and ``combinaison_2_temps``
    captures the structural property (forced chain with material
    gain).
    """
    adapter = GameEngineAdapter()
    state_before = BEG_CH03_002.state
    played = Move(path=(28, 22))
    pv = ["28-22", "17x28", "32x23x14x5"]
    state_after = adapter.apply_move(state_before, played)

    verdict = assemble_verdict(
        state_before, played, state_after,
        score_before=0.0, score_after=0.0,
        best_move=played, best_pv=pv,
        half_move_number=1, engine=adapter,
    )

    slugs = {m.motif for m in verdict.motifs}
    assert "sacrifice" in slugs, f"sacrifice should still fire — got {slugs}"
    assert "combinaison_2_temps" in slugs, (
        f"combinaison_2_temps should co-fire with sacrifice — got {slugs}. "
        f"If only sacrifice fires here, the FMJD relaxation has regressed."
    )
