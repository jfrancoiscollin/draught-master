"""
Lesson text extraction from PDF pages.

Lessons in Dubois books follow a consistent structure:
  - A chapter title page (e.g. "Chapitre 1 : les combinaisons en 2 temps")
  - Several pages of text (theory, often with illustrative board diagrams)
  - Then diagram pages (exercises) — we stop before those

When pdf_path is provided, extract_all_lessons() also detects board diagrams on
lesson pages and stores them as [{fen, label}] in the "diagrams" field.  Labels
are inferred from the layout-preserving text output of pdftotext: multi-column
caption lines (labels separated by 4+ spaces) are the primary signal.
"""
from __future__ import annotations
import re
import subprocess
import logging
from typing import Dict, Any, List, Optional

from config import BookConfig, LessonChapter

logger = logging.getLogger(__name__)


def extract_all_lessons(
    pages: List[str],
    cfg: BookConfig,
    pdf_path: Optional[str] = None,
    cwd: str = '.',
) -> Dict[str, Dict[str, Any]]:
    """
    Extract lesson text (and optionally diagrams) for all chapters in cfg.

    Returns a dict keyed by str(chapter_id):
    {
        "title":    "...",
        "text":     "...",
        "category": "...",
        "diagrams": []  or  [{"fen": "W:...", "label": "L'enchaînement latéral"}, ...]
    }
    """
    lessons: Dict[str, Dict[str, Any]] = {}
    chapters = sorted(cfg.lesson_chapters, key=lambda c: c.page)

    for i, ch in enumerate(chapters):
        next_start = chapters[i + 1].page if i + 1 < len(chapters) else len(pages) + 1
        ex_page = _find_exercise_page(cfg, ch.chapter_id)
        end_page = min(next_start, ex_page) if ex_page else next_start

        raw = _collect_text(pages, ch.page, end_page)
        text = _clean_lesson_text(raw, ch.title)

        diagrams: List[Dict[str, str]] = []
        if pdf_path:
            diagrams = _extract_lesson_diagrams(pdf_path, ch.page, end_page, cfg, cwd)
            if diagrams:
                logger.info('Chapter %s: %d diagram(s) extracted', ch.chapter_id, len(diagrams))

        lessons[str(ch.chapter_id)] = {
            'title':    ch.title,
            'text':     text,
            'category': ch.category,
            'diagrams': diagrams,
        }

    return lessons


# ── Diagram extraction ────────────────────────────────────────────────────────

def _extract_lesson_diagrams(
    pdf_path: str,
    start_page: int,
    end_page: int,
    cfg: BookConfig,
    cwd: str = '.',
) -> List[Dict[str, str]]:
    """
    Detect board diagrams on lesson pages and return [{fen, label}] in reading order.

    Iterates every page in [start_page, end_page) (1-based).  For each page,
    boards are detected with the same strategy used for exercise pages; their
    FENs are extracted and labels are inferred from the layout text.
    """
    try:
        from pdf_utils import render_page_gray
        from board_detection import find_boards
        from fen_extraction import analyze_board_fen
    except ImportError as e:
        logger.warning('Diagram extraction skipped (import error): %s', e)
        return []

    all_diagrams: List[Dict[str, str]] = []
    global_idx = 0  # running index for fallback labels

    for page_num in range(start_page, end_page):
        try:
            gray = render_page_gray(pdf_path, page_num, cwd=cwd)
        except Exception as e:
            logger.debug('render_page_gray page %d failed: %s', page_num, e)
            continue
        if gray is None:
            continue

        boards = find_boards(
            gray,
            style=cfg.board_style,
            min_border_run=cfg.min_border_run,
            expected_board_px=cfg.expected_board_px,
        )
        if not boards:
            continue

        labels = _extract_labels_from_page(pdf_path, page_num, len(boards))

        for j, (x1, y1, x2, y2) in enumerate(boards):
            try:
                fen = analyze_board_fen(
                    gray, x1, y1, x2, y2,
                    to_move='W',
                    white_threshold=cfg.white_piece_threshold,
                    black_threshold=cfg.black_piece_threshold,
                    sample_radius=cfg.sample_radius,
                )
            except Exception as e:
                logger.debug('analyze_board_fen board %d page %d failed: %s', j, page_num, e)
                continue

            global_idx += 1
            label = labels[j] if j < len(labels) else f'Diag. {global_idx}'
            all_diagrams.append({'fen': fen, 'label': label})

    return all_diagrams


def _extract_labels_from_page(
    pdf_path: str,
    page_num: int,
    board_count: int,
) -> List[str]:
    """
    Infer diagram labels from the pdftotext -layout output of a single page.

    Labels are short phrases (1-7 words, no digits) that appear below boards.
    In multi-board pages they share a single text line, separated by 4+ spaces.
    Single-column pages may have one label per line.

    Returns a list of up to board_count labels; missing entries fall back to
    the caller's "Diag. N" scheme.
    """
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', '-f', str(page_num), '-l', str(page_num),
             pdf_path, '-'],
            capture_output=True, text=True, check=False, encoding='utf-8',
        )
        text = result.stdout
    except Exception as e:
        logger.debug('pdftotext -layout page %d failed: %s', page_num, e)
        return []

    labels: List[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Skip pure page numbers
        if re.match(r'^\d+$', stripped):
            continue
        # Skip section headers ending with ":"
        if stripped.endswith(':'):
            continue

        # Split on 4+ consecutive spaces (multi-column indicator)
        parts = [p.strip() for p in re.split(r' {4,}', line) if p.strip()]

        if len(parts) >= 2:
            # Multi-column line — each part is a candidate label
            valid = [p for p in parts if _is_label(p)]
            if len(valid) >= 2:
                labels.extend(valid)
                continue

        # Single phrase on the line — accept only if it looks like a label
        if len(parts) == 1 and _is_label(parts[0]):
            # Only add standalone labels when we still need them and they're
            # not ordinary prose sentences (prose lines are usually longer)
            if len(labels) < board_count and len(parts[0].split()) <= 5:
                labels.append(parts[0])

    # Trim to board_count
    return labels[:board_count]


def _is_label(text: str) -> bool:
    """Return True if text looks like a board-diagram caption."""
    words = text.split()
    return (
        1 <= len(words) <= 7
        and not re.search(r'\d', text)       # no digits
        and len(text) < 55                    # not a full sentence
        and bool(re.search(r'[a-zA-ZÀ-ÿ]', text))  # has letters
        and not text.endswith(':')            # not a section header
    )


# ── Text helpers ──────────────────────────────────────────────────────────────

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
        if re.match(r'^\d{1,3}$', stripped):
            continue
        if stripped.lower() == title.lower():
            continue
        cleaned.append(line)

    text = '\n'.join(cleaned)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
