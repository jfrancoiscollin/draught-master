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
                phase TEXT, motifs_json TEXT, features_json TEXT, features_after_json TEXT,
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
                phase TEXT, motifs_json TEXT, features_json TEXT, features_after_json TEXT,
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
                phase TEXT, motifs_json TEXT, features_json TEXT, features_after_json TEXT,
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
                phase TEXT, motifs_json TEXT, features_json TEXT, features_after_json TEXT,
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


# ---------------------------------------------------------------------------
# explain-move — template path, caching, lang separation
# ---------------------------------------------------------------------------


def _init_pedagogy_tables(db_file: str) -> None:
    """Create the 3 pedagogy tables in an empty SQLite file (sync helper)."""
    import asyncio
    async def _go():
        conn = await aiosqlite.connect(db_file)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS move_verdicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, game_id TEXT,
                move_number INTEGER, side TEXT, fen_before TEXT, fen_after TEXT,
                move_notation TEXT, score_before REAL, score_after REAL,
                delta_winchance REAL, verdict TEXT, is_forced INTEGER,
                phase TEXT, motifs_json TEXT, features_json TEXT, features_after_json TEXT,
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
    asyncio.run(_go())


def test_explain_move_template_mode_returns_string(monkeypatch, tmp_path):
    """Template mode runs through dilf's pipeline and returns a real string
    (no Anthropic call). Regression test for the missing-await bug that
    caused a coroutine to leak into the response."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("pedagogy.api._db_path", lambda: db_file)
    _init_pedagogy_tables(db_file)

    import asyncio
    async def _seed():
        conn = await aiosqlite.connect(db_file)
        await _seed_verdict(conn, "game-tpl", 1)
        await conn.close()
    asyncio.run(_seed())

    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/pedagogy/explain-move",
        json={"game_id": "game-tpl", "move_number": 1, "mode": "template", "lang": "fr"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["text"], str) and data["text"].strip()
    assert data["cached"] is False
    assert data["mode"] == "template"


def test_explain_move_uses_cache_on_second_call(monkeypatch, tmp_path):
    """Same (verdict, mode, lang) → second call has cached=true and reuses
    the stored text. No invocation of the underlying explainer."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("pedagogy.api._db_path", lambda: db_file)
    _init_pedagogy_tables(db_file)

    import asyncio
    async def _seed():
        conn = await aiosqlite.connect(db_file)
        await _seed_verdict(conn, "game-cache", 1)
        await conn.close()
    asyncio.run(_seed())

    # Sentinel that fails the test if explain_verdict is called twice.
    call_count = {"n": 0}

    async def _fake_explain(verdict, *, mode, book_rag, lang):
        call_count["n"] += 1
        return f"text-{call_count['n']}"

    monkeypatch.setattr("pedagogy.api.explain_verdict", _fake_explain)

    app = _make_app()
    client = TestClient(app)
    payload = {"game_id": "game-cache", "move_number": 1, "mode": "template", "lang": "fr"}
    first = client.post("/api/pedagogy/explain-move", json=payload, headers=_auth_headers())
    second = client.post("/api/pedagogy/explain-move", json=payload, headers=_auth_headers())

    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["cached"] is False
    assert first.json()["text"] == "text-1"
    assert second.json()["cached"] is True
    assert second.json()["text"] == "text-1"
    assert call_count["n"] == 1


def test_explain_move_different_lang_creates_separate_cache(monkeypatch, tmp_path):
    """fr/template + en/template = two cached rows (one per language)."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("pedagogy.api._db_path", lambda: db_file)
    _init_pedagogy_tables(db_file)

    import asyncio
    async def _seed():
        conn = await aiosqlite.connect(db_file)
        await _seed_verdict(conn, "game-lang", 1)
        await conn.close()
    asyncio.run(_seed())

    captured = []

    async def _fake_explain(verdict, *, mode, book_rag, lang):
        captured.append(lang)
        return f"text-{lang}"

    monkeypatch.setattr("pedagogy.api.explain_verdict", _fake_explain)

    app = _make_app()
    client = TestClient(app)
    base = {"game_id": "game-lang", "move_number": 1, "mode": "template"}
    fr = client.post("/api/pedagogy/explain-move", json={**base, "lang": "fr"}, headers=_auth_headers())
    en = client.post("/api/pedagogy/explain-move", json={**base, "lang": "en"}, headers=_auth_headers())

    assert fr.json()["cached"] is False and en.json()["cached"] is False
    assert fr.json()["text"] == "text-fr"
    assert en.json()["text"] == "text-en"
    assert captured == ["fr", "en"]


# ---------------------------------------------------------------------------
# recommendations — exclude already-solved exercises
# ---------------------------------------------------------------------------


def test_get_recommendations_filters_solved(monkeypatch, tmp_path):
    """An exercise tagged with a weakness motif AND already solved by the
    user must not appear in the recommendations response."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("pedagogy.api._db_path", lambda: db_file)

    import asyncio
    async def _init():
        conn = await aiosqlite.connect(db_file)
        await conn.execute("""
            CREATE TABLE games (
                id TEXT PRIMARY KEY, user_id INTEGER,
                user_side TEXT, opening_name TEXT, status TEXT,
                -- `date` is queried by storage.fetch_user_games_with_verdicts
                -- (ORDER BY date DESC) — without it the test errored with
                -- "no such column: date" on the recommender's lookback walk.
                date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE TABLE move_verdicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, game_id TEXT,
                move_number INTEGER, side TEXT, fen_before TEXT, fen_after TEXT,
                move_notation TEXT, score_before REAL, score_after REAL,
                delta_winchance REAL, verdict TEXT, is_forced INTEGER,
                phase TEXT, motifs_json TEXT, features_json TEXT, features_after_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, move_number)
            )
        """)
        await conn.execute("""
            CREATE TABLE exercises (
                id INTEGER PRIMARY KEY, name TEXT,
                initial_fen TEXT, solution_moves TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE exercise_tags (
                exercise_id INTEGER, tag TEXT, PRIMARY KEY (exercise_id, tag)
            )
        """)
        await conn.execute("""
            CREATE TABLE user_exercise_solved (
                user_id INTEGER, exercise_id INTEGER, solved_at TEXT,
                PRIMARY KEY (user_id, exercise_id)
            )
        """)
        # Two exercises tagged coup_royal — one already solved by user 1.
        await conn.execute(
            "INSERT INTO exercises (id, name, initial_fen, solution_moves) VALUES "
            "(10, 'solved-ex', 'W:W32:B20', '[\"32-28\"]'), "
            "(11, 'fresh-ex',  'W:W31:B20', '[\"31-27\"]')"
        )
        await conn.execute(
            "INSERT INTO exercise_tags (exercise_id, tag) VALUES (10, 'coup_royal'), (11, 'coup_royal')"
        )
        await conn.execute(
            "INSERT INTO user_exercise_solved (user_id, exercise_id, solved_at) "
            "VALUES (1, 10, '2026-05-01')"
        )
        await conn.commit()
        await conn.close()
    asyncio.run(_init())

    # Force aggregate_user_profile to surface coup_royal as a weakness.
    from pedagogy.types import Phase, UserProfile

    def _fake_profile(user_id, games):
        return UserProfile(
            user_id=user_id,
            games_count=1,
            average_accuracy=0.5,
            strengths=[],
            weaknesses=[{"motif": "coup_royal", "missed": 5, "suffered": 0,
                         "played": 0, "total_severity": 5.0}],
            weakest_phase=Phase.MIDDLEGAME,
            recommended_exercise_tags=["coup_royal"],
        )
    monkeypatch.setattr("pedagogy.api.aggregate_user_profile", _fake_profile)

    # Force recommend_exercises to return whatever pool the endpoint hands it.
    monkeypatch.setattr(
        "pedagogy.api.recommend_exercises",
        lambda profile, pool, *, exclude_ids=(), n=10: list(pool)[:n],
    )

    app = _make_app()
    client = TestClient(app)
    resp = client.get("/api/pedagogy/profile/me/recommendations",
                      headers=_auth_headers(user_id=1))
    assert resp.status_code == 200
    ids = {e["id"] for e in resp.json()["exercises"]}
    assert 10 not in ids       # the solved one is filtered out
    assert 11 in ids           # the fresh one comes through
