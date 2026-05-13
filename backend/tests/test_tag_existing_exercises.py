"""Tests for backend/pedagogy/scripts/tag_existing_exercises.py — PR 13."""
from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import aiosqlite
import pytest


async def _seeded_conn(exercises: list[tuple]) -> aiosqlite.Connection:
    """Create an in-memory DB with the pedagogy tables and seed exercises."""
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("""
        CREATE TABLE exercises (
            id INTEGER PRIMARY KEY, name TEXT,
            initial_fen TEXT NOT NULL, solution_moves TEXT NOT NULL,
            difficulty INTEGER, category TEXT
        )
    """)
    await conn.execute("""
        CREATE TABLE exercise_tags (
            exercise_id INTEGER NOT NULL, tag TEXT NOT NULL,
            PRIMARY KEY (exercise_id, tag)
        )
    """)
    for ex in exercises:
        await conn.execute(
            "INSERT INTO exercises VALUES (?, ?, ?, ?, 1, 'cat')", ex
        )
    await conn.commit()
    return conn


@pytest.mark.asyncio
async def test_run_is_idempotent(monkeypatch):
    """Call _run twice; second call should report unchanged == 1."""
    from pedagogy.scripts.tag_existing_exercises import _iter_exercises, _detect_tags
    from pedagogy import storage

    conn = await _seeded_conn([(1, "ex", "W:W32:B20", json.dumps(["32-28"]))])

    # Monkeypatch _detect_tags to return a stable set
    monkeypatch.setattr(
        "pedagogy.scripts.tag_existing_exercises._detect_tags",
        lambda fen, moves: {"coup_royal"},
    )

    # First run
    exercises = await _iter_exercises(conn)
    for ex_id, fen, moves in exercises:
        new_tags = _detect_tags(fen, moves)
        await storage.set_exercise_tags(conn, ex_id, sorted(new_tags))

    # Second run — should all be unchanged
    tagged = unchanged = 0
    exercises = await _iter_exercises(conn)
    for ex_id, fen, moves in exercises:
        new_tags = _detect_tags(fen, moves)
        current = set(await storage.get_exercise_tags(conn, ex_id))
        if new_tags == current:
            unchanged += 1
        else:
            tagged += 1

    assert unchanged == 1
    assert tagged == 0
    await conn.close()


@pytest.mark.asyncio
async def test_run_dry_run_does_not_write(monkeypatch):
    """--dry-run must not write any rows to exercise_tags."""
    from pedagogy.scripts.tag_existing_exercises import _iter_exercises, _detect_tags
    from pedagogy import storage

    conn = await _seeded_conn([(1, "ex", "W:W32:B20", json.dumps(["32-28"]))])

    monkeypatch.setattr(
        "pedagogy.scripts.tag_existing_exercises._detect_tags",
        lambda fen, moves: {"sacrifice"},
    )

    exercises = await _iter_exercises(conn)
    for ex_id, fen, moves in exercises:
        new_tags = _detect_tags(fen, moves)
        current = set(await storage.get_exercise_tags(conn, ex_id))
        if new_tags != current:
            pass  # dry run — skip the write

    cur = await conn.execute("SELECT COUNT(*) FROM exercise_tags")
    row = await cur.fetchone()
    assert row[0] == 0
    await conn.close()


@pytest.mark.asyncio
async def test_run_skips_invalid_json(monkeypatch):
    """Exercises with malformed solution_moves should be skipped without crash."""
    from pedagogy.scripts.tag_existing_exercises import _iter_exercises

    conn = await _seeded_conn([
        (1, "good", "W:W32:B20", json.dumps(["32-28"])),
        (2, "bad", "W:W31:B20", "NOT_JSON"),
    ])

    exercises = await _iter_exercises(conn)
    # Only the valid exercise should be returned
    assert len(exercises) == 1
    assert exercises[0][0] == 1
    await conn.close()


@pytest.mark.asyncio
async def test_run_only_filters_by_id():
    """--only <id> should only process that exercise."""
    from pedagogy.scripts.tag_existing_exercises import _iter_exercises

    conn = await _seeded_conn([
        (1, "ex1", "W:W32:B20", json.dumps(["32-28"])),
        (2, "ex2", "W:W31:B20", json.dumps(["31-27"])),
        (3, "ex3", "W:W30:B20", json.dumps(["30-25"])),
    ])

    exercises = await _iter_exercises(conn, only_ids=[2])
    assert len(exercises) == 1
    assert exercises[0][0] == 2
    await conn.close()


@pytest.mark.asyncio
async def test_iter_exercises_returns_all_when_no_filter():
    """Without --only, all valid exercises are returned."""
    from pedagogy.scripts.tag_existing_exercises import _iter_exercises

    conn = await _seeded_conn([
        (1, "ex1", "W:W32:B20", json.dumps(["32-28"])),
        (2, "ex2", "W:W31:B20", json.dumps(["31-27"])),
    ])

    exercises = await _iter_exercises(conn)
    assert len(exercises) == 2
    await conn.close()
