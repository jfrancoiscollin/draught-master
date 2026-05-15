"""Purge corrupted Lidraughts import rows left by the pre-#20 split_pdn_games bug.

Before PR #20, `split_pdn_games` split on every `[Tag "..."]` instead
of on game boundaries. A real PDN with N games and ~8 tags each was
exploded into ~8N fragments, each one inserted as its own row in the
`games` table — most of them with `white_player='?'`, `black_player='?'`,
`move_count=0` (because the fragment held a single tag, no moves).

This script finds those rows and reports / removes them. Designed to
run **once** in production after #20 ships.

Detection heuristic (all conditions on the same row) :
  - source = 'lidraughts'
  - white_player = '?' OR black_player = '?'

Real Lidraughts games always have both player usernames filled in, so
'?' is a reliable signal of fragment corruption.

Usage (in the production container, from backend/) :

    # Dry-run (default) — list what would be deleted, change nothing.
    python -m scripts.clean_corrupted_lidraughts_imports

    # Apply.
    python -m scripts.clean_corrupted_lidraughts_imports --apply

Exit codes :
  0 — success (rows listed in dry-run, or rows removed in --apply mode)
  1 — DB error
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import aiosqlite  # noqa: E402
from db.config import DB_PATH  # noqa: E402


DETECT_WHERE = (
    "source = 'lidraughts' "
    "AND (white_player = '?' OR black_player = '?')"
)


async def main(apply: bool) -> int:
    if not Path(DB_PATH).exists():
        print(f"DB not found at {DB_PATH}")
        return 1

    async with aiosqlite.connect(str(DB_PATH)) as db:
        cur = await db.execute(
            f"SELECT COUNT(*) FROM games WHERE source = 'lidraughts'"
        )
        total_lid = (await cur.fetchone())[0]

        cur = await db.execute(
            f"SELECT COUNT(*) FROM games WHERE {DETECT_WHERE}"
        )
        corrupted = (await cur.fetchone())[0]
        print(f"Lidraughts rows total      : {total_lid}")
        print(f"  └ corrupted (?, move=0)  : {corrupted}")
        print(f"  └ healthy                : {total_lid - corrupted}")

        if corrupted == 0:
            print("\nNothing to clean.")
            return 0

        # Per-user breakdown
        cur = await db.execute(
            f"SELECT user_id, COUNT(*) FROM games "
            f"WHERE {DETECT_WHERE} GROUP BY user_id ORDER BY 2 DESC"
        )
        rows = await cur.fetchall()
        print("\nCorrupted by user_id:")
        for user_id, n in rows:
            print(f"  user_id={user_id}: {n} corrupted rows")

        # Sample first 5 corrupted rows
        cur = await db.execute(
            f"SELECT id, user_id, date, white_player, black_player, "
            f"move_count, source_id, length(pdn) "
            f"FROM games WHERE {DETECT_WHERE} LIMIT 5"
        )
        sample = await cur.fetchall()
        print("\nSample (first 5):")
        for r in sample:
            print(
                f"  id={r[0][:12]}…, user={r[1]}, date={r[2]}, "
                f"W={r[3]!r}, B={r[4]!r}, moves={r[5]}, "
                f"src_id={r[6]!r}, pdn_len={r[7]}"
            )

        if not apply:
            print(f"\n[dry-run] would DELETE {corrupted} rows. "
                  "Re-run with --apply to commit.")
            return 0

        print(f"\nDeleting {corrupted} rows…")
        # Also delete annotations rows tied to those games if any
        await db.execute(
            f"DELETE FROM games WHERE {DETECT_WHERE}"
        )
        await db.commit()
        print(f"Deleted {corrupted} rows. New total Lidraughts rows: "
              f"{total_lid - corrupted}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="actually delete")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(apply=args.apply)))
