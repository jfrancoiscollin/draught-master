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
