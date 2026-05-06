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


def _load() -> dict:
    if os.path.isfile(_CACHE_PATH):
        try:
            with open(_CACHE_PATH) as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("opening_eval_cache load error: %s", exc)
    return {}


def lookup(fen: str) -> dict | None:
    """Return cached {score, bestMove} or None if not in cache."""
    return _load().get(fen)


def store(entries: list[dict]) -> int:
    """Persist a list of {fen, score, bestMove}. Returns number of new entries."""
    with _lock:
        cache = _load()
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
    return len(_load())
