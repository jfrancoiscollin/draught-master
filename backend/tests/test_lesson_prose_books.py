"""The lesson-prose endpoints expose all three readable books without id clashes.

Débutant (1-16), Dubois sens du jeu (101-135) and Dubois combinaisons
(201-241) all serve chapter prose through ``/api/lessons`` (titles) and
``/api/lessons/{chapter}`` (full text). Their chapter-id ranges must stay
disjoint so the shared per-chapter endpoint is unambiguous.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient

from main import app

_client = TestClient(app)

_BOOKS = {
    "manuel_debutant": (1, 99),
    "manuel_dubois_sens_du_jeu": (100, 199),
    "manuel_dubois_combinaisons": (200, 299),
}


def test_each_book_lists_chapters_in_its_own_id_range():
    for book, (lo, hi) in _BOOKS.items():
        data = _client.get("/api/lessons", params={"book": book}).json()
        assert data, f"{book} exposes no chapters"
        ids = [int(k) for k in data]
        assert all(lo <= i <= hi for i in ids), f"{book} ids out of range: {ids}"


def test_chapter_id_ranges_are_disjoint():
    seen: dict[int, str] = {}
    for book in _BOOKS:
        for ch in _client.get("/api/lessons", params={"book": book}).json():
            i = int(ch)
            assert i not in seen, f"chapter {i} claimed by both {seen.get(i)} and {book}"
            seen[i] = book


def test_chapter_endpoint_serves_full_prose():
    # One representative chapter per book: real title + non-empty prose text.
    for ch in (1, 102, 201):
        r = _client.get(f"/api/lessons/{ch}")
        assert r.status_code == 200, ch
        body = r.json()
        assert body["title"].strip()
        assert len(body["text"]) > 200, f"chapter {ch} prose too short"


def test_combinaisons_chapters_are_reachable():
    # The 41 Dubois combinaisons chapters were dormant before this wiring.
    data = _client.get("/api/lessons", params={"book": "manuel_dubois_combinaisons"}).json()
    assert len(data) == 41
    # Every listed chapter must resolve to served prose.
    for ch in data:
        assert _client.get(f"/api/lessons/{ch}").status_code == 200
