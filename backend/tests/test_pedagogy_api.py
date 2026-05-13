"""Tests for backend/pedagogy/api.py — PR 8 acceptance criteria."""
from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import aiosqlite
import pytest
from fastapi.testclient import TestClient


def _make_app():
    """Build a minimal FastAPI test app with the pedagogy router."""
    from fastapi import FastAPI
    from pedagogy.api import router
    app = FastAPI()
    app.include_router(router)
    return app


def _auth_headers(user_id: int = 1, email: str = "test@example.com") -> dict:
    """Create a valid JWT for tests."""
    from auth import _create_token
    token = _create_token(user_id, email)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_verdict(conn, game_id: str = "game-test", move_number: int = 1):
    from pedagogy import storage
    from pedagogy.types import MoveVerdict, Verdict, Phase
    v = MoveVerdict(
        move_number=move_number,
        side="white",
        move_notation="32-28",
        fen_before="W:W32:B20",
        fen_after="W:W28:B20",
        score_before=0.1,
        score_after=0.05,
        delta_winchance=0.05,
        verdict=Verdict.GOOD,
        is_forced=False,
        phase=Phase.MIDDLEGAME,
        motifs=[],
        features_before=None,
        features_after=None,
    )
    return await storage.upsert_move_verdict(conn, game_id, v)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_move_verdict_404_when_not_computed(monkeypatch, tmp_path):
    """Fresh DB → 404 for any (game_id, move_number)."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("pedagogy.api._db_path", lambda: db_file)

    import asyncio
    async def _init():
        conn = await aiosqlite.connect(db_file)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS move_verdicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, game_id TEXT,
                move_number INTEGER, side TEXT, fen_before TEXT, fen_after TEXT,
                move_notation TEXT, score_before REAL, score_after REAL,
                delta_winchance REAL, verdict TEXT, is_forced INTEGER,
                phase TEXT, motifs_json TEXT, features_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, move_number)
            )
        """)
        await conn.commit()
        await conn.close()
    asyncio.run(_init())

    app = _make_app()
    client = TestClient(app)
    resp = client.get("/api/pedagogy/move-verdict/no-game/1", headers=_auth_headers())
    assert resp.status_code == 404


def test_get_move_verdict_returns_persisted_row(monkeypatch, tmp_path):
    """Write a verdict via storage, GET returns it."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("pedagogy.api._db_path", lambda: db_file)

    import asyncio
    async def _setup():
        conn = await aiosqlite.connect(db_file)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS move_verdicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, game_id TEXT,
                move_number INTEGER, side TEXT, fen_before TEXT, fen_after TEXT,
                move_notation TEXT, score_before REAL, score_after REAL,
                delta_winchance REAL, verdict TEXT, is_forced INTEGER,
                phase TEXT, motifs_json TEXT, features_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, move_number)
            )
        """)
        await conn.commit()
        await _seed_verdict(conn, "game-x", 5)
        await conn.close()
    asyncio.run(_setup())

    app = _make_app()
    client = TestClient(app)
    resp = client.get("/api/pedagogy/move-verdict/game-x/5", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["move_notation"] == "32-28"
    assert data["verdict"] == "good"


def test_analyze_game_unauthenticated_returns_401():
    """No token → 401."""
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/pedagogy/analyze-game", json={"game_id": "x"})
    assert resp.status_code == 401


def test_explain_move_404_when_verdict_missing(monkeypatch, tmp_path):
    """explain-move returns 404 if verdict not yet computed."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("pedagogy.api._db_path", lambda: db_file)

    import asyncio
    async def _init():
        conn = await aiosqlite.connect(db_file)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS move_verdicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, game_id TEXT,
                move_number INTEGER, side TEXT, fen_before TEXT, fen_after TEXT,
                move_notation TEXT, score_before REAL, score_after REAL,
                delta_winchance REAL, verdict TEXT, is_forced INTEGER,
                phase TEXT, motifs_json TEXT, features_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, move_number)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pedagogy_explanations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, move_verdict_id INTEGER,
                mode TEXT, lang TEXT, text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(move_verdict_id, mode, lang)
            )
        """)
        await conn.commit()
        await conn.close()
    asyncio.run(_init())

    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/pedagogy/explain-move",
        json={"game_id": "missing", "move_number": 99, "mode": "template", "lang": "fr"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 404


def test_get_user_profile_forbidden_for_other_user(monkeypatch, tmp_path):
    """Non-admin reading another user's profile → 403."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("pedagogy.api._db_path", lambda: db_file)

    import asyncio
    async def _init():
        conn = await aiosqlite.connect(db_file)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY, user_id INTEGER,
                user_side TEXT, opening_name TEXT, status TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS move_verdicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, game_id TEXT,
                move_number INTEGER, side TEXT, fen_before TEXT, fen_after TEXT,
                move_notation TEXT, score_before REAL, score_after REAL,
                delta_winchance REAL, verdict TEXT, is_forced INTEGER,
                phase TEXT, motifs_json TEXT, features_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, move_number)
            )
        """)
        await conn.commit()
        await conn.close()
    asyncio.run(_init())

    app = _make_app()
    client = TestClient(app)
    # user_id=1 tries to access user_id=2
    resp = client.get("/api/pedagogy/profile/2", headers=_auth_headers(user_id=1))
    assert resp.status_code == 403
