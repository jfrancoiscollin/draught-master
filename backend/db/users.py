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
        cursor = await db.execute("SELECT id, email, created_at FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


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
