"""JSON-file cache for pre-computed Scan position evaluations.

Positions are keyed by FEN string and store {score, bestMove, cont}.
The file path can be overridden with the OPENING_EVAL_CACHE env var so that
a Railway volume mount makes the cache persistent across redeploys.
"""
from __future__ import annotations

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

_CACHE_PATH = os.environ.get(
    "OPENING_EVAL_CACHE",
    os.path.join(os.path.dirname(__file__), "opening_eval_cache.json"),
)
_lock = threading.Lock()

# In-memory cache — loaded once at first access, updated on every store()
_mem_cache: dict | None = None


def _get_cache() -> dict:
    """Return the in-memory cache, loading from disk if not yet loaded."""
    global _mem_cache
    if _mem_cache is None:
        _mem_cache = _load_from_disk()
    return _mem_cache


def _load_from_disk() -> dict:
    if os.path.isfile(_CACHE_PATH):
        try:
            with open(_CACHE_PATH) as f:
                data = json.load(f)
                logger.info("opening_eval_cache: loaded %d entries from disk", len(data))
                return data
        except Exception as exc:
            logger.warning("opening_eval_cache load error: %s", exc)
    return {}


def _flush() -> None:
    """Write in-memory cache to disk (must be called under _lock)."""
    os.makedirs(os.path.dirname(os.path.abspath(_CACHE_PATH)), exist_ok=True)
    with open(_CACHE_PATH, "w") as f:
        json.dump(_mem_cache, f, separators=(",", ":"))


def lookup(fen: str) -> dict | None:
    """Return cached entry {score, bestMove, cont?} or None if not in cache."""
    with _lock:
        return _get_cache().get(fen)


def store(entries: list[dict]) -> int:
    """Persist a list of {fen, score, bestMove}. Returns number of new entries."""
    global _mem_cache
    with _lock:
        cache = _get_cache()
        before = len(cache)
        for e in entries:
            fen = e.get("fen")
            if not fen:
                continue
            existing = cache.get(fen, {})
            existing["score"] = e.get("score", 0)
            existing["bestMove"] = e.get("bestMove")
            cache[fen] = existing
        _flush()
        new_count = len(cache) - before
        logger.info("opening_eval_cache: +%d new entries (%d total)", new_count, len(cache))
        return new_count


def store_continuations(cont_map: dict[str, dict[str, int]]) -> None:
    """Merge continuation frequency data into the cache.

    cont_map: {fen: {move_pdn: count}}
    Creates skeleton entries for FENs not yet evaluated (score=0, bestMove=None).
    """
    global _mem_cache
    if not cont_map:
        return
    with _lock:
        cache = _get_cache()
        for fen, moves in cont_map.items():
            entry = cache.setdefault(fen, {"score": 0, "bestMove": None})
            existing: dict[str, int] = entry.get("cont", {})
            for move, cnt in moves.items():
                existing[move] = existing.get(move, 0) + cnt
            entry["cont"] = existing
        _flush()
    logger.info("store_continuations: updated %d positions", len(cont_map))


def size() -> int:
    with _lock:
        return len(_get_cache())
