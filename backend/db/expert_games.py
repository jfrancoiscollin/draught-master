"""CRUD for the expert_games table (NNUE training corpus)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from .config import DB_PATH

logger = logging.getLogger(__name__)


def _parse_ndjson_game(obj: dict) -> dict[str, Any] | None:
    """Extract a storable record from one Lidraughts NDJSON game object.

    Returns None if the game lacks moves (unusable for training).
    """
    moves = (obj.get("moves") or obj.get("pdn") or obj.get("pgn")
             or obj.get("notation") or "").strip()
    if not moves:
        return None

    players = obj.get("players", {})
    wp = players.get("white", {})
    bp = players.get("black", {})
    white_name = (wp.get("user", {}).get("name") or wp.get("name") or "?")
    black_name  = (bp.get("user", {}).get("name") or bp.get("name") or "?")
    white_rating = wp.get("rating") or wp.get("user", {}).get("rating")
    black_rating  = bp.get("rating") or bp.get("user", {}).get("rating")

    winner = obj.get("winner", "")
    if winner == "white":
        result = "1-0"
    elif winner == "black":
        result = "0-1"
    else:
        result = "1/2-1/2"

    # Date: createdAt is milliseconds since epoch on Lidraughts
    date: str | None = None
    ts = obj.get("createdAt")
    if ts:
        try:
            date = datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            pass

    num_plies = len(moves.split())
    variant = obj.get("variant", {}).get("key", "standard") if isinstance(obj.get("variant"), dict) else "standard"

    pdn = (
        f'[Event "{obj.get("event") or "?"}"]\n'
        f'[White "{white_name}"]\n'
        f'[Black "{black_name}"]\n'
        f'[Result "{result}"]\n'
        + (f'[WhiteElo "{white_rating}"]\n' if white_rating else "")
        + (f'[BlackElo "{black_rating}"]\n' if black_rating else "")
        + (f'[Date "{date}"]\n' if date else "")
        + f'\n{moves}\n'
    )

    return {
        "source": "lidraughts",
        "source_id": obj.get("id"),
        "date": date,
        "white_name": white_name,
        "black_name": black_name,
        "white_rating": white_rating,
        "black_rating": black_rating,
        "result": result,
        "num_plies": num_plies,
        "event": obj.get("event") or obj.get("tournamentId"),
        "variant": variant,
        "pdn": pdn,
    }


async def ingest_ndjson(ndjson_text: str) -> dict[str, int]:
    """Parse Lidraughts NDJSON and INSERT OR IGNORE into expert_games.

    Returns {"inserted": N, "skipped": N, "errors": N}.
    """
    inserted = skipped = errors = 0
    records: list[dict] = []

    for line in ndjson_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            rec = _parse_ndjson_game(obj)
            if rec is None:
                skipped += 1
            else:
                records.append(rec)
        except Exception as exc:
            logger.debug("ingest_ndjson: parse error: %s", exc)
            errors += 1

    if not records:
        return {"inserted": 0, "skipped": skipped, "errors": errors}

    async with aiosqlite.connect(DB_PATH) as db:
        for rec in records:
            try:
                cur = await db.execute(
                    """
                    INSERT OR IGNORE INTO expert_games
                        (source, source_id, date, white_name, black_name,
                         white_rating, black_rating, result, num_plies,
                         event, variant, pdn)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rec["source"], rec["source_id"], rec["date"],
                        rec["white_name"], rec["black_name"],
                        rec["white_rating"], rec["black_rating"],
                        rec["result"], rec["num_plies"],
                        rec["event"], rec["variant"], rec["pdn"],
                    ),
                )
                if cur.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as exc:
                logger.warning("ingest_ndjson: insert error: %s", exc)
                errors += 1
        await db.commit()

    return {"inserted": inserted, "skipped": skipped, "errors": errors}


async def get_stats() -> dict[str, Any]:
    """Return aggregate stats for the expert_games corpus."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*), MIN(date), MAX(date) FROM expert_games"
        )
        row = await cur.fetchone()
        total = int(row[0]) if row else 0
        min_date = row[1] if row else None
        max_date = row[2] if row else None

        cur2 = await db.execute(
            "SELECT source, COUNT(*) FROM expert_games GROUP BY source"
        )
        by_source = {r[0]: int(r[1]) for r in await cur2.fetchall()}

    return {
        "total": total,
        "by_source": by_source,
        "min_date": min_date,
        "max_date": max_date,
    }
