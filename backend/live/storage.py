"""SQLite helpers for the live_challenges table.

Stays a thin layer: every function takes an `aiosqlite.Connection` from
the caller (the route handler owns the lifecycle). No business rules
here — those live in api.py.
"""

from __future__ import annotations

import secrets
from typing import Any, Optional

import aiosqlite


def _new_challenge_id() -> str:
    """Short opaque id, URL-safe, ~96 bits of entropy. Plenty for a
    challenge queue that's pruned within minutes."""
    return secrets.token_urlsafe(12)


async def insert_challenge(
    conn: aiosqlite.Connection,
    *,
    challenger_id: int,
    opponent_id: int,
    preferred_color: str,
) -> str:
    """Insert a fresh pending challenge, return its id."""
    cid = _new_challenge_id()
    await conn.execute(
        """
        INSERT INTO live_challenges
            (id, challenger_id, opponent_id, preferred_color, status)
        VALUES (?, ?, ?, ?, 'pending')
        """,
        (cid, challenger_id, opponent_id, preferred_color),
    )
    await conn.commit()
    return cid


async def fetch_challenge(
    conn: aiosqlite.Connection, challenge_id: str
) -> Optional[dict[str, Any]]:
    """Single-row fetch by id. Returns the row + the two usernames so
    the route handler can build a ChallengeOut without N+1 lookups."""
    cur = await conn.execute(
        """
        SELECT c.id, c.challenger_id, c.opponent_id, c.preferred_color,
               c.status, c.created_at, c.resolved_at, c.game_id,
               cu.username AS challenger_username,
               ou.username AS opponent_username
          FROM live_challenges c
          JOIN users cu ON cu.id = c.challenger_id
          JOIN users ou ON ou.id = c.opponent_id
         WHERE c.id = ?
        """,
        (challenge_id,),
    )
    row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


async def fetch_pending_for_user(
    conn: aiosqlite.Connection, user_id: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (received, sent) pending-challenge lists for one user."""
    base = """
        SELECT c.id, c.challenger_id, c.opponent_id, c.preferred_color,
               c.status, c.created_at, c.resolved_at, c.game_id,
               cu.username AS challenger_username,
               ou.username AS opponent_username
          FROM live_challenges c
          JOIN users cu ON cu.id = c.challenger_id
          JOIN users ou ON ou.id = c.opponent_id
         WHERE c.status = 'pending' AND {who} = ?
         ORDER BY c.created_at DESC
    """
    rec_cur = await conn.execute(base.format(who="c.opponent_id"), (user_id,))
    received = [_row_to_dict(r) for r in await rec_cur.fetchall()]
    snt_cur = await conn.execute(base.format(who="c.challenger_id"), (user_id,))
    sent = [_row_to_dict(r) for r in await snt_cur.fetchall()]
    return received, sent


async def update_status(
    conn: aiosqlite.Connection,
    challenge_id: str,
    status: str,
    *,
    game_id: Optional[str] = None,
) -> None:
    """Move a challenge from 'pending' to a terminal state. Stamps
    resolved_at and (optionally) links the spawned game."""
    await conn.execute(
        """
        UPDATE live_challenges
           SET status = ?, resolved_at = CURRENT_TIMESTAMP, game_id = ?
         WHERE id = ?
        """,
        (status, game_id, challenge_id),
    )
    await conn.commit()


async def find_user_by_username(
    conn: aiosqlite.Connection, username: str
) -> Optional[dict[str, Any]]:
    """Case-insensitive lookup. Returns {id, username} or None."""
    cur = await conn.execute(
        "SELECT id, username FROM users WHERE LOWER(username) = LOWER(?)",
        (username,),
    )
    row = await cur.fetchone()
    if row is None:
        return None
    return {"id": int(row[0]), "username": str(row[1])}


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Hand-roll the dict — aiosqlite Row mapping behaviour depends on
    whether row_factory was set, which it isn't here. Positions match
    the SELECT lists above."""
    return {
        "id":                  str(row[0]),
        "challenger_id":       int(row[1]),
        "opponent_id":         int(row[2]),
        "preferred_color":     str(row[3]),
        "status":              str(row[4]),
        "created_at":          str(row[5]),
        "resolved_at":         str(row[6]) if row[6] is not None else None,
        "game_id":             str(row[7]) if row[7] is not None else None,
        "challenger_username": str(row[8]),
        "opponent_username":   str(row[9]),
    }
