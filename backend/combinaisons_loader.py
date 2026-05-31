"""Loader for the Dubois "Apprendre les combinaisons" corpus.

These 408 exercises (combination depth 2 → 6, difficulty 1-5) were
extracted from the Dubois manual (see scripts/book_extraction/configs/
dubois_combinaisons.py) and live as ``INITIAL_EXERCISES`` in
``db/exercises_data.py``. They were historically seeded at DB ids 1-572,
then retired; that id range is deliberately avoided. We re-introduce them
at a fresh offset so they cannot collide with persisted progress rows
pointing at the old static books.

Convention: rows get sequential DB ids from ``COMBINAISONS_ID_OFFSET + 1``
in the deterministic order returned here (the source file order).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Clear of manuel_debutant (2000+) and the strategy manuals (5000+), and
# clear of the burned 1-572 legacy range.
COMBINAISONS_ID_OFFSET = 7000

BOOK_ID = "manuel_dubois_combinaisons"

# Chapter prose lives in lessons.json keyed 1..41, but the lesson-prose
# endpoint (/api/lessons/{chapter}) is shared with the Débutant chapters
# (1..16), so we expose the combinaisons chapters under a dedicated range to
# avoid that collision. Mirrors the "sens du jeu" convention (100+).
#   Débutant       1..16
#   sens du jeu    101..135
#   combinaisons   201..241   (this loader)
COMBINAISONS_CHAPTER_OFFSET = 200

_LESSONS_PATH = Path(__file__).resolve().parent / "lessons.json"


def combinaisons_chapters() -> dict[str, Any]:
    """The chapter prose (title / text / category / diagrams), keyed by id.

    Source ids 1..41 in ``lessons.json`` are re-keyed to
    ``COMBINAISONS_CHAPTER_OFFSET + n`` so they never collide with the
    Débutant chapters on the shared prose endpoint.
    """
    if not _LESSONS_PATH.is_file():
        return {}
    raw = json.loads(_LESSONS_PATH.read_text())
    return {
        str(COMBINAISONS_CHAPTER_OFFSET + int(ch)): lesson
        for ch, lesson in raw.items()
    }


def all_combinaisons_exercises() -> list[dict[str, Any]]:
    """Exercise rows ready for ``INSERT INTO exercises (...)``.

    Deterministic order (source file order) so id assignment is stable.
    """
    from db.exercises_data import INITIAL_EXERCISES

    return [
        {
            "name": ex["name"],
            "description": ex["description"],
            "initial_fen": ex["initial_fen"],
            "solution_moves": ex["solution_moves"],
            "difficulty": ex["difficulty"],
            "category": ex["category"],
            "hint": ex.get("hint"),
            "book_id": BOOK_ID,
        }
        for ex in INITIAL_EXERCISES
    ]
