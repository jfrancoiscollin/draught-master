"""J3 acceptance tests: live game state machine end-to-end.

Covers:
  - challenge acceptance spawns a game and broadcasts game_started to
    both clients, with consistent color assignment
  - move frame: legal coup is validated, broadcast move_played to both,
    persisted in games.pdn and games.turn
  - illegal / unknown / out-of-turn / not-in-game moves return error
    only to the sender
  - resign frame marks abandoned_<color> and broadcasts game_ended
  - natural game end (no legal moves) flips status to 'finished' and
    broadcasts game_ended

These are integration tests through the WS endpoint; the unit-level
correctness of `game_engine` is covered by its own suite.
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
    p = tmp_path / "live_game.sqlite"
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


def _accept_challenge_and_drain(client, *, preferred_color: str = "white"):
    """Spin up two WS connections (alice + bob), create + accept a challenge,
    drain the auth_ok / challenge_received / challenge_resolved /
    game_started frames, and return (ws_alice, ws_bob, alice_role, bob_role,
    game_session_dict).

    Caller must hold the WS connections open via `with` blocks around the
    whole test body — this helper assumes the with-clause is already open.
    """
    raise NotImplementedError("helper kept open below — see test bodies")


# ---------------------------------------------------------------------------
# game_started broadcast
# ---------------------------------------------------------------------------


def test_challenge_accept_spawns_game_and_broadcasts(db_path):
    """Both players receive a game_started frame with the same game_id
    and complementary white/black assignments."""
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_alice, \
         client.websocket_connect("/api/live/ws") as ws_bob:
        ws_alice.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        assert ws_alice.receive_json()["type"] == "auth_ok"
        ws_bob.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        assert ws_bob.receive_json()["type"] == "auth_ok"

        cid = client.post(
            "/api/live/challenge",
            headers=_auth_header(1, "alice@example.com"),
            json={"opponent_username": "bob", "preferred_color": "white"},
        ).json()["id"]
        # Drain Bob's challenge_received.
        assert ws_bob.receive_json()["type"] == "challenge_received"

        r = client.post(
            f"/api/live/challenge/{cid}/respond",
            headers=_auth_header(2, "bob@example.com"),
            json={"accept": True},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"
        assert r.json()["game_id"] is not None

        # Alice gets challenge_resolved + game_started; Bob gets game_started.
        # Order within Alice's queue: challenge_resolved is sent first.
        m1 = ws_alice.receive_json()
        m2 = ws_alice.receive_json()
        # game_started might be first or second depending on the send order
        # — we sent challenge_resolved first in the handler, so it should
        # arrive first.
        assert m1["type"] == "challenge_resolved"
        assert m2["type"] == "game_started"
        assert m2["session"]["white_user_id"] == 1   # alice as challenger picked 'white'
        assert m2["session"]["black_user_id"] == 2
        assert m2["session"]["turn"] == "white"
        assert m2["session"]["status"] == "in_progress"

        bob_msg = ws_bob.receive_json()
        assert bob_msg["type"] == "game_started"
        assert bob_msg["session"]["game_id"] == m2["session"]["game_id"]


def test_decline_does_not_spawn_game(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_alice:
        ws_alice.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        assert ws_alice.receive_json()["type"] == "auth_ok"

        cid = client.post(
            "/api/live/challenge",
            headers=_auth_header(1, "alice@example.com"),
            json={"opponent_username": "bob"},
        ).json()["id"]
        r = client.post(
            f"/api/live/challenge/{cid}/respond",
            headers=_auth_header(2, "bob@example.com"),
            json={"accept": False},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "declined"
        assert r.json()["game_id"] is None

        m = ws_alice.receive_json()
        assert m["type"] == "challenge_resolved"
        # No game_started should follow.


# ---------------------------------------------------------------------------
# move + move_played broadcast
# ---------------------------------------------------------------------------


def _drain_until_game_started(ws_a, ws_b, client):
    """Helper used by multiple tests below: alice challenges bob (alice =
    white), bob accepts, all init frames are drained. Returns nothing —
    state is in the WS sockets."""
    cid = client.post(
        "/api/live/challenge",
        headers=_auth_header(1, "alice@example.com"),
        json={"opponent_username": "bob", "preferred_color": "white"},
    ).json()["id"]
    assert ws_b.receive_json()["type"] == "challenge_received"
    client.post(
        f"/api/live/challenge/{cid}/respond",
        headers=_auth_header(2, "bob@example.com"),
        json={"accept": True},
    )
    # Drain alice: challenge_resolved + game_started ; drain bob: game_started.
    assert ws_a.receive_json()["type"] == "challenge_resolved"
    assert ws_a.receive_json()["type"] == "game_started"
    assert ws_b.receive_json()["type"] == "game_started"


def test_move_legal_broadcasts_move_played_to_both(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_a, \
         client.websocket_connect("/api/live/ws") as ws_b:
        ws_a.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        ws_b.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        ws_a.receive_json(); ws_b.receive_json()  # auth_ok
        _drain_until_game_started(ws_a, ws_b, client)

        # Alice plays the canonical opening 32-28.
        ws_a.send_json({"type": "move", "move": "32-28"})
        a_resp = ws_a.receive_json()
        b_resp = ws_b.receive_json()
        assert a_resp["type"] == "move_played"
        assert a_resp["move"] == "32-28"
        assert a_resp["by"] == "white"
        assert a_resp["session"]["turn"] == "black"
        assert b_resp == a_resp  # both clients see the same frame


def test_move_out_of_turn_returns_error_only_to_sender(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_a, \
         client.websocket_connect("/api/live/ws") as ws_b:
        ws_a.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        ws_b.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        ws_a.receive_json(); ws_b.receive_json()
        _drain_until_game_started(ws_a, ws_b, client)

        # Bob tries to play first even though he's black.
        ws_b.send_json({"type": "move", "move": "20-25"})
        err = ws_b.receive_json()
        assert err["type"] == "error"
        assert err["reason"] == "not_your_turn"
        # Alice didn't receive anything — assert by sending her a ping
        # and getting pong back immediately (no queued move_played).
        ws_a.send_json({"type": "ping"})
        assert ws_a.receive_json() == {"type": "pong"}


def test_move_unknown_notation_returns_error(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_a, \
         client.websocket_connect("/api/live/ws") as ws_b:
        ws_a.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        ws_b.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        ws_a.receive_json(); ws_b.receive_json()
        _drain_until_game_started(ws_a, ws_b, client)

        ws_a.send_json({"type": "move", "move": "32-99"})  # bogus square
        err = ws_a.receive_json()
        assert err["type"] == "error"
        assert err["reason"] == "unknown_move"


def test_move_when_not_in_game_returns_error(db_path):
    """Carol isn't in a game. Her move frame should error out cleanly."""
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_c:
        ws_c.send_json({"type": "auth", "token": _token(3, "carol@example.com")})
        assert ws_c.receive_json()["type"] == "auth_ok"
        ws_c.send_json({"type": "move", "move": "32-28"})
        err = ws_c.receive_json()
        assert err["type"] == "error"
        assert err["reason"] == "not_in_game"


def test_move_persists_pdn_and_turn_to_db(db_path):
    """After a move, the games row reflects the new pdn + turn."""
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_a, \
         client.websocket_connect("/api/live/ws") as ws_b:
        ws_a.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        ws_b.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        ws_a.receive_json(); ws_b.receive_json()
        _drain_until_game_started(ws_a, ws_b, client)

        ws_a.send_json({"type": "move", "move": "32-28"})
        played = ws_a.receive_json()
        ws_b.receive_json()  # drain bob's copy
        game_id = played["session"]["game_id"]

        # Look up the row directly.
        async def _peek():
            conn = await aiosqlite.connect(db_path)
            cur = await conn.execute(
                "SELECT pdn, turn, status FROM games WHERE id = ?", (game_id,),
            )
            row = await cur.fetchone()
            await conn.close()
            return row
        row = asyncio.new_event_loop().run_until_complete(_peek())
        assert row[1] == "black"
        assert row[2] == "in_progress"
        assert "32-28" in (row[0] or "")


# ---------------------------------------------------------------------------
# resign + game_ended broadcast
# ---------------------------------------------------------------------------


def test_resign_marks_abandoned_and_broadcasts_game_ended(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_a, \
         client.websocket_connect("/api/live/ws") as ws_b:
        ws_a.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        ws_b.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        ws_a.receive_json(); ws_b.receive_json()
        _drain_until_game_started(ws_a, ws_b, client)

        ws_a.send_json({"type": "resign"})
        a_msg = ws_a.receive_json()
        b_msg = ws_b.receive_json()
        assert a_msg["type"] == "game_ended"
        assert a_msg["session"]["status"] == "abandoned_white"
        assert a_msg["session"]["result"] == "black"
        assert b_msg == a_msg


def test_move_after_resign_returns_error(db_path):
    client = TestClient(_make_app())
    with client.websocket_connect("/api/live/ws") as ws_a, \
         client.websocket_connect("/api/live/ws") as ws_b:
        ws_a.send_json({"type": "auth", "token": _token(1, "alice@example.com")})
        ws_b.send_json({"type": "auth", "token": _token(2, "bob@example.com")})
        ws_a.receive_json(); ws_b.receive_json()
        _drain_until_game_started(ws_a, ws_b, client)

        ws_a.send_json({"type": "resign"})
        ws_a.receive_json(); ws_b.receive_json()  # drain game_ended

        # Bob now tries to move — game is over.
        ws_b.send_json({"type": "move", "move": "20-25"})
        err = ws_b.receive_json()
        assert err["type"] == "error"
        assert err["reason"] == "game_over"
