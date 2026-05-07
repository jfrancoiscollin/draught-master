"""
SQLite-backed opening book for AI-Draught.

Improvements over the old JSON-file cache (opening_eval_db.py):
  - Horizontal-mirror canonicalization: stores the lexicographically smaller
    of (fen, mirror(fen)), halving storage and doubling lookup coverage.
  - Per-row writes via INSERT OR REPLACE — no full-file rewrites.
  - games_seen + depth columns enable cleanup queries.
  - WAL mode for concurrent reads without blocking writes.
  - cleanup() prunes rare / too-deep positions in one SQL pass.
  - migrate_from_json() for one-time import of the old cache.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_DB_PATH = os.environ.get(
    "OPENING_BOOK_DB",
    os.path.join(os.path.dirname(__file__), "opening_book.db"),
)
_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


# ─── Connection & schema ──────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(os.path.abspath(_DB_PATH)), exist_ok=True)
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _init_schema(_conn)
    return _conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS opening_book (
            fen        TEXT    PRIMARY KEY,
            score      INTEGER NOT NULL DEFAULT 0,
            best_move  TEXT,
            games_seen INTEGER NOT NULL DEFAULT 0,
            depth      INTEGER NOT NULL DEFAULT 99,
            updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS opening_continuations (
            fen   TEXT    NOT NULL,
            move  TEXT    NOT NULL,
            count INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (fen, move),
            FOREIGN KEY (fen) REFERENCES opening_book(fen) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_cont_fen ON opening_continuations(fen);
    """)
    conn.commit()


# ─── Mirror / canonicalization ────────────────────────────────────────────────

def mirror_sq(sq: int) -> int:
    """Horizontal mirror of dark square 1-50 (flip position within each rank of 5)."""
    r = (sq - 1) // 5
    p = (sq - 1) % 5
    return r * 5 + (4 - p) + 1


def _mirror_section(section: str) -> str:
    """Mirror one FEN section like 'WK3,5,12' preserving king/man ordering."""
    color = section[0]
    kings: list[int] = []
    men: list[int] = []
    for token in section[1:].split(','):
        token = token.strip()
        if not token:
            continue
        if token.startswith('K'):
            kings.append(mirror_sq(int(token[1:])))
        else:
            men.append(mirror_sq(int(token)))
    kings.sort()
    men.sort()
    pieces = ['K' + str(sq) for sq in kings] + [str(sq) for sq in men]
    return color + (','.join(pieces) if pieces else '')


def mirror_fen(fen: str) -> str:
    parts = fen.split(':')
    return ':'.join([parts[0]] + [_mirror_section(s) for s in parts[1:]])


def mirror_move(pdn: str) -> str:
    """Mirror a PDN move string like '32-28' or '23x14x5'."""
    if not pdn:
        return pdn
    clean = pdn.lstrip('K')
    sep = 'x' if 'x' in clean else '-'
    return sep.join(str(mirror_sq(int(p))) for p in clean.split(sep) if p)


def canonical(fen: str) -> tuple[str, bool]:
    """Return (canonical_fen, was_mirrored). Picks the lexicographically smaller FEN."""
    m = mirror_fen(fen)
    if m < fen:
        return m, True
    return fen, False


# ─── Public API ───────────────────────────────────────────────────────────────

def lookup(fen: str) -> Optional[dict]:
    """Return {score, bestMove, cont?} or None if not in book."""
    canon, was_mirrored = canonical(fen)
    with _lock:
        conn = _get_conn()
        row = conn.execute(
            "SELECT score, best_move FROM opening_book WHERE fen = ?", (canon,)
        ).fetchone()
        if row is None:
            return None
        cont_rows = conn.execute(
            "SELECT move, count FROM opening_continuations WHERE fen = ?", (canon,)
        ).fetchall()

    best = row["best_move"]
    if was_mirrored and best:
        best = mirror_move(best)

    result: dict = {"score": row["score"], "bestMove": best}
    if cont_rows:
        cont = {r["move"]: r["count"] for r in cont_rows}
        if was_mirrored:
            cont = {mirror_move(m): c for m, c in cont.items()}
        result["cont"] = cont
    return result


def store(entries: list[dict], depth: int = 99) -> int:
    """Persist evaluated positions. depth per entry overrides the parameter.
    Returns number of newly inserted rows."""
    if not entries:
        return 0
    with _lock:
        conn = _get_conn()
        new_count = 0
        for e in entries:
            fen = e.get("fen")
            if not fen:
                continue
            canon, was_mirrored = canonical(fen)
            best = e.get("bestMove")
            if was_mirrored and best:
                best = mirror_move(best)
            score = int(e.get("score", 0))
            entry_depth = int(e.get("depth", depth))

            existing = conn.execute(
                "SELECT depth FROM opening_book WHERE fen = ?", (canon,)
            ).fetchone()
            if existing is None:
                new_count += 1
                conn.execute(
                    """INSERT INTO opening_book(fen, score, best_move, games_seen, depth)
                       VALUES (?, ?, ?, 0, ?)""",
                    (canon, score, best, entry_depth),
                )
            else:
                conn.execute(
                    """UPDATE opening_book
                       SET score=?, best_move=?, depth=MIN(depth,?), updated_at=datetime('now')
                       WHERE fen=?""",
                    (score, best, entry_depth, canon),
                )
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM opening_book").fetchone()[0]
        logger.info("opening_book.store: +%d new (%d total)", new_count, total)
        return new_count


def store_continuations(
    cont_map: dict[str, dict[str, int]],
    fen_depths: Optional[dict[str, int]] = None,
) -> None:
    """Merge continuation frequency data. Creates skeleton book entries as needed.

    fen_depths: optional {fen: depth} to record at which half-move each position
                was first reached.
    """
    if not cont_map:
        return
    with _lock:
        conn = _get_conn()
        for fen, moves in cont_map.items():
            canon, was_mirrored = canonical(fen)
            game_count = sum(moves.values())
            depth = int(fen_depths.get(fen, 99)) if fen_depths else 99
            conn.execute(
                """INSERT INTO opening_book(fen, score, best_move, games_seen, depth)
                   VALUES (?, 0, NULL, ?, ?)
                   ON CONFLICT(fen) DO UPDATE SET
                     games_seen = games_seen + excluded.games_seen,
                     depth      = MIN(depth, excluded.depth)""",
                (canon, game_count, depth),
            )
            for move, cnt in moves.items():
                m = mirror_move(move) if was_mirrored else move
                conn.execute(
                    """INSERT INTO opening_continuations(fen, move, count) VALUES (?,?,?)
                       ON CONFLICT(fen, move) DO UPDATE SET count = count + excluded.count""",
                    (canon, m, cnt),
                )
        conn.commit()
    logger.info("store_continuations: merged %d positions", len(cont_map))


def size() -> int:
    with _lock:
        return _get_conn().execute("SELECT COUNT(*) FROM opening_book").fetchone()[0]


def cleanup(
    min_games: int = 3,
    max_depth: int = 40,
    min_cont_pct: float = 0.03,
    min_cont_count: int = 2,
) -> dict:
    """Remove low-quality entries and orphan continuations. Returns stats."""
    with _lock:
        conn = _get_conn()
        before = conn.execute("SELECT COUNT(*) FROM opening_book").fetchone()[0]

        # 1. Prune rare continuation moves (absolute count OR relative frequency)
        conn.execute(
            """DELETE FROM opening_continuations
               WHERE count < ?
                  OR (
                      SELECT CAST(opening_continuations.count AS REAL)
                             / NULLIF(b.games_seen, 0)
                      FROM opening_book b
                      WHERE b.fen = opening_continuations.fen
                  ) < ?""",
            (min_cont_count, min_cont_pct),
        )

        # 2. Prune positions that are too rare or belong to the middle-game
        conn.execute(
            "DELETE FROM opening_book WHERE games_seen < ? OR depth > ?",
            (min_games, max_depth),
        )

        conn.commit()
        after = conn.execute("SELECT COUNT(*) FROM opening_book").fetchone()[0]
        cont_left = conn.execute("SELECT COUNT(*) FROM opening_continuations").fetchone()[0]
        removed = before - after
        logger.info("cleanup: %d → %d positions (-%d), %d continuations remain",
                    before, after, removed, cont_left)
        return {
            "before": before,
            "after": after,
            "removed": removed,
            "continuations_remaining": cont_left,
        }


def stats() -> dict:
    """Return summary statistics about the book."""
    with _lock:
        conn = _get_conn()
        positions = conn.execute("SELECT COUNT(*) FROM opening_book").fetchone()[0]
        with_eval = conn.execute(
            "SELECT COUNT(*) FROM opening_book WHERE best_move IS NOT NULL"
        ).fetchone()[0]
        continuations = conn.execute("SELECT COUNT(*) FROM opening_continuations").fetchone()[0]
        depth_dist = conn.execute(
            "SELECT depth, COUNT(*) as n FROM opening_book GROUP BY depth ORDER BY depth"
        ).fetchall()
    return {
        "positions": positions,
        "evaluated": with_eval,
        "continuations": continuations,
        "depth_distribution": {str(r["depth"]): r["n"] for r in depth_dist},
    }


def migrate_from_json(json_path: str) -> dict:
    """One-time migration from the old opening_eval_cache.json file."""
    import json as _json
    try:
        with open(json_path) as f:
            data = _json.load(f)
    except FileNotFoundError:
        return {"migrated": 0, "skipped": "file not found"}

    entries = [
        {"fen": fen, "score": v.get("score", 0), "bestMove": v.get("bestMove")}
        for fen, v in data.items()
    ]
    cont_map = {fen: v["cont"] for fen, v in data.items() if v.get("cont")}
    added = store(entries)
    if cont_map:
        store_continuations(cont_map)
    logger.info("migrate_from_json: %d entries from %s (%d new)", len(entries), json_path, added)
    return {"source": json_path, "total_entries": len(entries), "new_positions": added}
