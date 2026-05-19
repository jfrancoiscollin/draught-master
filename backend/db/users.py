from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any

import aiosqlite

from .config import DB_PATH


async def create_user(email: str, password_hash: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, password_hash, datetime.utcnow().isoformat()),
        )
        await db.commit()
        return cursor.lastrowid


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
