"""Backfill exercise_tags from dilf's deterministic motif detectors.

Idempotent one-shot. Run once after the exercise_tags table is created,
and again if new detectors land. The script writes the **detected
motif set** for each exercise to exercise_tags, replacing any prior
tag set for that exercise.

Usage:
    python -m backend.pedagogy.scripts.tag_existing_exercises
    python -m backend.pedagogy.scripts.tag_existing_exercises --dry-run
    python -m backend.pedagogy.scripts.tag_existing_exercises --only 42 43 44

Column name adaptations vs. spec:
  - exercises.initial_fen (not fen_start)
  - exercises.solution_moves (not solution_moves_json), already a JSON string
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Iterable, Optional

import aiosqlite

from pedagogy.game import parse_fen
from pedagogy.motifs import ALL_DETECTORS

from .. import storage

logger = logging.getLogger("pedagogy.tag_existing_exercises")


def _db_path() -> str:
    import os
    from pathlib import Path
    db_dir = os.getenv("DB_DIR", str(Path(__file__).parent.parent.parent))
    return str(Path(db_dir) / "draught_master.db")


# ---------------------------------------------------------------------------
# Per-exercise tagging
# ---------------------------------------------------------------------------


def _detect_tags(fen_start: str, solution_moves: list[str]) -> set[str]:
    """Run every detector on (state_before, first_move, state_after).

    Returns the motif names that fired. We don't store severity or role —
    exercise_tags is just a coarse index for recommendations.
    """
    state_before = parse_fen(fen_start)
    if not solution_moves:
        return set()

    # Parse first move notation (e.g. "32-28" or "40x29x18") into a dilf Move.
    # Try dilf's own parse_move; fall back to building Move manually.
    first_move_notation = solution_moves[0]
    try:
        from pedagogy.game import parse_move_notation  # dilf utility
        first_move = parse_move_notation(first_move_notation, state_before)
    except (ImportError, AttributeError):
        first_move = _parse_move_fallback(first_move_notation)

    if first_move is None:
        return set()

    try:
        from pedagogy.game import apply_move as dilf_apply_move
        state_after = dilf_apply_move(state_before, first_move)
    except Exception:
        return set()

    tags: set[str] = set()
    for detector_cls in ALL_DETECTORS:
        try:
            detector = detector_cls()
            match = detector.detect(
                state_before=state_before,
                state_after=state_after,
                move=first_move,
                best_move=None,
                pv=[],
                score_before=0.0,
                score_after=0.0,
                engine=None,
            )
            if match is not None:
                tags.add(match.motif)
        except Exception as exc:
            logger.debug("detector %s skipped: %s", detector_cls.__name__, exc)
    return tags


def _parse_move_fallback(notation: str):
    """Parse a move notation string into a dilf Move when the library
    function is unavailable. Handles quiet (32-28) and capture (40x29x18)."""
    try:
        from pedagogy.game import Move
        if "x" in notation:
            squares = tuple(int(s) for s in notation.split("x"))
        else:
            squares = tuple(int(s) for s in notation.split("-"))
        captures: tuple[int, ...] = ()
        return Move(path=squares, captures=captures, promotion=False)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# DB iteration
# ---------------------------------------------------------------------------


async def _iter_exercises(
    conn: aiosqlite.Connection,
    only_ids: Optional[list[int]] = None,
) -> list[tuple[int, str, list[str]]]:
    if only_ids:
        placeholders = ",".join("?" * len(only_ids))
        cur = await conn.execute(
            f"SELECT id, initial_fen, solution_moves FROM exercises "
            f"WHERE id IN ({placeholders})",
            tuple(only_ids),
        )
    else:
        cur = await conn.execute(
            "SELECT id, initial_fen, solution_moves FROM exercises"
        )
    rows = await cur.fetchall()
    out: list[tuple[int, str, list[str]]] = []
    for row in rows:
        try:
            moves = json.loads(row[2])
        except (json.JSONDecodeError, TypeError):
            logger.warning("exercise %s has invalid solution_moves; skipping", row[0])
            continue
        out.append((int(row[0]), str(row[1]), list(moves)))
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def _run(only_ids: Optional[list[int]], dry_run: bool) -> int:
    tagged = 0
    unchanged = 0
    skipped = 0

    from db.config import DB_PATH  # draught-master DB path

    async with aiosqlite.connect(DB_PATH) as conn:
        exercises = await _iter_exercises(conn, only_ids)
        for ex_id, fen, moves in exercises:
            try:
                new_tags = _detect_tags(fen, moves)
            except Exception as exc:  # noqa: BLE001
                logger.warning("exercise %s: detector error: %s", ex_id, exc)
                skipped += 1
                continue

            current = set(await storage.get_exercise_tags(conn, ex_id))
            if new_tags == current:
                unchanged += 1
                continue

            if dry_run:
                logger.info(
                    "[dry-run] exercise %s: %s -> %s",
                    ex_id, sorted(current), sorted(new_tags),
                )
                tagged += 1
                continue

            await storage.set_exercise_tags(conn, ex_id, sorted(new_tags))
            logger.info(
                "exercise %s tagged with %s",
                ex_id, sorted(new_tags) or "(none — cleared)",
            )
            tagged += 1

    logger.info(
        "done: %d tagged, %d unchanged, %d skipped",
        tagged, unchanged, skipped,
    )
    return 0 if skipped == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute the diff but don't write.")
    parser.add_argument("--only", type=int, nargs="*", default=None,
                        help="Only re-tag this/these exercise id(s).")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return asyncio.run(_run(args.only, args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
