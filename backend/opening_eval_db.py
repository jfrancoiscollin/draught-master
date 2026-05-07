"""JSON-file cache for pre-computed Scan position evaluations.

Positions are keyed by FEN string and store {score, bestMove, depth}.
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


def lookup(fen: str) -> dict | None:
    """Return cached {score, bestMove} or None if not in cache."""
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
            cache[fen] = {
                "score": e.get("score", 0),
                "bestMove": e.get("bestMove"),
            }
        os.makedirs(os.path.dirname(os.path.abspath(_CACHE_PATH)), exist_ok=True)
        with open(_CACHE_PATH, "w") as f:
            json.dump(cache, f, separators=(",", ":"))
        new_count = len(cache) - before
        logger.info("opening_eval_cache: +%d new entries (%d total)", new_count, len(cache))
        return new_count


def size() -> int:
    with _lock:
        return len(_get_cache())
