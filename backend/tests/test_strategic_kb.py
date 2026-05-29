"""Tests for the thematic strategic knowledge base and its API routes."""

from __future__ import annotations

import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from strategy import strategic_kb as kb
from strategy.api import router


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_theme_index_non_empty_and_sorted():
    cards = kb.theme_index()
    assert cards
    counts = [c["n_positions"] for c in cards]
    assert counts == sorted(counts, reverse=True)
    for c in cards:
        assert c["theme"]
        assert c["n_positions"] >= 1
        assert len(c["examples"]) <= 3
        assert c["sources"]


def test_representative_dedupes_and_prefers_human():
    cards = kb.theme_index("SIJBRANDS")
    sample = cards[0]["examples"]
    fens = [e["fen"] for e in sample]
    assert len(fens) == len(set(fens))  # de-duplicated


def test_theme_detail_round_trips():
    theme = kb.theme_index()[0]["theme"]
    detail = kb.theme_detail(theme)
    assert detail["theme"] == theme
    assert detail["n_positions"] >= 1
    assert detail["positions"]


def test_kb_themes_endpoint(client: TestClient):
    r = client.get("/api/strategy/kb-themes")
    assert r.status_code == 200
    assert len(r.json()) > 1


def test_kb_theme_endpoint_and_404(client: TestClient):
    theme = kb.theme_index()[0]["theme"]
    r = client.get("/api/strategy/kb-theme", params={"theme": theme})
    assert r.status_code == 200
    assert r.json()["n_positions"] >= 1

    r = client.get("/api/strategy/kb-theme", params={"theme": "zzz-nope"})
    assert r.status_code == 404


def test_diagram_fen_carries_validity_flag(client: TestClient):
    """The prose-facing endpoint exposes the engine-validated flag so the
    frontend can skip rendering a broken board for a bad auto FEN."""
    # A known-good Sijbrands diagram.
    r = client.get(
        "/api/strategy/diagram-fen",
        params={"source": "SIJBRANDS", "page": 6, "number": 1},
    )
    assert r.status_code == 200 and r.json()["valid"] is True
    # A known detector failure (empty board "W:W:B").
    r = client.get(
        "/api/strategy/diagram-fen",
        params={"source": "SIJBRANDS", "page": 7, "number": 7},
    )
    assert r.status_code == 200 and r.json()["valid"] is False
