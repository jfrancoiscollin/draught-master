"""Tests for /api/strategy/* — backend RAG over dilf's prose corpus.

The strategy module wires `pedagogy.prose.retrieval` (from dilf) into
two routes :

- ``GET /api/strategy/topics`` enumerates the curated topic buttons
- ``GET /api/strategy/search?topic=<key>&top_k=<n>`` returns the
  top-K passages most similar to the topic's centroid.

These tests assume the bundled dilf package ships embedding sidecars
(installed via ``[tool.setuptools.package-data]``). If the sidecars
are missing, every topic would be dormant and ``search`` would 503 —
which we cover with ``test_dormant_topic_returns_503`` via a forced
empty filter.
"""
from __future__ import annotations

import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from strategy.api import router
from strategy.topics import TOPICS, topic_centroid


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_list_topics_returns_all_curated_buttons(client: TestClient) -> None:
    r = client.get("/api/strategy/topics")
    assert r.status_code == 200
    payload = r.json()
    keys = {t["key"] for t in payload}
    expected = {t.key for t in TOPICS}
    assert keys == expected, f"topic keys drifted: {keys ^ expected}"


def test_topics_carry_required_fields(client: TestClient) -> None:
    """Each topic must expose label_fr, label_en, description_fr,
    and an ``available`` flag the frontend uses to disable empty buttons."""
    r = client.get("/api/strategy/topics")
    for t in r.json():
        assert {"key", "label_fr", "label_en", "description_fr", "available"} <= set(t)
        assert isinstance(t["available"], bool)


def test_search_unknown_topic_404s(client: TestClient) -> None:
    r = client.get("/api/strategy/search", params={"topic": "banana", "top_k": 3})
    assert r.status_code == 404
    assert "banana" in r.json()["detail"]


def test_search_respects_top_k(client: TestClient) -> None:
    r = client.get("/api/strategy/search", params={"topic": "roozenburg", "top_k": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["topic_key"] == "roozenburg"
    assert body["top_k"] == 5
    assert len(body["passages"]) <= 5


def test_search_passages_are_sourced(client: TestClient) -> None:
    """Each returned passage must carry the metadata the frontend needs
    to render a citation card (source code, book slug, page number)."""
    r = client.get("/api/strategy/search", params={"topic": "roozenburg", "top_k": 3})
    assert r.status_code == 200
    for p in r.json()["passages"]:
        assert p["passage_id"]
        assert p["source"] == p["source"].upper()
        assert p["book"]
        assert isinstance(p["page"], int) and p["page"] >= 1
        assert isinstance(p["score"], float)
        assert isinstance(p["text"], str) and p["text"].strip()


def test_search_results_sorted_by_score_descending(client: TestClient) -> None:
    r = client.get("/api/strategy/search", params={"topic": "classique", "top_k": 5})
    passages = r.json()["passages"]
    scores = [p["score"] for p in passages]
    assert scores == sorted(scores, reverse=True), (
        f"results not sorted by score desc: {scores}"
    )


def test_search_source_filter_applied(client: TestClient) -> None:
    """A topic with a source filter must only return passages from that
    source. Catches regressions where the centroid is computed correctly
    but the search ignores the filter."""
    r = client.get("/api/strategy/search", params={"topic": "roozenburg", "top_k": 10})
    sources = {p["source"] for p in r.json()["passages"]}
    assert sources == {"ROOZENBURG"}, (
        f"expected only ROOZENBURG passages, got {sources}"
    )


def test_top_k_clamped_to_corpus_size(client: TestClient) -> None:
    """top_k=50 on a small filtered shard returns at most the shard's size."""
    r = client.get("/api/strategy/search", params={"topic": "keller", "top_k": 50})
    assert r.status_code == 200
    body = r.json()
    # KELLER has 289 passages — 50 returned is fine. Just enforce the
    # contract that we never exceed top_k.
    assert len(body["passages"]) <= 50


def test_centroid_is_unit_norm() -> None:
    """Internal sanity: centroid normalization must hold so cosine
    similarity in search_with_vector behaves as expected."""
    import numpy as np

    for topic in TOPICS:
        c = topic_centroid(topic.key)
        if c is None:
            continue
        norm = float(np.linalg.norm(c))
        assert abs(norm - 1.0) < 1e-5, f"{topic.key}: centroid norm = {norm}"


@pytest.mark.parametrize(
    "source,page",
    [
        ("SIJBRANDS", 48),
        ("SPRINGER", 10),
        ("ROOZENBURG", 10),
        ("KELLER", 10),
    ],
)
def test_page_image_bundled_source(client: TestClient, source: str, page: int) -> None:
    """Pre-rendered page JPGs ship with the backend for these sources.
    `/page-image?source=<S>&page=<N>` returns the JPEG when present."""
    r = client.get("/api/strategy/page-image", params={"source": source, "page": page})
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert len(r.content) > 1000


def test_page_image_unknown_page_404s(client: TestClient) -> None:
    r = client.get(
        "/api/strategy/page-image", params={"source": "SIJBRANDS", "page": 9999}
    )
    assert r.status_code == 404
    assert "9999" in r.json()["detail"]


def test_page_image_unbundled_source_404s(client: TestClient) -> None:
    """A source we don't ship pages for must 404, not 500. All 4 corpora
    are now bundled (Sprints 1-2 in docs/STRATEGIE_DIAGRAMS_PLAN.md), so
    we probe with a synthetic source name to exercise the not-found path."""
    r = client.get(
        "/api/strategy/page-image", params={"source": "NOT_A_REAL_SOURCE", "page": 10}
    )
    assert r.status_code == 404


def test_diagram_crop_sijbrands(client: TestClient) -> None:
    """Sijbrands ships extracted diagram crops via texture-variance detection
    + caption proximity matching (Sprint 3, lane B). ~70% of pages produce
    at least one match — p.48 #6 is one of the canonical Chapter 4 examples."""
    r = client.get(
        "/api/strategy/diagram",
        params={"source": "SIJBRANDS", "page": 48, "number": 6},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert len(r.content) > 1000


def test_diagram_crop_springer(client: TestClient) -> None:
    """Springer ships extracted crops too (Sprint 4). Same DIAGRAMME N
    caption pattern as Sijbrands, just re-run through the generic
    extract_diagrams script with the springer source slug."""
    r = client.get(
        "/api/strategy/diagram",
        params={"source": "SPRINGER", "page": 9, "number": 1},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert len(r.content) > 1000


def test_diagram_crop_unextracted_pair_404s(client: TestClient) -> None:
    """A (page, number) pair not in the manifest must 404 — the frontend
    catches this via <img onError> and falls back to /page-image."""
    r = client.get(
        "/api/strategy/diagram",
        params={"source": "SIJBRANDS", "page": 48, "number": 99},
    )
    assert r.status_code == 404
    assert "not extracted" in r.json()["detail"]


def test_diagram_crop_unbundled_source_404s(client: TestClient) -> None:
    """Sources without an extraction manifest (KELLER and ROOZENBURG —
    see docs/STRATEGIE_DIAGRAMS_PLAN.md for why we skipped them) must
    404 with a clear hint."""
    r = client.get(
        "/api/strategy/diagram",
        params={"source": "KELLER", "page": 10, "number": 1},
    )
    assert r.status_code == 404
    assert "no diagram crops" in r.json()["detail"]


def test_diagram_fen_no_file_404(client: TestClient) -> None:
    """KELLER doesn't ship a diagrams_fens.json — different 404 message
    than 'not yet annotated' so the operator can tell the difference."""
    r = client.get(
        "/api/strategy/diagram-fen",
        params={"source": "KELLER", "page": 10, "number": 1},
    )
    assert r.status_code == 404
    assert "no FEN file" in r.json()["detail"]


def test_diagram_fen_not_annotated_404(client: TestClient) -> None:
    """Sijbrands and Springer ship diagrams_fens.json with `entries: []`
    — every diagram returns 404 'not yet annotated' until JF fills it in."""
    r = client.get(
        "/api/strategy/diagram-fen",
        params={"source": "SIJBRANDS", "page": 48, "number": 6},
    )
    assert r.status_code == 404
    assert "not yet annotated" in r.json()["detail"]


def test_diagram_fen_returns_annotation(client: TestClient, monkeypatch) -> None:
    """Once a (page, number) pair is added to diagrams_fens.json, the
    endpoint returns the FEN. Simulated by monkey-patching the loader
    so the test doesn't depend on the (currently empty) bundled file."""
    from strategy import api as api_mod

    sample_fen = "W:W31,32,33,34,35,36,37,38,39,40:B6,7,8,9,10,11,12,13,14,15"
    monkeypatch.setattr(
        api_mod,
        "_load_diagram_fens",
        lambda source: {(48, 6): sample_fen} if source == "SIJBRANDS" else {},
    )
    r = client.get(
        "/api/strategy/diagram-fen",
        params={"source": "SIJBRANDS", "page": 48, "number": 6},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["fen"] == sample_fen
    assert body["page"] == 48
    assert body["number"] == 6


def test_dormant_topic_returns_503(monkeypatch) -> None:
    """A topic whose filter matches no passage must yield 503, not 500.
    Simulated by injecting a topic with an impossible source filter."""
    import strategy.topics as topics_mod
    from strategy.api import router as router_mod
    from strategy.topics import Topic

    impossible = Topic(
        key="_test_impossible",
        label_fr="x",
        label_en="x",
        description_fr="x",
        source_filter=("NONEXISTENT_SOURCE",),
    )
    monkeypatch.setattr(topics_mod, "TOPICS", topics_mod.TOPICS + (impossible,))
    # Bust the lru_cache so the new topic is visible.
    topics_mod._topics_by_key.cache_clear()
    topics_mod.topic_centroid.cache_clear()

    app = FastAPI()
    app.include_router(router_mod)
    client = TestClient(app)

    r = client.get(
        "/api/strategy/search",
        params={"topic": "_test_impossible", "top_k": 3},
    )
    assert r.status_code == 503
    assert "no embedded passages" in r.json()["detail"]
