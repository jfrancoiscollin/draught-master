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

from typing import Any

# Clear of manuel_debutant (2000+) and the strategy manuals (5000+), and
# clear of the burned 1-572 legacy range.
COMBINAISONS_ID_OFFSET = 7000

BOOK_ID = "manuel_dubois_combinaisons"


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
