"""Smoke test: every dilf symbol consumed by draught-master is importable.

If this test goes red on a PR, dilf has broken the contract documented
in ``backend/pedagogy/INTEROP.md`` (and ``INTEROP.md`` at the root of
``jfrancoiscollin/dilf``). The two-step dance in INTEROP.md explains
how to coordinate the fix.

Each test imports the symbols of one dilf module and asserts the
minimum surface this repo relies on. The point is **not** to retest
dilf's behaviour — only its public surface — so assertions stay
shallow (class/callable/signature checks).
"""
from __future__ import annotations

import dataclasses
import inspect


# ---------------------------------------------------------------------------
# pedagogy.types — dataclasses persisted into SQLite + reconstructed
# ---------------------------------------------------------------------------


def test_pedagogy_types_importable() -> None:
    from pedagogy.types import (
        Features,
        GameAnalysis,
        MotifMatch,
        MoveVerdict,
        Phase,
        UserProfile,
        Verdict,
    )

    for cls in (Features, GameAnalysis, MotifMatch, MoveVerdict, UserProfile):
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} is no longer a dataclass"
    assert issubclass(Phase, str)
    assert issubclass(Verdict, str)


def test_verdict_string_values_are_stable() -> None:
    """move_verdicts.verdict stores the raw string. Renaming = data
    migration grade breaking change."""
    from pedagogy.types import Verdict

    for required in ("brilliant", "best", "excellent", "good",
                     "inaccuracy", "mistake", "blunder", "forced", "book"):
        assert any(v.value == required for v in Verdict), \
            f"Verdict.{required} disappeared upstream"


def test_phase_string_values_are_stable() -> None:
    from pedagogy.types import Phase

    for required in ("opening", "middlegame", "endgame"):
        assert any(p.value == required for p in Phase), \
            f"Phase.{required} disappeared upstream"


# ---------------------------------------------------------------------------
# pedagogy.game — primitives + parser
# ---------------------------------------------------------------------------


def test_pedagogy_game_importable() -> None:
    from pedagogy.game import GameState, Move, parse_fen

    assert dataclasses.is_dataclass(GameState)
    assert dataclasses.is_dataclass(Move)
    assert callable(parse_fen)


def test_move_has_path_and_captures() -> None:
    """tag_existing_exercises constructs Move(path=..., captures=...).
    Both fields must remain."""
    from pedagogy.game import Move

    names = {f.name for f in dataclasses.fields(Move)}
    assert "path" in names
    assert "captures" in names


# ---------------------------------------------------------------------------
# pedagogy.motifs — registry
# ---------------------------------------------------------------------------


def test_all_detectors_registry() -> None:
    from pedagogy.motifs import ALL_DETECTORS

    assert isinstance(ALL_DETECTORS, list)
    assert len(ALL_DETECTORS) > 0
    for cls in ALL_DETECTORS:
        instance = cls()
        assert hasattr(instance, "name")
        assert callable(getattr(instance, "detect", None))


# ---------------------------------------------------------------------------
# pedagogy.explanations — pipeline + BookRAG
# ---------------------------------------------------------------------------


def test_explain_verdict_is_async_with_expected_kwargs() -> None:
    """api.py's /explain-move handler awaits this with these kwargs."""
    from pedagogy.explanations import explain_verdict

    assert inspect.iscoroutinefunction(explain_verdict), \
        "explain_verdict must remain async (api.py awaits it)"
    params = inspect.signature(explain_verdict).parameters
    for required in ("mode", "book_rag", "lang"):
        assert required in params, f"explain_verdict lost the {required} kwarg"


def test_book_rag_from_directory_factory_exists() -> None:
    """main.py builds the shared BookRAG singleton via
    BookRAG.from_directory(corpus_path) at app startup."""
    from pedagogy.explanations import BookRAG

    assert hasattr(BookRAG, "from_directory"), (
        "BookRAG.from_directory missing — main.py app startup will crash. "
        "Either restore the classmethod on dilf or stop using it here."
    )


# ---------------------------------------------------------------------------
# pedagogy.profile — aggregator + recommender
# ---------------------------------------------------------------------------


def test_aggregate_user_profile_callable() -> None:
    from pedagogy.profile.aggregator import aggregate_user_profile

    assert callable(aggregate_user_profile)


def test_recommend_exercises_callable() -> None:
    from pedagogy.profile.recommender import recommend_exercises

    assert callable(recommend_exercises)


# ---------------------------------------------------------------------------
# pedagogy.verdicts — assembler
# ---------------------------------------------------------------------------


def test_assemble_verdict_callable() -> None:
    """api.py's /analyze-game handler calls this per half-move."""
    from pedagogy.verdicts.assembler import assemble_verdict

    assert callable(assemble_verdict)


# ---------------------------------------------------------------------------
# pedagogy.protocols — typing.Protocol for the Scan engine adapter
# ---------------------------------------------------------------------------


def test_engine_protocol_class_exists() -> None:
    """engine_adapter.GameEngineAdapter satisfies EngineProtocol."""
    from pedagogy.protocols import EngineProtocol

    assert inspect.isclass(EngineProtocol)
