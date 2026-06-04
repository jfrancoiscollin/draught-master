"""Goedemoed exercise books as chapter-structured *exercise* books.

Goedemoed's diagrams carry a study ``theme`` (Combinaisons, Calcul, …) instead
of prose. To render the two volumes like the Débutant book (a collapsible list
of chapters, each with starred exercises and a progress count), we expose each
theme as a "chapter":

  * :func:`theme_index` maps every (page, number) to ``(chapter_no, theme)`` so
    :mod:`strategy.build_goedemoed_exercises` can stamp ``Chapitre N`` into each
    exercise's description (the exercise list groups on that) and label it ``Dk``.
  * :func:`goedemoed_chapters` returns the per-chapter prose keyed by a
    book-specific id range (so it never collides with the Débutant / Dubois
    chapters on the shared ``/api/lessons/{chapter}`` endpoint) — a one-line
    intro plus a few illustrative diagrams, enough for the 📖 lesson button.

Chapter numbering follows the themes' first appearance in the book (same order
as the manual's table of contents).
"""
from __future__ import annotations

from typing import Any

# Disjoint lesson-id ranges (Débutant 1-16, sens-du-jeu 101-135, combinaisons
# 201-241). Goedemoed vol. 2 → 300+, vol. 3 → 400+. Mirrored in the frontend
# ExercisePanel.LESSON_ID_OFFSET.
CHAPTER_OFFSET: dict[str, int] = {"GOEDEMOED": 300, "GOEDEMOED3": 400}


def _themes(source: str) -> list[dict]:
    from .api import _theme_chapters  # noqa: PLC0415 — lazy, avoids import cost
    return _theme_chapters(source) or []


def theme_index(source: str) -> dict[tuple[int, int], tuple[int, str]]:
    """``(page, number) -> (chapter_no, theme)`` for every renderable diagram."""
    out: dict[tuple[int, int], tuple[int, str]] = {}
    for i, chapter in enumerate(_themes(source), start=1):
        for (page, number) in chapter["diagrams"]:
            out[(page, number)] = (i, chapter["theme"])
    return out


def goedemoed_chapters(source: str) -> dict[str, Any]:
    """Per-chapter prose keyed by ``str(CHAPTER_OFFSET[source] + n)``."""
    from .api import _fen_for  # noqa: PLC0415
    src = source.upper()
    off = CHAPTER_OFFSET.get(src)
    if off is None:
        return {}
    out: dict[str, Any] = {}
    for i, chapter in enumerate(_themes(src), start=1):
        diagrams = []
        for (page, number) in chapter["diagrams"][:6]:
            fen = _fen_for(src, page, number)
            if fen:
                diagrams.append({"fen": fen, "caption": f"p.{page} #{number}"})
        out[str(off + i)] = {
            "title": chapter["theme"],
            "text": (
                f"« {chapter['theme']} » — {len(chapter['diagrams'])} positions. "
                "Trouvez le meilleur coup dans chaque exercice."
            ),
            "category": "",
            "diagrams": diagrams,
        }
    return out
