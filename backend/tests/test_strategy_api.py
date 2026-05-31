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
    """A source with no extraction manifest must 404 with a clear hint.
    All four manuals are now scanned, so this probes an unknown source."""
    r = client.get(
        "/api/strategy/diagram",
        params={"source": "NONEXISTENT", "page": 10, "number": 1},
    )
    assert r.status_code == 404
    assert "no diagram crops" in r.json()["detail"]


def test_diagram_fen_missing_entry_404(client: TestClient) -> None:
    """All four manuals now ship auto FENs covering their manifest, so a
    404 only happens for a (page, number) that exists in neither the human
    nor the auto file. Probe a deliberately out-of-range coordinate."""
    r = client.get(
        "/api/strategy/diagram-fen",
        params={"source": "KELLER", "page": 999, "number": 99},
    )
    assert r.status_code == 404
    assert "no FEN" in r.json()["detail"]


def test_diagram_fen_trusted_auto_drops_badge(client: TestClient) -> None:
    """Sijbrands is now a trusted-auto source: an auto-detected FEN is
    served as kind='human' (no 'non validé' badge) and carries the
    engine-validated flag."""
    r = client.get(
        "/api/strategy/diagram-fen",
        params={"source": "SIJBRANDS", "page": 6, "number": 1},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "human"
    assert body["valid"] is True


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


def test_scanned_manual_is_multi_chapter_and_deduplicated(client: TestClient) -> None:
    """Each scanned manual reads as several distinct chapters.

    The transversal reading topics (ouverture / plans / principes / pièges,
    plus finales) turn the old 2-chapter view into a fuller read, and each
    passage is assigned to a single best-fit chapter (no cross-chapter
    duplication).
    """
    for source in ("SIJBRANDS", "SPRINGER", "ROOZENBURG", "KELLER"):
        r = client.get("/api/strategy/manual", params={"source": source})
        assert r.status_code == 200, source
        chapters = r.json()["chapters"]
        assert len(chapters) >= 4, f"{source}: only {len(chapters)} chapters"

        ids = [p["passage_id"] for ch in chapters for p in ch["passages"]]
        assert len(ids) == len(set(ids)), f"{source}: a passage appears in two chapters"

        # Scores are descending within each chapter and meaningfully similar.
        for ch in chapters:
            scores = [p["score"] for p in ch["passages"]]
            assert scores == sorted(scores, reverse=True), f"{source}/{ch['topic_key']}"


def test_section_titles_are_clean_not_body_text() -> None:
    """Regression: the manual must never title a card with a stray body line.

    The raw extraction recurs a heading (e.g. "Thème 8") on every page and
    captured the following line as the title, so later pages inherited move
    sequences / full sentences. _load_diagram_sections canonicalises each
    heading to one clean title; assert every served title is title-ish and a
    heading shows a single title across its pages.
    """
    from strategy.api import _is_titleish, _load_diagram_sections

    for source in ("SPRINGER", "SIJBRANDS", "ROOZENBURG", "KELLER"):
        sections = _load_diagram_sections(source)
        per_heading: dict[str, set[str]] = {}
        for entry in sections.values():
            h, t = entry.get("heading"), entry.get("title", "")
            assert h is not None
            if t:  # non-empty titles must look like real titles
                assert _is_titleish(t), f"{source}: junk title {t!r} under {h!r}"
            per_heading.setdefault(h, set()).add(t)
        # One canonical title per heading (no per-page drift).
        for h, titles in per_heading.items():
            assert len(titles) == 1, f"{source}: heading {h!r} has drifting titles {titles}"


def test_springer_theme_8_canonical_title() -> None:
    """The reported bug: Springer p.167 showed 'Thème 8 · Et ce logiciel…'.
    It must now read the real theme title."""
    from strategy.api import _load_diagram_sections

    s = _load_diagram_sections("SPRINGER")
    assert s.get(167, {}).get("heading") == "Thème 8"
    assert "ouverture" in s[167]["title"].lower()
    assert "logiciel" not in s[167]["title"].lower()


def test_manual_passages_are_readable_prose(client: TestClient) -> None:
    """Regression: the manual must not surface pure move-score / game-citation
    dumps (reported on Goedemoed: "0 prose"). Every served passage carries a
    real sentence."""
    from strategy.prose_quality import has_prose

    for source in ("SIJBRANDS", "SPRINGER", "ROOZENBURG", "KELLER"):
        r = client.get("/api/strategy/manual", params={"source": source})
        assert r.status_code == 200, source
        served = [p for ch in r.json()["chapters"] for p in ch["passages"]]
        assert served, f"{source}: manual is empty"
        for p in served:
            assert has_prose(p["text"]), f"{source}: non-prose passage {p['passage_id']}"


def test_manual_chapters_and_lesson_shape(client: TestClient) -> None:
    """The strategic manual exposes a book-order chapter list and renders each
    chapter in the Débutant lesson shape (title/text/diagrams) so LessonPanel
    can display it identically."""
    import re

    toc = client.get("/api/strategy/manual-chapters", params={"source": "SIJBRANDS"})
    assert toc.status_code == 200
    chapters = toc.json()["chapters"]
    assert len(chapters) > 5
    # Indices are contiguous from 0 and every chapter has a title.
    assert [c["index"] for c in chapters] == list(range(len(chapters)))
    assert all(c["title"].strip() for c in chapters)

    # Find a chapter that actually carries diagrams and check the lesson shape.
    saw_diagram_ref = False
    for c in chapters[:12]:
        L = client.get(
            "/api/strategy/manual-lesson",
            params={"source": "SIJBRANDS", "chapter": c["index"]},
        ).json()
        assert L["title"].strip()
        assert isinstance(L["text"], str) and L["text"].strip()
        for d in L["diagrams"]:
            assert d["fen"].startswith(("W:", "B:"))
            assert d["label"].startswith("diag.")
        if L["diagrams"]:
            saw_diagram_ref = True
            # Every diag. K used in the text has a backing diagram entry.
            used = {int(m) for m in re.findall(r"diag\.\s*(\d+)", L["text"])}
            assert used and max(used) <= len(L["diagrams"])
    assert saw_diagram_ref, "no chapter exposed a diagram"


def test_manual_lesson_out_of_range_404(client: TestClient) -> None:
    r = client.get(
        "/api/strategy/manual-lesson", params={"source": "SIJBRANDS", "chapter": 99999}
    )
    assert r.status_code == 404
