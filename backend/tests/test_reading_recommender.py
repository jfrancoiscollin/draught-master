"""The reading recommender maps a game's verdicts to strategic prose.

Pure aggregation + deterministic topic mapping + centroid retrieval (no
embedding at query time). Uses small duck-typed stand-ins for the dilf
verdict/feature objects so the test doesn't need a Scan run.
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from strategy.reading_recommender import recommend_reading


def _features(side: str, holes=0, isolated=0, backward=0):
    kw = {
        f"holes_{side}": list(range(holes)),
        f"isolated_pawns_{side}": list(range(isolated)),
        f"backward_pawns_{side}": list(range(backward)),
    }
    # the other side's fields default to empty
    other = "black" if side == "white" else "white"
    for stem in ("holes", "isolated_pawns", "backward_pawns"):
        kw.setdefault(f"{stem}_{other}", [])
    return SimpleNamespace(**kw)


def _verdict(side, verdict, phase, features=None, motifs=()):
    return SimpleNamespace(
        side=side, verdict=verdict, phase=phase,
        features_after=features, motifs=list(motifs),
    )


def test_endgame_mistakes_recommend_finales():
    # White user blunders repeatedly in the endgame.
    verdicts = [
        _verdict("white", "blunder", "endgame"),
        _verdict("white", "mistake", "endgame"),
        _verdict("black", "blunder", "endgame"),  # opponent — ignored
        _verdict("white", "best", "opening"),
    ]
    recos = recommend_reading(verdicts, user_side="white", lang="fr")
    assert recos, "expected at least one recommendation"
    assert recos[0]["topic_key"] == "finales"
    assert recos[0]["reason"]
    # Centroid retrieval returns representative passages with a source.
    assert recos[0]["passages"]
    for p in recos[0]["passages"]:
        assert p["source"] == p["source"].upper()
        assert isinstance(p["score"], float)
        assert p["text"].strip()


def test_structural_and_tactical_signals_add_topics():
    motif = SimpleNamespace(role="missed", motif="x")
    verdicts = [
        _verdict("white", "mistake", "middlegame",
                 features=_features("white", holes=2, isolated=1), motifs=[motif]),
        _verdict("white", "blunder", "middlegame",
                 features=_features("white", holes=2), motifs=[motif]),
    ]
    recos = recommend_reading(verdicts, user_side="white", lang="fr")
    keys = {r["topic_key"] for r in recos}
    # Middlegame cost -> plans; structural weakness -> principes; missed
    # tactics -> pieges. At most max_reco of them, deduped.
    assert "plans" in keys
    assert keys & {"principes", "pieges"}
    assert len(recos) <= 3


def test_clean_game_has_no_recommendations():
    verdicts = [
        _verdict("white", "best", "opening"),
        _verdict("white", "excellent", "middlegame"),
        _verdict("white", "good", "endgame"),
    ]
    assert recommend_reading(verdicts, user_side="white", lang="fr") == []


def test_reco_passages_are_deduped_topics():
    verdicts = [_verdict("white", "blunder", "endgame") for _ in range(5)]
    recos = recommend_reading(verdicts, user_side="white", lang="en")
    keys = [r["topic_key"] for r in recos]
    assert len(keys) == len(set(keys))
