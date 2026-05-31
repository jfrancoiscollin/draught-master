"""Loader for the Dubois "Apprendre le sens du jeu" corpus.

72 positional exercises across 14 chapters (notion d'avantage, liberté de
mouvement, le pion d'angle 46, les pions de base, formations…), extracted
from the Dubois manual (see scripts/book_extraction/configs/
dubois_sens_du_jeu.py) and stored as ``SENS_DU_JEU_EXERCISES`` in
``db/sens_du_jeu_exercises.py``. The matching chapter prose (with
illustrative diagrams) lives in ``sens_du_jeu_lessons.json``.

Historically seeded at ids 501-572 then retired; that range is avoided.
We re-introduce the exercises at a fresh offset so they cannot collide
with persisted progress rows.

Convention: rows get sequential DB ids from ``SENS_DU_JEU_ID_OFFSET + 1``
in the deterministic order returned here (the source file order).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Clear of debutant (2000+), strategy (5000+), Dubois combinations (7000+)
# and the burned 1-572 legacy range.
SENS_DU_JEU_ID_OFFSET = 8000

BOOK_ID = "manuel_dubois_sens_du_jeu"

_LESSONS_PATH = Path(__file__).resolve().parent / "sens_du_jeu_lessons.json"


def all_sens_du_jeu_exercises() -> list[dict[str, Any]]:
    """Exercise rows ready for ``INSERT INTO exercises (...)``.

    Deterministic order (source file order) so id assignment is stable.
    """
    from db.sens_du_jeu_exercises import SENS_DU_JEU_EXERCISES

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
        for ex in SENS_DU_JEU_EXERCISES
    ]


def sens_du_jeu_chapters() -> dict[str, Any]:
    """The chapter prose (title / text / category / diagrams), keyed by id."""
    if not _LESSONS_PATH.is_file():
        return {}
    return json.loads(_LESSONS_PATH.read_text())
