from __future__ import annotations
import json
import re as _re
from datetime import datetime
from typing import Optional, List, Dict, Any

import aiosqlite

from .config import DB_PATH


def _extract_chapter(description: str) -> Optional[int]:
    m = _re.search(r'Chapitre\s+(\d+)', description or "")
    return int(m.group(1)) if m else None


async def get_exercises(
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    book_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM exercises WHERE 1=1"
        params: List[Any] = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if difficulty is not None:
            query += " AND difficulty = ?"
            params.append(difficulty)
        if book_id is not None:
            query += " AND book_id = ?"
            params.append(book_id)
        query += " ORDER BY difficulty ASC, id ASC"
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["solution_moves"] = json.loads(data["solution_moves"])
            data["chapter"] = _extract_chapter(data.get("description", ""))
            result.append(data)
        return result


async def get_exercise(exercise_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,))
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            data["solution_moves"] = json.loads(data["solution_moves"])
            data["chapter"] = _extract_chapter(data.get("description", ""))
            return data
        return None


async def save_exercise(exercise: Dict[str, Any]) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO exercises (name, description, initial_fen, solution_moves, difficulty, category, hint)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exercise["name"],
                exercise.get("description", ""),
                exercise["initial_fen"],
                json.dumps(exercise.get("solution_moves", [])),
                exercise.get("difficulty", 1),
                exercise.get("category", "general"),
                exercise.get("hint", ""),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def record_progress(exercise_id: int, solved: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, attempts, solved FROM user_progress WHERE exercise_id = ?",
            (exercise_id,),
        )
        row = await cursor.fetchone()
        if row:
            new_solved = 1 if (row[2] or solved) else 0
            date_solved = datetime.utcnow().isoformat() if solved and not row[2] else None
            await db.execute(
                "UPDATE user_progress SET attempts = attempts + 1, solved = ?, date_solved = COALESCE(date_solved, ?) WHERE id = ?",
                (new_solved, date_solved, row[0]),
            )
        else:
            date_solved = datetime.utcnow().isoformat() if solved else None
            await db.execute(
                "INSERT INTO user_progress (exercise_id, attempts, solved, date_solved) VALUES (?, 1, ?, ?)",
                (exercise_id, 1 if solved else 0, date_solved),
            )
        await db.commit()


async def mark_exercise_solved(user_id: int, exercise_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO user_exercise_solved (user_id, exercise_id, solved_at)
            VALUES (?, ?, ?)
            """,
            (user_id, exercise_id, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def get_user_solved_exercise_ids(user_id: int) -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT exercise_id FROM user_exercise_solved WHERE user_id = ?",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
