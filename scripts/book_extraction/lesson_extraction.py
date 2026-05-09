"""
Lesson text extraction from PDF pages.

Lessons in Dubois books follow a consistent structure:
  - A chapter title page (e.g. "Chapitre 1 : les combinaisons en 2 temps")
  - Several pages of text (theory)
  - Then diagram pages (exercises) — we stop before those

The lesson_chapters list in the config maps chapter IDs to their start pages.
We extract text from each chapter's start page up to the next chapter's start page
(or the end of text, whichever comes first), then clean noise.
"""
from __future__ import annotations
import re
from typing import Dict, Any, List

from config import BookConfig, LessonChapter


def extract_all_lessons(
    pages: List[str],
    cfg: BookConfig,
) -> Dict[str, Dict[str, Any]]:
    """
    Extract lesson text for all chapters defined in cfg.lesson_chapters.

    Returns a dict keyed by str(chapter_id):
    {
        "title": "...",
        "text": "...",
        "category": "...",
        "diagrams": []   # reserved for future diagram references
    }
    """
    lessons: Dict[str, Dict[str, Any]] = {}
    chapters = sorted(cfg.lesson_chapters, key=lambda c: c.page)

    for i, ch in enumerate(chapters):
        # Find the ending page: next chapter's start page, or end of doc
        next_start = chapters[i + 1].page if i + 1 < len(chapters) else len(pages) + 1
        # Also stop at the first exercise page for this chapter
        ex_page = _find_exercise_page(cfg, ch.chapter_id)
        end_page = min(next_start, ex_page) if ex_page else next_start

        raw = _collect_text(pages, ch.page, end_page)
        text = _clean_lesson_text(raw, ch.title)

        lessons[str(ch.chapter_id)] = {
            'title': ch.title,
            'text': text,
            'category': ch.category,
            'diagrams': [],
        }

    return lessons


def _find_exercise_page(cfg: BookConfig, chapter_id: int) -> int:
    """Return the exercise start page for a given chapter, or 0 if none."""
    for block in cfg.exercise_chapters:
        if block.chapter_id == chapter_id:
            return block.ex_page
    return 0


def _collect_text(pages: List[str], start: int, end: int) -> str:
    """Concatenate pages[start-1 .. end-2] (1-based page numbers)."""
    parts = []
    for p in range(start, end):
        idx = p - 1
        if 0 <= idx < len(pages):
            parts.append(pages[idx])
    return '\n'.join(parts)


def _clean_lesson_text(raw: str, title: str) -> str:
    """
    Remove page numbers, headers, and artefacts from extracted lesson text.

    Heuristics:
    - Lines that are purely numeric (page numbers) are dropped.
    - Very short lines at the start/end of a page (headers/footers) are dropped.
    - Repeated chapter title at the start is dropped.
    """
    lines = raw.splitlines()
    cleaned: List[str] = []
    for line in lines:
        stripped = line.strip()
        # Drop pure page-number lines
        if re.match(r'^\d{1,3}$', stripped):
            continue
        # Drop empty repeated title at start
        if stripped.lower() == title.lower():
            continue
        cleaned.append(line)

    text = '\n'.join(cleaned)
    # Collapse runs of 3+ blank lines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
