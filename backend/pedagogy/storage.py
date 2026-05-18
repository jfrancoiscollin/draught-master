"""Persistence helpers for the pedagogy layer.

Round-trips `MoveVerdict` / `GameAnalysis` / explanation rows between
the in-memory dataclasses (provided by the `dilf` package) and the
three SQLite tables added in db/schema.py.

All functions are async (aiosqlite). No FastAPI imports here — this
module is callable from a script (PR 13) as well as from the API
router (PR 8).

Column name adaptations vs. spec:
  - games.id is TEXT (UUID), not INTEGER → game_id is TEXT here
  - exercises.initial_fen (not fen_start), exercises.name (not title),
    exercises.solution_moves (not solution_moves_json)
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Optional

import aiosqlite

from pedagogy.types import (
    Features,
    GameAnalysis,
    MotifMatch,
    MoveVerdict,
    Phase,
    Verdict,
)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _motifs_to_json(motifs: list[MotifMatch]) -> str:
    return json.dumps([asdict(m) for m in motifs], ensure_ascii=False)


def _motifs_from_json(blob: str) -> list[MotifMatch]:
    raw = json.loads(blob)
    return [MotifMatch(**m) for m in raw]


def _features_to_json(features: Optional[Features]) -> Optional[str]:
    if features is None:
        return None
    return json.dumps(asdict(features), ensure_ascii=False, default=str)


def _features_from_json(blob: Optional[str]) -> Optional[Features]:
    if blob is None:
        return None
    raw = json.loads(blob)
    raw["phase"] = Phase(raw["phase"])
    # Backfill fields added to Features over time so blobs persisted by
    # older deploys still rehydrate cleanly. hanging_pieces_{w,b} +
    # threatened_captures_{w,b} are always [] in legacy blobs — they
    # weren't computed back then. ThreatenedCapture entries persisted as
    # plain dicts via asdict need rebuilding into instances so the
    # downstream contract (dataclass attribute access) still works.
    from pedagogy.types import ThreatenedCapture
    raw.setdefault("hanging_pieces_white", [])
    raw.setdefault("hanging_pieces_black", [])
    for key in ("threatened_captures_white", "threatened_captures_black"):
        items = raw.get(key) or []
        raw[key] = [
            ThreatenedCapture(
                path=tuple(it.get("path", ())),
                captures=tuple(it.get("captures", ())),
            )
            for it in items
        ]
    return Features(**raw)


# ---------------------------------------------------------------------------
# move_verdicts CRUD
# ---------------------------------------------------------------------------


async def upsert_move_verdict(
    conn: aiosqlite.Connection,
    game_id: str,
    verdict: MoveVerdict,
) -> int:
    """Insert or replace a verdict, return its row id."""
    await conn.execute(
        """
        INSERT OR REPLACE INTO move_verdicts
            (game_id, move_number, side, fen_before, fen_after, move_notation,
             score_before, score_after, delta_winchance, verdict, is_forced,
             phase, motifs_json, features_json, features_after_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            game_id,
            verdict.move_number,
            verdict.side,
            verdict.fen_before,
            verdict.fen_after,
            verdict.move_notation,
            verdict.score_before,
            verdict.score_after,
            verdict.delta_winchance,
            verdict.verdict.value,
            1 if verdict.is_forced else 0,
            verdict.phase.value,
            _motifs_to_json(verdict.motifs),
            _features_to_json(verdict.features_before),
            _features_to_json(verdict.features_after),
        ),
    )
    await conn.commit()
    cur = await conn.execute(
        "SELECT id FROM move_verdicts WHERE game_id = ? AND move_number = ?",
        (game_id, verdict.move_number),
    )
    row = await cur.fetchone()
    assert row is not None
    return int(row[0])


async def upsert_game_analysis(
    conn: aiosqlite.Connection,
    analysis: GameAnalysis,
) -> list[int]:
    """Upsert every MoveVerdict of a GameAnalysis. Returns the row ids."""
    ids: list[int] = []
    for v in analysis.verdicts:
        ids.append(await upsert_move_verdict(conn, str(analysis.game_id), v))
    return ids


async def get_move_verdict(
    conn: aiosqlite.Connection,
    game_id: str,
    move_number: int,
) -> Optional[MoveVerdict]:
    cur = await conn.execute(
        """
        SELECT move_number, side, fen_before, fen_after, move_notation,
               score_before, score_after, delta_winchance, verdict,
               is_forced, phase, motifs_json, features_json, features_after_json
          FROM move_verdicts
         WHERE game_id = ? AND move_number = ?
        """,
        (game_id, move_number),
    )
    row = await cur.fetchone()
    if row is None:
        return None
    return MoveVerdict(
        move_number=row[0],
        side=row[1],
        fen_before=row[2],
        fen_after=row[3],
        move_notation=row[4],
        score_before=row[5],
        score_after=row[6],
        delta_winchance=row[7],
        verdict=Verdict(row[8]),
        is_forced=bool(row[9]),
        phase=Phase(row[10]),
        motifs=_motifs_from_json(row[11]),
        features_before=_features_from_json(row[12]),
        features_after=_features_from_json(row[13]),
    )


async def fetch_user_games_with_verdicts(
    conn: aiosqlite.Connection,
    user_id: int,
    lookback: int = 30,
) -> list[GameAnalysis]:
    """Fetch the last `lookback` finished games of `user_id` and
    materialise their verdicts. Used by aggregate_user_profile().

    Ordering: ``ORDER BY date DESC`` so the lookback window matches what
    the user sees in ``/api/history`` (the panel UI). Using ``rowid``
    instead would silently diverge whenever the lidraughts API returns
    games in non-chronological INSERT order — the 30 lookback games
    would then be a different subset than the 30 the user analyses,
    leaving the Points faibles panel empty even with many analyses
    completed.
    """
    cur = await conn.execute(
        """
        SELECT id, user_side, opening_name
          FROM games
         WHERE user_id = ?
           AND (status = 'finished' OR status IS NULL)
         ORDER BY date DESC
         LIMIT ?
        """,
        (user_id, lookback),
    )
    games = await cur.fetchall()
    out: list[GameAnalysis] = []
    for row in games:
        game_id = str(row[0])
        verdicts = await _fetch_verdicts_for_game(conn, game_id)
        out.append(
            GameAnalysis(
                game_id=game_id,
                user_id=user_id,
                user_side=row[1] or "white",
                opening_name=row[2] or "",
                verdicts=verdicts,
                summary={},
            )
        )
    return out


async def _fetch_verdicts_for_game(
    conn: aiosqlite.Connection, game_id: str
) -> list[MoveVerdict]:
    cur = await conn.execute(
        """
        SELECT move_number FROM move_verdicts
         WHERE game_id = ? ORDER BY move_number
        """,
        (game_id,),
    )
    move_numbers = [int(r[0]) for r in await cur.fetchall()]
    out: list[MoveVerdict] = []
    for mn in move_numbers:
        v = await get_move_verdict(conn, game_id, mn)
        if v is not None:
            out.append(v)
    return out


# ---------------------------------------------------------------------------
# pedagogy_explanations
# ---------------------------------------------------------------------------


async def upsert_explanation(
    conn: aiosqlite.Connection,
    move_verdict_id: int,
    mode: str,
    lang: str,
    text: str,
) -> None:
    await conn.execute(
        """
        INSERT OR REPLACE INTO pedagogy_explanations
            (move_verdict_id, mode, lang, text)
        VALUES (?, ?, ?, ?)
        """,
        (move_verdict_id, mode, lang, text),
    )
    await conn.commit()


async def get_explanation(
    conn: aiosqlite.Connection,
    move_verdict_id: int,
    mode: str,
    lang: str,
) -> Optional[str]:
    cur = await conn.execute(
        """
        SELECT text FROM pedagogy_explanations
         WHERE move_verdict_id = ? AND mode = ? AND lang = ?
        """,
        (move_verdict_id, mode, lang),
    )
    row = await cur.fetchone()
    return str(row[0]) if row is not None else None


# ---------------------------------------------------------------------------
# exercise_tags
# ---------------------------------------------------------------------------


async def set_exercise_tags(
    conn: aiosqlite.Connection,
    exercise_id: int,
    tags: list[str],
) -> None:
    """Replace the tag set for one exercise atomically."""
    await conn.execute("DELETE FROM exercise_tags WHERE exercise_id = ?", (exercise_id,))
    for tag in tags:
        await conn.execute(
            "INSERT OR IGNORE INTO exercise_tags (exercise_id, tag) VALUES (?, ?)",
            (exercise_id, tag),
        )
    await conn.commit()


async def get_exercise_tags(
    conn: aiosqlite.Connection, exercise_id: int
) -> list[str]:
    cur = await conn.execute(
        "SELECT tag FROM exercise_tags WHERE exercise_id = ? ORDER BY tag",
        (exercise_id,),
    )
    return [str(r[0]) for r in await cur.fetchall()]


async def fetch_exercises_by_tags(
    conn: aiosqlite.Connection,
    tags: list[str],
    exclude_ids: list[int] | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return exercises matching ANY of `tags`, including their full tag set.

    The ``tags`` field is required by dilf's ``recommend_exercises()`` to
    rank exercises by how many of their tags match the user's weaknesses.
    """
    if not tags:
        return []
    placeholders = ",".join("?" * len(tags))
    excl_clause = ""
    params: list[Any] = list(tags)
    if exclude_ids:
        excl_clause = (
            f" AND e.id NOT IN ({','.join('?' * len(exclude_ids))})"
        )
        params.extend(exclude_ids)
    params.append(limit)
    cur = await conn.execute(
        f"""
        SELECT DISTINCT e.id, e.name, e.initial_fen
          FROM exercises e
          JOIN exercise_tags et ON et.exercise_id = e.id
         WHERE et.tag IN ({placeholders}){excl_clause}
         LIMIT ?
        """,
        params,
    )
    rows = await cur.fetchall()
    result: list[dict[str, Any]] = []
    for r in rows:
        ex_id = int(r[0])
        full_tags = await get_exercise_tags(conn, ex_id)
        result.append({"id": ex_id, "title": r[1], "fen_start": r[2], "tags": full_tags})
    return result


async def fetch_exercises_for_motif(
    conn: aiosqlite.Connection,
    motif_slug: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return full exercise data for exercises tagged with ``motif_slug``.

    Results are ordered by difficulty ascending so the drill starts easy.
    """
    import json as _json  # noqa: PLC0415

    cur = await conn.execute(
        """
        SELECT e.id, e.name, e.description, e.initial_fen, e.solution_moves,
               e.difficulty, e.category, e.hint
          FROM exercises e
          JOIN exercise_tags et ON et.exercise_id = e.id
         WHERE et.tag = ?
         ORDER BY e.difficulty ASC, e.id ASC
         LIMIT ?
        """,
        (motif_slug, limit),
    )
    rows = await cur.fetchall()
    result: list[dict[str, Any]] = []
    for r in rows:
        try:
            solution_moves = _json.loads(r[4])
        except Exception:  # noqa: BLE001
            solution_moves = []
        result.append({
            "id": int(r[0]),
            "name": r[1],
            "description": r[2],
            "initial_fen": r[3],
            "solution_moves": solution_moves,
            "difficulty": int(r[5]),
            "category": r[6],
            "hint": r[7],
        })
    return result


async def fetch_already_solved_exercise_ids(
    conn: aiosqlite.Connection, user_id: int
) -> list[int]:
    cur = await conn.execute(
        "SELECT exercise_id FROM user_exercise_solved WHERE user_id = ?",
        (user_id,),
    )
    return [int(r[0]) for r in await cur.fetchall()]
