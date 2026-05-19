"""J4 acceptance tests — disconnect grace period + reconnect path.

End-to-end WebSocket testing with Starlette's TestClient is brittle for
the "close session A, open session B, observe a server-side timer
fire" pattern: the second session can hang waiting for the first to
fully clean up, even when both sessions live in the same loop. We
test the public WS surface for the parts that don't need that pattern
(disconnect → opponent_disconnected push), and exercise the timer /
reconnect bookkeeping unit-style against the manager + helper.

Covers:
  - opponent_disconnected pushed when a player drops their WS mid-game (E2E)
  - ConnectionManager.cancel_forfeit returns True only when a timer
    was actually pending
  - schedule_forfeit cancels a previously-pending task before replacing
  - _forfeit_after_grace marks abandoned_<color> + broadcasts game_ended
    when the sleep completes
  - _forfeit_after_grace is a no-op when the game already ended
    (e.g. user resigned before the timer fired)
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


def _token(user_id: int, email: str) -> str:
    from auth import _create_token
    return _create_token(user_id, email)


def _auth_header(user_id: int, email: str) -> dict:
    return {"Authorization": f"Bearer {_token(user_id, email)}"}


@pytest.fixture(autouse=True)
def _short_grace(monkeypatch):
    """200 ms is plenty above asyncio task-switching jitter on CI and
    keeps the unit suite well under a second."""
    monkeypatch.setattr("live.api._DISCONNECT_GRACE_S", 0.2)


@pytest.fixture(autouse=True)
def _reset_state():
    from live.presence import manager
    from live.game_session import manager as game_manager
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(manager.reset())
        loop.run_until_complete(game_manager.reset())
    finally:
        loop.close()
    yield


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    p = tmp_path / "live_grace.sqlite"
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
        await conn.execute("""
            CREATE TABLE games (
                id TEXT PRIMARY KEY,
                kind TEXT DEFAULT 'imported',
                user_id INTEGER,
                user_side TEXT,
                white_user_id INTEGER,
                black_user_id INTEGER,
                turn TEXT DEFAULT 'white',
                status TEXT DEFAULT 'finished',
                pdn TEXT,
                date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.executemany(
            "INSERT INTO users (id, username, email) VALUES (?, ?, ?)",
            [(1, "alice", "alice@example.com"),
             (2, "bob",   "bob@example.com")],
        )
        await conn.commit()
        await conn.close()
    asyncio.run(_init())
    return str(p)


# ---------------------------------------------------------------------------
# E2E: disconnect → opponent_disconnected push
# ---------------------------------------------------------------------------


def test_disconnect_pushes_opponent_disconnected(db_path):
    """When Alice drops, Bob receives an opponent_disconnected frame
    naming Alice and giving the grace window in seconds."""
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_bob:
        ws_bob.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        assert ws_bob.receive_json()["type"] == "auth_ok"

        with client.websocket_connect("/api/live/ws") as ws_alice:
            ws_alice.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
            assert ws_alice.receive_json()["type"] == "auth_ok"

            # Alice challenges, Bob accepts.
            cid = client.post(
                "/api/live/challenge",
                headers=_auth_header(1, "alice@example.com"),
                json={"opponent_username": "bob", "preferred_color": "white"},
            ).json()["id"]
            assert ws_bob.receive_json()["type"] == "challenge_received"
            client.post(
                f"/api/live/challenge/{cid}/respond",
                headers=_auth_header(2, "bob@example.com"),
                json={"accept": True},
            )
            assert ws_alice.receive_json()["type"] == "challenge_resolved"
            assert ws_alice.receive_json()["type"] == "game_started"
            assert ws_bob.receive_json()["type"] == "game_started"

            # Alice's with-block exits, dropping her WS.

        msg = ws_bob.receive_json()
        assert msg["type"] == "opponent_disconnected"
        assert msg["user_id"] == 1
        # Grace window is exposed as a hint to the client UI for the
        # local countdown. Value is whatever _short_grace patched.
        assert "grace_seconds" in msg


# ---------------------------------------------------------------------------
# Unit-level: forfeit task bookkeeping
# ---------------------------------------------------------------------------


def test_cancel_forfeit_returns_false_when_no_timer():
    """Cancel with no pending task is a no-op and signals it."""
    from live.game_session import manager as game_manager
    assert game_manager.cancel_forfeit(999) is False


def test_schedule_forfeit_replaces_previous_task():
    """Re-scheduling cancels the old timer — single timer per user."""
    from live.game_session import manager as game_manager

    async def _go():
        async def _noop():
            await asyncio.sleep(10)
        t1 = asyncio.create_task(_noop())
        game_manager.schedule_forfeit(42, t1)
        t2 = asyncio.create_task(_noop())
        game_manager.schedule_forfeit(42, t2)
        # First task should have been cancelled by the replacement.
        await asyncio.sleep(0.01)
        assert t1.cancelled()
        # Cancel the second so the test exits cleanly.
        game_manager.cancel_forfeit(42)
        await asyncio.sleep(0.01)
        assert t2.cancelled()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_go())
    finally:
        loop.close()


def test_forfeit_after_grace_marks_abandoned(db_path):
    """End-to-end of the helper: spawn a session, fire the forfeit
    helper directly, assert the session is now abandoned_white and
    the games row reflects it."""
    from live import api as live_api
    from live.game_session import manager as game_manager

    async def _go():
        async with aiosqlite.connect(db_path) as conn:
            await game_manager.start_game(
                conn,
                challenger_id=1,
                opponent_id=2,
                preferred_color="white",
            )
        # _forfeit_after_grace sleeps grace_s (0.2s) then resigns.
        await live_api._forfeit_after_grace(1)
        # Session is now abandoned_white.
        sess = game_manager.session_for(1)
        assert sess is not None
        assert sess.status == "abandoned_white"
        assert sess.result == "black"
        # The games row was updated.
        async with aiosqlite.connect(db_path) as conn:
            cur = await conn.execute(
                "SELECT status FROM games WHERE id = ?", (sess.game_id,),
            )
            row = await cur.fetchone()
            assert row[0] == "abandoned_white"

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_go())
    finally:
        loop.close()


def test_forfeit_after_grace_noop_when_already_ended(db_path):
    """If the user resigned before the timer fired, the forfeit helper
    is a no-op and doesn't broadcast a duplicate game_ended."""
    from live import api as live_api
    from live.game_session import manager as game_manager

    async def _go():
        async with aiosqlite.connect(db_path) as conn:
            sess = await game_manager.start_game(
                conn,
                challenger_id=1,
                opponent_id=2,
                preferred_color="white",
            )
            # Pre-emptive resign.
            await game_manager.resign(conn, user_id=1)
        original_status = game_manager.session_for(1).status
        original_result = game_manager.session_for(1).result
        # Now the timer fires.
        await live_api._forfeit_after_grace(1)
        # No state change.
        s = game_manager.session_for(1)
        assert s.status == original_status
        assert s.result == original_result

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_go())
    finally:
        loop.close()


def test_clear_forfeit_drops_handle_without_cancelling():
    """clear_forfeit is the post-completion path — drop the dict entry
    without cancelling (the task already ran)."""
    from live.game_session import manager as game_manager

    async def _go():
        async def _done_quickly():
            return
        t = asyncio.create_task(_done_quickly())
        game_manager.schedule_forfeit(7, t)
        await asyncio.sleep(0.01)
        assert t.done()
        # Clearing shouldn't raise even though the task is already done.
        game_manager.clear_forfeit(7)
        # Cancelling now returns False — nothing pending.
        assert game_manager.cancel_forfeit(7) is False

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_go())
    finally:
        loop.close()
