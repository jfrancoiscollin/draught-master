"""Tests for backend/live/api.py — J1 acceptance criteria.

Covers the challenge queue: create, list pending, accept/decline,
cancel, plus the four 4xx paths (404 unknown opponent, 422 self,
409 duplicate, 409 already-responded).
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import aiosqlite
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app():
    from live.api import router
    app = FastAPI()
    app.include_router(router)
    return app


def _auth_headers(user_id: int, email: str) -> dict:
    from auth import _create_token
    token = _create_token(user_id, email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Per-test SQLite file with just the users + live_challenges
    tables; no need to spin the full schema for these routes. Pattern
    mirrors test_pedagogy_api.py: monkeypatch the api module's
    ``_db_path`` so we don't have to rebuild module-level constants."""
    p = tmp_path / "live.sqlite"
    monkeypatch.setattr("live.api._db_path", lambda: str(p))

    async def _init():
        conn = await aiosqlite.connect(str(p))
        await conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT UNIQUE
            )
        """)
        # Mirror of db/schema.py:live_challenges (kept minimal — drop FK
        # cascades to keep the in-memory init terse).
        await conn.execute("""
            CREATE TABLE live_challenges (
                id TEXT PRIMARY KEY,
                challenger_id INTEGER NOT NULL,
                opponent_id INTEGER NOT NULL,
                preferred_color TEXT NOT NULL DEFAULT 'random',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,
                game_id TEXT
            )
        """)
        await conn.executemany(
            "INSERT INTO users (id, username, email) VALUES (?, ?, ?)",
            [
                (1, "alice", "alice@example.com"),
                (2, "bob",   "bob@example.com"),
                (3, "carol", "carol@example.com"),
            ],
        )
        await conn.commit()
        await conn.close()
    asyncio.run(_init())
    return str(p)


# ---------------------------------------------------------------------------
# create_challenge
# ---------------------------------------------------------------------------


def test_create_challenge_happy_path(db_path):
    app = _make_app()
    client = TestClient(app)
    r = client.post(
        "/api/live/challenge",
        headers=_auth_headers(1, "alice@example.com"),
        json={"opponent_username": "bob", "preferred_color": "white"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["challenger_username"] == "alice"
    assert data["opponent_username"] == "bob"
    assert data["preferred_color"] == "white"
    assert data["status"] == "pending"
    assert data["game_id"] is None


def test_create_challenge_username_lookup_is_case_insensitive(db_path):
    app = _make_app()
    client = TestClient(app)
    r = client.post(
        "/api/live/challenge",
        headers=_auth_headers(1, "alice@example.com"),
        json={"opponent_username": "BOB"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["opponent_username"] == "bob"


def test_create_challenge_unknown_opponent_404(db_path):
    app = _make_app()
    client = TestClient(app)
    r = client.post(
        "/api/live/challenge",
        headers=_auth_headers(1, "alice@example.com"),
        json={"opponent_username": "nobody"},
    )
    assert r.status_code == 404


def test_create_challenge_self_challenge_422(db_path):
    app = _make_app()
    client = TestClient(app)
    r = client.post(
        "/api/live/challenge",
        headers=_auth_headers(1, "alice@example.com"),
        json={"opponent_username": "alice"},
    )
    assert r.status_code == 422


def test_create_challenge_duplicate_pending_409(db_path):
    app = _make_app()
    client = TestClient(app)
    h = _auth_headers(1, "alice@example.com")
    r1 = client.post("/api/live/challenge", headers=h,
                     json={"opponent_username": "bob"})
    assert r1.status_code == 200
    r2 = client.post("/api/live/challenge", headers=h,
                     json={"opponent_username": "bob"})
    assert r2.status_code == 409


# ---------------------------------------------------------------------------
# list_pending_challenges
# ---------------------------------------------------------------------------


def test_pending_challenges_split_sent_vs_received(db_path):
    app = _make_app()
    client = TestClient(app)
    # Alice challenges Bob and Carol.
    client.post("/api/live/challenge",
                headers=_auth_headers(1, "alice@example.com"),
                json={"opponent_username": "bob"})
    client.post("/api/live/challenge",
                headers=_auth_headers(1, "alice@example.com"),
                json={"opponent_username": "carol"})
    # Carol challenges Alice back.
    client.post("/api/live/challenge",
                headers=_auth_headers(3, "carol@example.com"),
                json={"opponent_username": "alice"})

    r = client.get("/api/live/challenges/pending",
                   headers=_auth_headers(1, "alice@example.com"))
    assert r.status_code == 200, r.text
    payload = r.json()
    assert len(payload["sent"]) == 2
    assert {c["opponent_username"] for c in payload["sent"]} == {"bob", "carol"}
    assert len(payload["received"]) == 1
    assert payload["received"][0]["challenger_username"] == "carol"


# ---------------------------------------------------------------------------
# respond_challenge
# ---------------------------------------------------------------------------


def test_respond_accept_moves_to_accepted(db_path):
    app = _make_app()
    client = TestClient(app)
    create = client.post(
        "/api/live/challenge",
        headers=_auth_headers(1, "alice@example.com"),
        json={"opponent_username": "bob"},
    )
    cid = create.json()["id"]
    r = client.post(
        f"/api/live/challenge/{cid}/respond",
        headers=_auth_headers(2, "bob@example.com"),
        json={"accept": True},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "accepted"
    assert data["resolved_at"] is not None


def test_respond_decline_moves_to_declined(db_path):
    app = _make_app()
    client = TestClient(app)
    cid = client.post(
        "/api/live/challenge",
        headers=_auth_headers(1, "alice@example.com"),
        json={"opponent_username": "bob"},
    ).json()["id"]
    r = client.post(
        f"/api/live/challenge/{cid}/respond",
        headers=_auth_headers(2, "bob@example.com"),
        json={"accept": False},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "declined"


def test_respond_by_non_opponent_404(db_path):
    """Carol shouldn't be able to respond to a challenge between alice
    and bob. We return 404 (not 403) to avoid leaking existence."""
    app = _make_app()
    client = TestClient(app)
    cid = client.post(
        "/api/live/challenge",
        headers=_auth_headers(1, "alice@example.com"),
        json={"opponent_username": "bob"},
    ).json()["id"]
    r = client.post(
        f"/api/live/challenge/{cid}/respond",
        headers=_auth_headers(3, "carol@example.com"),
        json={"accept": True},
    )
    assert r.status_code == 404


def test_respond_twice_409(db_path):
    app = _make_app()
    client = TestClient(app)
    cid = client.post(
        "/api/live/challenge",
        headers=_auth_headers(1, "alice@example.com"),
        json={"opponent_username": "bob"},
    ).json()["id"]
    client.post(f"/api/live/challenge/{cid}/respond",
                headers=_auth_headers(2, "bob@example.com"),
                json={"accept": True})
    r = client.post(f"/api/live/challenge/{cid}/respond",
                    headers=_auth_headers(2, "bob@example.com"),
                    json={"accept": True})
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# cancel_challenge
# ---------------------------------------------------------------------------


def test_cancel_by_challenger_moves_to_cancelled(db_path):
    app = _make_app()
    client = TestClient(app)
    cid = client.post(
        "/api/live/challenge",
        headers=_auth_headers(1, "alice@example.com"),
        json={"opponent_username": "bob"},
    ).json()["id"]
    r = client.post(
        f"/api/live/challenge/{cid}/cancel",
        headers=_auth_headers(1, "alice@example.com"),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_cancel_by_non_challenger_404(db_path):
    app = _make_app()
    client = TestClient(app)
    cid = client.post(
        "/api/live/challenge",
        headers=_auth_headers(1, "alice@example.com"),
        json={"opponent_username": "bob"},
    ).json()["id"]
    # Bob (opponent) can't cancel — must decline via /respond instead.
    r = client.post(
        f"/api/live/challenge/{cid}/cancel",
        headers=_auth_headers(2, "bob@example.com"),
    )
    assert r.status_code == 404
