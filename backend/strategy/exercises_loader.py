"""Expose the mined manual combinations as seedable exercise rows.

Reads ``strategy_exercises.json`` (produced by ``generate_exercises.py``)
and yields rows in the exact shape ``db/schema.py`` upserts, mirroring
``manuels.loader``. IDs live in their own range so they never collide
with the manuel_debutant rows (2001+).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_PATH = Path(__file__).resolve().parent / "strategy_exercises.json"

# IDs 5001+ — clear of manuel_debutant (2001+) and the legacy Dubois
# range (1..572) dropped at init.
STRATEGY_ID_OFFSET = 5000


@lru_cache(maxsize=1)
def _raw() -> list[dict[str, Any]]:
    if not _PATH.is_file():
        return []
    return json.loads(_PATH.read_text()).get("exercises", [])


# Sources seeded before GOEDEMOED was added. Their IDs are assigned by the
# enumerate order in db/schema.py and are referenced by curriculum_resolved.json
# and by users' saved progress, so their relative order must never change.
# New sources are appended *after* these to keep existing IDs stable.
_LEGACY_SOURCES = ("KELLER", "SIJBRANDS", "SPRINGER")


def _sort_key(ex: dict[str, Any]) -> tuple:
    # Legacy sources keep their original (diagram_id-sorted) positions; any new
    # source sorts strictly after them, so it only ever occupies fresh IDs.
    is_new = ex["source"].upper() not in _LEGACY_SOURCES
    return (is_new, ex["diagram_id"])


def all_strategy_exercises() -> list[dict[str, Any]]:
    """Exercise rows ready for ``INSERT INTO exercises (...)``.

    Legacy sources are emitted first in their original diagram-id order so their
    seeded IDs stay fixed; newer sources are appended afterwards.
    """
    rows: list[dict[str, Any]] = []
    for ex in sorted(_raw(), key=_sort_key):
        rows.append(
            {
                "name": ex["name"],
                "description": ex["description"],
                "initial_fen": ex["initial_fen"],
                "solution_moves": ex["solution_moves"],
                "difficulty": ex["difficulty"],
                "category": ex["category"],
                "hint": ex["hint"],
                "book_id": f"manuel_{ex['source'].lower()}",
            }
        )
    return rows
