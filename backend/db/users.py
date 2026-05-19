from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any

import aiosqlite

from .config import DB_PATH


async def create_user(
    email: str, password_hash: str, username: Optional[str] = None,
) -> int:
    """Insert a new user row. ``username`` is optional here so the
    legacy /register call sites (none after the signup-username
    landed, but kept for safety) still compile; the new register
    flow always passes it. Case-insensitive uniqueness is enforced
    by ``idx_users_username_nocase`` — the IntegrityError surfaces
    up if the caller didn't pre-check."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO users (email, password_hash, created_at, username) "
            "VALUES (?, ?, ?, ?)",
            (email, password_hash, datetime.utcnow().isoformat(), username),
        )
        await db.commit()
        return cursor.lastrowid


async def delete_user(user_id: int) -> None:
    """Wipe a user account and every row that points at it.

    SQLite doesn't enforce ``ON DELETE CASCADE`` unless
    ``PRAGMA foreign_keys = ON`` is set on every connection, and we
    don't currently set it everywhere — so we do the cascade in
    Python rather than rely on the declared FKs. Done in one
    transaction so a partial failure doesn't leave orphans.

    Tables touched, in order:
      - move_verdicts via the games CASCADE (still relies on the
        FK pragma, but live games + imports both go through games.id
        so deleting the games rows is enough either way)
      - pedagogy_explanations same story (CASCADE off move_verdicts)
      - live_challenges where the user is either side
      - games where the user is owner OR white OR black
      - user_exercise_solved
      - user_lesson_read
      - password_reset_tokens (by email)
      - users itself

    Idempotent: deleting a non-existent user is a no-op (returns
    without raising).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        # Look up email for the password-reset cleanup before nuking
        # the row.
        cur = await db.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            return
        email = str(row[0])

        # Live challenges where the user is either party.
        await db.execute(
            "DELETE FROM live_challenges WHERE challenger_id = ? OR opponent_id = ?",
            (user_id, user_id),
        )
        # Games owned by or featuring this user — kind='imported' uses
        # user_id; kind='live' uses white_user_id / black_user_id.
        # CASCADE on games.id removes move_verdicts (and through it,
        # pedagogy_explanations) when the FK pragma above is honoured.
        await db.execute(
            "DELETE FROM games "
            " WHERE user_id = ? OR white_user_id = ? OR black_user_id = ?",
            (user_id, user_id, user_id),
        )
        # User-level progress tables (no CASCADE declared).
        await db.execute("DELETE FROM user_exercise_solved WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM user_lesson_read WHERE user_id = ?", (user_id,))
        # Pending password-reset tokens. Keyed by email since the
        # schema doesn't have a user_id column.
        await db.execute("DELETE FROM password_reset_tokens WHERE email = ?", (email,))
        # Finally the user.
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()


async def username_is_taken(username: str) -> bool:
    """Case-insensitive lookup used by /register to pre-check before
    creating the user, so we can return a clean 409 instead of letting
    the unique-index IntegrityError bubble up."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM users WHERE LOWER(username) = LOWER(?) LIMIT 1",
            (username,),
        )
        return await cur.fetchone() is not None


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, email, created_at, lidraughts_username, username FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def set_lidraughts_username(user_id: int, username: Optional[str]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET lidraughts_username = ? WHERE id = ?",
            (username, user_id),
        )
        await db.commit()


_USERNAME_RE = __import__("re").compile(r"^[A-Za-z0-9_-]{2,30}$")


async def set_username(user_id: int, username: str) -> Optional[str]:
    """Persist the display username used by Live PvP and other social
    surfaces. Returns ``None`` on success, an error slug otherwise:

      ``invalid``  → fails the [A-Za-z0-9_-]{2,30} regex
      ``taken``    → another user has the same case-insensitive value

    Case-insensitive uniqueness is enforced by ``idx_users_username_nocase``
    in db/schema.py; we still pre-check so we can return a clean
    error code instead of letting the IntegrityError bubble up to the
    API layer.
    """
    if not _USERNAME_RE.match(username):
        return "invalid"
    async with aiosqlite.connect(DB_PATH) as db:
        # Detect collision with someone else's username.
        cur = await db.execute(
            "SELECT id FROM users WHERE LOWER(username) = LOWER(?) AND id != ?",
            (username, user_id),
        )
        if await cur.fetchone() is not None:
            return "taken"
        await db.execute(
            "UPDATE users SET username = ? WHERE id = ?",
            (username, user_id),
        )
        await db.commit()
    return None


async def ensure_default_username(user_id: int) -> Optional[str]:
    """Auto-populate ``users.username`` from the email local-part on
    the user's first ``GET /api/auth/me`` post-migration. Idempotent —
    no-op when the row already has one.

    Collision handling: the local-part is sanitised against
    :data:`_USERNAME_RE`, then suffixed ``_1``, ``_2``, … until the
    case-insensitive unique constraint is satisfied. Returns the
    resolved username (or ``None`` if the user doesn't exist).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT username, email FROM users WHERE id = ?", (user_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        if row["username"]:
            return str(row["username"])
        email = str(row["email"] or "")
        base = email.split("@", 1)[0]
        # Strip characters the regex rejects so we don't fight ourselves
        # in the suffix loop. Two-char minimum: pad with 'u' if too
        # short post-sanitisation.
        sanitised = "".join(c for c in base if c.isalnum() or c in "_-") or "u"
        if len(sanitised) < 2:
            sanitised += "u"
        sanitised = sanitised[:28]  # leave room for a 2-digit suffix
        candidate = sanitised
        i = 0
        while True:
            collision = await (await db.execute(
                "SELECT id FROM users WHERE LOWER(username) = LOWER(?) AND id != ?",
                (candidate, user_id),
            )).fetchone()
            if collision is None:
                break
            i += 1
            candidate = f"{sanitised}_{i}"
        await db.execute(
            "UPDATE users SET username = ? WHERE id = ?", (candidate, user_id),
        )
        await db.commit()
    return candidate


async def create_reset_token(email: str, token: str, expires_at: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM password_reset_tokens WHERE email = ?", (email,)
        )
        await db.execute(
            "INSERT INTO password_reset_tokens (email, token, expires_at) VALUES (?, ?, ?)",
            (email, token, expires_at),
        )
        await db.commit()


async def get_reset_token(token: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM password_reset_tokens WHERE token = ? AND used = 0", (token,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def consume_reset_token(token: str, new_password_hash: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT email FROM password_reset_tokens WHERE token = ? AND used = 0", (token,)
        )
        row = await cursor.fetchone()
        if not row:
            return False
        email = row[0]
        await db.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?", (new_password_hash, email)
        )
        await db.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE token = ?", (token,)
        )
        await db.commit()
        return True


async def mark_lesson_read(user_id: int, chapter: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO user_lesson_read (user_id, chapter, read_at)
            VALUES (?, ?, ?)
            """,
            (user_id, chapter, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def get_user_read_lesson_chapters(user_id: int) -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT chapter FROM user_lesson_read WHERE user_id = ?",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
