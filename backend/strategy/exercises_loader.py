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


def all_strategy_exercises() -> list[dict[str, Any]]:
    """Exercise rows ready for ``INSERT INTO exercises (...)``.

    Sorted by diagram id for stable, deterministic ID assignment.
    """
    rows: list[dict[str, Any]] = []
    for ex in sorted(_raw(), key=lambda e: e["diagram_id"]):
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
