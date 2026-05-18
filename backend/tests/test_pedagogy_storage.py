"""Tests for backend/pedagogy/storage.py — PR 7 acceptance criteria."""
from __future__ import annotations

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import aiosqlite
import pytest

from db.schema import init_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_verdict(**kwargs):
    """Build a minimal MoveVerdict with sensible defaults."""
    from pedagogy.types import MoveVerdict, Verdict, Phase
    defaults = dict(
        move_number=1,
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
    defaults.update(kwargs)
    return MoveVerdict(**defaults)


def _make_analysis(game_id: str, user_id: int, verdicts=None):
    from pedagogy.types import GameAnalysis
    return GameAnalysis(
        game_id=game_id,
        user_id=user_id,
        user_side="white",
        opening_name="",
        verdicts=verdicts or [_make_verdict()],
        summary={},
    )


async def _fresh_conn():
    conn = await aiosqlite.connect(":memory:")
    await init_db.__wrapped__(conn) if hasattr(init_db, "__wrapped__") else None
    # init_db uses its own connection; recreate tables manually for in-memory
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY, date TEXT, user_id INTEGER,
            user_side TEXT, opening_name TEXT, status TEXT DEFAULT 'finished'
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY, name TEXT, initial_fen TEXT,
            solution_moves TEXT, difficulty INTEGER, category TEXT
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_exercise_solved (
            user_id INTEGER, exercise_id INTEGER,
            solved_at TEXT, PRIMARY KEY (user_id, exercise_id)
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS move_verdicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL, move_number INTEGER NOT NULL,
            side TEXT, fen_before TEXT, fen_after TEXT, move_notation TEXT,
            score_before REAL, score_after REAL, delta_winchance REAL,
            verdict TEXT, is_forced INTEGER, phase TEXT,
            motifs_json TEXT, features_json TEXT, features_after_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (game_id, move_number)
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS pedagogy_explanations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            move_verdict_id INTEGER NOT NULL, mode TEXT, lang TEXT, text TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (move_verdict_id, mode, lang)
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS exercise_tags (
            exercise_id INTEGER NOT NULL, tag TEXT NOT NULL,
            PRIMARY KEY (exercise_id, tag)
        )
    """)
    await conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_move_verdict_round_trip():
    from pedagogy import storage
    conn = await _fresh_conn()
    v = _make_verdict()
    row_id = await storage.upsert_move_verdict(conn, "game-1", v)
    assert isinstance(row_id, int)
    result = await storage.get_move_verdict(conn, "game-1", 1)
    assert result is not None
    assert result.move_notation == "32-28"
    assert result.verdict.value == "good"
    await conn.close()


@pytest.mark.asyncio
async def test_upsert_move_verdict_roundtrips_features_after_and_hanging():
    from pedagogy import storage
    from pedagogy.types import Features, Phase
    feats_after = Features(
        white_men=15, white_kings=0, black_men=14, black_kings=0,
        material_balance=1,
        center_count_white=3, center_count_black=2,
        left_wing_white=2, right_wing_white=2,
        left_wing_black=2, right_wing_black=3,
        isolated_pawns_white=[], isolated_pawns_black=[],
        backward_pawns_white=[], backward_pawns_black=[],
        holes_white=[], holes_black=[],
        outposts_white=[], outposts_black=[],
        white_legal_moves=7, black_legal_moves=8,
        hanging_pieces_white=[28], hanging_pieces_black=[],
        white_promotion_distance=5, black_promotion_distance=4,
        formations=[], phase=Phase.MIDDLEGAME,
    )
    conn = await _fresh_conn()
    v = _make_verdict(features_after=feats_after)
    await storage.upsert_move_verdict(conn, "game-feat", v)
    got = await storage.get_move_verdict(conn, "game-feat", 1)
    assert got is not None and got.features_after is not None
    assert got.features_after.hanging_pieces_white == [28]
    assert got.features_after.material_balance == 1
    await conn.close()


@pytest.mark.asyncio
async def test_features_from_json_backfills_missing_hanging_fields():
    # Legacy blob written before the hanging_pieces fields existed: the
    # deserialiser must still rehydrate it without raising.
    from pedagogy.storage import _features_from_json
    import json as _json
    legacy_blob = _json.dumps({
        "white_men": 10, "white_kings": 0, "black_men": 10, "black_kings": 0,
        "material_balance": 0,
        "center_count_white": 2, "center_count_black": 2,
        "left_wing_white": 1, "right_wing_white": 1,
        "left_wing_black": 1, "right_wing_black": 1,
        "isolated_pawns_white": [], "isolated_pawns_black": [],
        "backward_pawns_white": [], "backward_pawns_black": [],
        "holes_white": [], "holes_black": [],
        "outposts_white": [], "outposts_black": [],
        "white_legal_moves": 0, "black_legal_moves": 0,
        "white_promotion_distance": 5, "black_promotion_distance": 5,
        "formations": [], "phase": "middlegame",
    })
    f = _features_from_json(legacy_blob)
    assert f is not None
    assert f.hanging_pieces_white == []
    assert f.hanging_pieces_black == []


@pytest.mark.asyncio
async def test_upsert_move_verdict_is_idempotent():
    from pedagogy import storage
    conn = await _fresh_conn()
    v = _make_verdict()
    await storage.upsert_move_verdict(conn, "game-1", v)
    await storage.upsert_move_verdict(conn, "game-1", v)
    cur = await conn.execute(
        "SELECT COUNT(*) FROM move_verdicts WHERE game_id = 'game-1' AND move_number = 1"
    )
    row = await cur.fetchone()
    assert row[0] == 1
    await conn.close()


@pytest.mark.asyncio
async def test_upsert_game_analysis_persists_all_verdicts():
    from pedagogy import storage
    conn = await _fresh_conn()
    verdicts = [_make_verdict(move_number=i, fen_before=f"W:W{i}:B20") for i in range(1, 4)]
    analysis = _make_analysis("game-2", 42, verdicts=verdicts)
    ids = await storage.upsert_game_analysis(conn, analysis)
    assert len(ids) == 3
    cur = await conn.execute("SELECT COUNT(*) FROM move_verdicts WHERE game_id = 'game-2'")
    row = await cur.fetchone()
    assert row[0] == 3
    await conn.close()


@pytest.mark.asyncio
async def test_upsert_explanation_overwrites_same_mode_lang():
    from pedagogy import storage
    conn = await _fresh_conn()
    v = _make_verdict()
    vid = await storage.upsert_move_verdict(conn, "game-3", v)
    await storage.upsert_explanation(conn, vid, "template", "fr", "Texte 1")
    await storage.upsert_explanation(conn, vid, "template", "fr", "Texte 2")
    cur = await conn.execute(
        "SELECT COUNT(*) FROM pedagogy_explanations WHERE move_verdict_id = ?", (vid,)
    )
    row = await cur.fetchone()
    assert row[0] == 1
    text = await storage.get_explanation(conn, vid, "template", "fr")
    assert text == "Texte 2"
    await conn.close()


@pytest.mark.asyncio
async def test_upsert_explanation_distinguishes_lang():
    from pedagogy import storage
    conn = await _fresh_conn()
    v = _make_verdict()
    vid = await storage.upsert_move_verdict(conn, "game-4", v)
    await storage.upsert_explanation(conn, vid, "template", "fr", "En français")
    await storage.upsert_explanation(conn, vid, "template", "en", "In English")
    cur = await conn.execute(
        "SELECT COUNT(*) FROM pedagogy_explanations WHERE move_verdict_id = ?", (vid,)
    )
    row = await cur.fetchone()
    assert row[0] == 2
    await conn.close()


@pytest.mark.asyncio
async def test_set_exercise_tags_replaces_atomically():
    from pedagogy import storage
    conn = await _fresh_conn()
    await conn.execute("INSERT INTO exercises VALUES (1,'ex','W:W32:B20','[]',1,'cat')")
    await conn.commit()
    await storage.set_exercise_tags(conn, 1, ["coup_royal", "sacrifice"])
    await storage.set_exercise_tags(conn, 1, ["sacrifice", "coup_turc", "envoi_a_dame"])
    tags = await storage.get_exercise_tags(conn, 1)
    assert set(tags) == {"sacrifice", "coup_turc", "envoi_a_dame"}
    await conn.close()


@pytest.mark.asyncio
async def test_fetch_exercises_by_tags_excludes_solved():
    from pedagogy import storage
    conn = await _fresh_conn()
    await conn.execute("INSERT INTO exercises VALUES (1,'ex1','W:W32:B20','[]',1,'cat')")
    await conn.execute("INSERT INTO exercises VALUES (2,'ex2','W:W31:B20','[]',1,'cat')")
    await conn.commit()
    await storage.set_exercise_tags(conn, 1, ["coup_royal"])
    await storage.set_exercise_tags(conn, 2, ["coup_royal"])
    results = await storage.fetch_exercises_by_tags(conn, ["coup_royal"], exclude_ids=[1])
    ids = [r["id"] for r in results]
    assert 1 not in ids
    assert 2 in ids
    await conn.close()


@pytest.mark.asyncio
async def test_tables_exist_in_fresh_db():
    conn = await _fresh_conn()
    cur = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = {r[0] for r in await cur.fetchall()}
    assert "move_verdicts" in tables
    assert "pedagogy_explanations" in tables
    assert "exercise_tags" in tables
    await conn.close()


@pytest.mark.asyncio
async def test_fetch_user_games_with_verdicts_orders_desc():
    """The most recent game should come first (spec §10)."""
    from pedagogy import storage
    conn = await _fresh_conn()
    await conn.execute(
        "INSERT INTO games (id, date, user_id, user_side, opening_name, status) "
        "VALUES (?, '2026-01-01', 1, 'white', '', 'finished')",
        ("game-old",),
    )
    await conn.execute(
        "INSERT INTO games (id, date, user_id, user_side, opening_name, status) "
        "VALUES (?, '2026-05-01', 1, 'white', '', 'finished')",
        ("game-new",),
    )
    await conn.commit()
    await storage.upsert_move_verdict(conn, "game-old", _make_verdict(move_number=1))
    await storage.upsert_move_verdict(conn, "game-new", _make_verdict(move_number=1))
    games = await storage.fetch_user_games_with_verdicts(conn, user_id=1, lookback=30)
    assert [g.game_id for g in games] == ["game-new", "game-old"]
    await conn.close()


@pytest.mark.asyncio
async def test_fetch_user_games_with_verdicts_orders_by_date_not_rowid():
    """Lookback window must follow date, not INSERT order.

    Regression: the lidraughts import inserts games in API-response
    order, which is not always chronological. If the lookback used
    ``ORDER BY rowid DESC`` the 30 newest-by-date games (the ones the
    user sees in ``/api/history`` and analyses first) could end up
    outside the window — leaving Points faibles empty for hours of
    analysing.
    """
    from pedagogy import storage
    conn = await _fresh_conn()
    # Insert the MOST RECENT date FIRST (low rowid), older date last
    # (high rowid). With rowid-based ordering the old game would come
    # first, breaking the assertion.
    await conn.execute(
        "INSERT INTO games (id, date, user_id, user_side, opening_name, status) "
        "VALUES (?, '2026-12-01', 1, 'white', '', 'finished')",
        ("g-recent",),
    )
    await conn.execute(
        "INSERT INTO games (id, date, user_id, user_side, opening_name, status) "
        "VALUES (?, '2020-01-01', 1, 'white', '', 'finished')",
        ("g-ancient",),
    )
    await conn.commit()
    games = await storage.fetch_user_games_with_verdicts(conn, user_id=1, lookback=30)
    assert [g.game_id for g in games] == ["g-recent", "g-ancient"]
    await conn.close()
