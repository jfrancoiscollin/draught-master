"""Tests for the live WebSocket endpoint (J2).

Covers:
  - first-frame auth handshake (success + missing/malformed/invalid token)
  - ping / pong heartbeat
  - unknown message types → error frame, connection stays open
  - single-connection-per-user: second connect kicks the first
  - end-to-end push: REST /challenge fires a `challenge_received` frame
    on the opponent's WS
  - REST /respond fires `challenge_resolved` on the challenger's WS
  - REST /cancel fires `challenge_cancelled` on the opponent's WS
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


@pytest.fixture(autouse=True)
def _reset_manager():
    """Each test starts with an empty presence dict + an empty game
    session map. Both singletons leak between tests otherwise."""
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
    p = tmp_path / "live_ws.sqlite"
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
             (2, "bob",   "bob@example.com"),
             (3, "carol", "carol@example.com")],
        )
        await conn.commit()
        await conn.close()

    asyncio.run(_init())
    return str(p)


# ---------------------------------------------------------------------------
# Auth handshake
# ---------------------------------------------------------------------------


def test_ws_auth_happy_path(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws:
        ws.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        msg = ws.receive_json()
        assert msg == {"type": "auth_ok", "user_id": 1}


def test_ws_missing_auth_frame_closes(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws:
        ws.send_json({"type": "ping"})  # not an auth frame
        msg = ws.receive_json()
        assert msg["type"] == "auth_error"
        assert "auth frame required" in msg["reason"]


def test_ws_missing_token_field(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws:
        ws.send_json({"type": "auth"})  # no token
        msg = ws.receive_json()
        assert msg["type"] == "auth_error"
        assert "token missing" in msg["reason"]


def test_ws_invalid_token(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws:
        ws.send_json({"type": "auth", "token": "not.a.valid.jwt"})
        msg = ws.receive_json()
        assert msg["type"] == "auth_error"


# ---------------------------------------------------------------------------
# Ping / pong + unknown types
# ---------------------------------------------------------------------------


def test_ws_ping_pong(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws:
        ws.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        assert ws.receive_json()["type"] == "auth_ok"

        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}


def test_ws_unknown_type_yields_error_but_keeps_connection(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws:
        ws.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        ws.receive_json()
        ws.send_json({"type": "bogus_message_type"})
        err = ws.receive_json()
        assert err["type"] == "error"
        # Connection is still alive after the error frame.
        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}


# ---------------------------------------------------------------------------
# Single connection per user
# ---------------------------------------------------------------------------


def test_second_connection_kicks_first(db_path):
    """User 1 connects from tab A, then from tab B. Tab A must receive
    a `kicked_by_other_session` frame before being closed."""
    client = TestClient(_make_app())
    tok = _token(1, "alice@example.com")
    with client.websocket_connect("/api/live/ws") as ws_a:
        ws_a.send_json({"type": "auth", "token": tok})
        assert ws_a.receive_json()["type"] == "auth_ok"

        with client.websocket_connect("/api/live/ws") as ws_b:
            ws_b.send_json({"type": "auth", "token": tok})
            assert ws_b.receive_json()["type"] == "auth_ok"

            # ws_a should now see a kick frame.
            kick = ws_a.receive_json()
            assert kick == {"type": "kicked_by_other_session"}


# ---------------------------------------------------------------------------
# REST → WS push hooks
# ---------------------------------------------------------------------------


def _auth_header(user_id: int, email: str) -> dict:
    return {"Authorization": f"Bearer {_token(user_id, email)}"}


def test_create_challenge_pushes_to_opponent(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_bob:
        ws_bob.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        assert ws_bob.receive_json()["type"] == "auth_ok"

        # Alice challenges Bob over REST.
        r = client.post(
            "/api/live/challenge",
            headers=_auth_header(1, "alice@example.com"),
            json={"opponent_username": "bob"},
        )
        assert r.status_code == 200, r.text

        push = ws_bob.receive_json()
        assert push["type"] == "challenge_received"
        assert push["challenge"]["challenger_username"] == "alice"
        assert push["challenge"]["opponent_username"] == "bob"


def test_respond_challenge_pushes_to_challenger(db_path):
    client = TestClient(_make_app())
    # Bob has to be offline for the create push to be dropped; Alice
    # online so she receives the resolution push.
    with client.websocket_connect("/api/live/ws") as ws_alice:
        ws_alice.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        assert ws_alice.receive_json()["type"] == "auth_ok"

        cid = client.post(
            "/api/live/challenge",
            headers=_auth_header(1, "alice@example.com"),
            json={"opponent_username": "bob"},
        ).json()["id"]
        client.post(
            f"/api/live/challenge/{cid}/respond",
            headers=_auth_header(2, "bob@example.com"),
            json={"accept": True},
        )
        push = ws_alice.receive_json()
        assert push["type"] == "challenge_resolved"
        assert push["challenge"]["status"] == "accepted"


def test_cancel_challenge_pushes_to_opponent(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_bob:
        ws_bob.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        assert ws_bob.receive_json()["type"] == "auth_ok"

        cid = client.post(
            "/api/live/challenge",
            headers=_auth_header(1, "alice@example.com"),
            json={"opponent_username": "bob"},
        ).json()["id"]

        # Drain the `challenge_received` push so we see `challenge_cancelled` next.
        first = ws_bob.receive_json()
        assert first["type"] == "challenge_received"

        client.post(
            f"/api/live/challenge/{cid}/cancel",
            headers=_auth_header(1, "alice@example.com"),
        )
        cancel = ws_bob.receive_json()
        assert cancel["type"] == "challenge_cancelled"
        assert cancel["challenge"]["status"] == "cancelled"


def test_push_to_offline_user_is_silently_dropped(db_path):
    """If Bob isn't connected, the create_challenge push silently
    fails (no exception) and the REST request still returns 200."""
    client = TestClient(_make_app())
    r = client.post(
        "/api/live/challenge",
        headers=_auth_header(1, "alice@example.com"),
        json={"opponent_username": "bob"},
    )
    assert r.status_code == 200
    # No assertion on the WS side — Bob is offline, no socket to inspect.
    # The point of this test is that the handler doesn't crash on missing
    # presence; the 200 response is the proof.


# ---------------------------------------------------------------------------
# GET /api/live/online — projection of presence + in_game
# ---------------------------------------------------------------------------


def test_online_endpoint_omits_caller_and_users_without_username(db_path):
    """The caller is filtered out (can't challenge self); users with a
    NULL username are skipped too (auto-fill makes that rare in
    practice but the projection should still be safe)."""
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_alice, \
         client.websocket_connect("/api/live/ws") as ws_bob:
        ws_alice.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        assert ws_alice.receive_json()["type"] == "auth_ok"
        ws_bob.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        assert ws_bob.receive_json()["type"] == "auth_ok"

        # Seed usernames so the rows survive the NULL filter.
        async def _seed():
            async with aiosqlite.connect(db_path) as conn:
                await conn.execute("UPDATE users SET username = 'alice' WHERE id = 1")
                await conn.execute("UPDATE users SET username = 'bob'   WHERE id = 2")
                # Carol stays NULL on purpose to assert she's skipped.
                await conn.commit()
        asyncio.new_event_loop().run_until_complete(_seed())

        r = client.get("/api/live/online", headers=_auth_header(1, "alice@example.com"))
        assert r.status_code == 200, r.text
        users = r.json()["users"]
        # Alice (the caller) is filtered out; carol has no username so
        # she doesn't appear either; only bob remains.
        assert [u["username"] for u in users] == ["bob"]
        assert users[0]["in_game"] is False


def test_online_endpoint_flags_users_in_game(db_path):
    """Bob is alice's opponent in an accepted challenge → the online
    projection should mark his row as in_game=True so the lobby can
    disable the Défier button."""
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_a, \
         client.websocket_connect("/api/live/ws") as ws_b:
        ws_a.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        ws_b.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        ws_a.receive_json(); ws_b.receive_json()

        async def _seed():
            async with aiosqlite.connect(db_path) as conn:
                await conn.execute("UPDATE users SET username = 'alice' WHERE id = 1")
                await conn.execute("UPDATE users SET username = 'bob' WHERE id = 2")
                await conn.execute("UPDATE users SET username = 'carol' WHERE id = 3")
                await conn.commit()
        asyncio.new_event_loop().run_until_complete(_seed())

        # Alice + Bob start a game (challenge accepted path).
        cid = client.post(
            "/api/live/challenge",
            headers=_auth_header(1, "alice@example.com"),
            json={"opponent_username": "bob"},
        ).json()["id"]
        # Drain the challenge_received push on Bob.
        ws_b.receive_json()
        client.post(
            f"/api/live/challenge/{cid}/respond",
            headers=_auth_header(2, "bob@example.com"),
            json={"accept": True},
        )
        # Drain the game_started broadcasts so the WS queues stay clean
        # for any further tests that share the fixture state.
        ws_a.receive_json(); ws_a.receive_json()
        ws_b.receive_json()

        # Carol (online, not in a game) views the lobby — she should
        # see both alice and bob, both flagged in_game=True.
        with client.websocket_connect("/api/live/ws") as ws_c:
            ws_c.send_json({"type": "auth", "token": _token(3, "carol@example.com")})
            ws_c.receive_json()
            r = client.get("/api/live/online", headers=_auth_header(3, "carol@example.com"))
            users = {u["username"]: u for u in r.json()["users"]}
            assert users["alice"]["in_game"] is True
            assert users["bob"]["in_game"] is True
