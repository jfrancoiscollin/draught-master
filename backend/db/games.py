from __future__ import annotations
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

import aiosqlite

from .config import DB_PATH


async def save_game(
    game_id: str,
    date: str,
    white_player: str,
    black_player: str,
    result: Optional[str],
    pdn: str,
    fen_positions: List[str],
    move_count: int,
    user_id: Optional[int] = None,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO games
            (id, date, white_player, black_player, result, pdn, fen_positions, move_count, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (game_id, date, white_player, black_player, result, pdn, json.dumps(fen_positions), move_count, user_id),
        )
        await db.commit()


async def save_imported_game(
    game_id: str,
    user_id: int,
    date: str,
    white_player: str,
    black_player: str,
    result: Optional[str],
    pdn: str,
    move_count: int,
    source: str,
    source_id: Optional[str],
    user_side: Optional[str] = None,
) -> bool:
    """Insert a game imported from an external source.
    Returns True if inserted, False if already present (idempotent on
    (user_id, source, source_id)).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        if source_id:
            cur = await db.execute(
                "SELECT 1 FROM games WHERE user_id = ? AND source = ? AND source_id = ?",
                (user_id, source, source_id),
            )
            if await cur.fetchone():
                return False
        await db.execute(
            """
            INSERT OR IGNORE INTO games
            (id, date, white_player, black_player, result, pdn, fen_positions,
             move_count, user_id, source, source_id, user_side, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'finished')
            """,
            (
                game_id, date, white_player, black_player, result, pdn,
                json.dumps([]), move_count, user_id, source, source_id,
                user_side,
            ),
        )
        await db.commit()
        return True


async def count_user_games_by_source(user_id: int, source: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM games WHERE user_id = ? AND source = ?",
            (user_id, source),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def save_game_annotations(game_id: str, user_id: Optional[int], annotations: list) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE games
            SET annotations_json = ?,
                user_id = COALESCE(user_id, ?)
            WHERE id = ?
            """,
            (json.dumps(annotations), user_id, game_id),
        )
        await db.commit()


async def get_user_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, date, result, annotations_json
            FROM games
            WHERE user_id = ? AND annotations_json IS NOT NULL
            ORDER BY date DESC
            """,
            (user_id,),
        )
        rows = await cursor.fetchall()
        cur2 = await db.execute(
            "SELECT COUNT(*) FROM games WHERE user_id = ? AND source = 'lidraughts'",
            (user_id,),
        )
        lidraughts_count_row = await cur2.fetchone()
        games_from_lidraughts = int(lidraughts_count_row[0]) if lidraughts_count_row else 0

    total_games = 0
    total_moves = 0
    total_blunders = 0
    total_mistakes = 0
    total_inaccuracies = 0
    recent_games: list = []

    for row in rows:
        try:
            annotations = json.loads(row["annotations_json"])
        except Exception:
            continue
        if not annotations:
            continue

        total_games += 1
        n = len(annotations)
        b = sum(1 for a in annotations if a.get("verdict") == "blunder")
        m = sum(1 for a in annotations if a.get("verdict") == "mistake")
        i = sum(1 for a in annotations if a.get("verdict") == "inaccuracy")
        acc = round((n - b - m - i) / n * 100, 1) if n > 0 else 100.0

        total_moves += n
        total_blunders += b
        total_mistakes += m
        total_inaccuracies += i

        if len(recent_games) < 10:
            recent_games.append({
                "id": row["id"],
                "date": row["date"],
                "result": row["result"],
                "accuracy_pct": acc,
                "blunders": b,
                "mistakes": m,
                "inaccuracies": i,
                "move_count": n,
            })

    overall_acc = (
        round((total_moves - total_blunders - total_mistakes - total_inaccuracies) / total_moves * 100, 1)
        if total_moves > 0 else None
    )
    return {
        "total_games": total_games,
        "total_moves": total_moves,
        "blunders": total_blunders,
        "mistakes": total_mistakes,
        "inaccuracies": total_inaccuracies,
        "accuracy_pct": overall_acc,
        "recent_games": recent_games,
        "games_from_lidraughts": games_from_lidraughts,
    }


async def get_games(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM games ORDER BY date DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_game(game_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            data["fen_positions"] = json.loads(data["fen_positions"])
            return data
        return None


async def save_active_game(game_id: str, state_json: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO active_games (id, state_json, updated_at) VALUES (?, ?, ?)",
            (game_id, state_json, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def load_active_game(game_id: str) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT state_json FROM active_games WHERE id = ?", (game_id,))
        row = await cursor.fetchone()
        return row[0] if row else None


async def delete_active_game(game_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM active_games WHERE id = ?", (game_id,))
        await db.commit()
