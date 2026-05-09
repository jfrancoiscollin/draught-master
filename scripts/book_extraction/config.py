"""
Book configuration dataclass.

Each book needs one config in configs/. The pipeline reads it to know:
  - Where the PDF lives
  - Which pages carry exercises and their solutions
  - Which pages carry lesson text
  - What IDs to assign (offset strategy avoids DB collisions)
  - Which board-detection algorithm to use
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional


@dataclass
class ChapterExerciseBlock:
    """One chapter's exercise block: the diagram page(s) and solution page(s)."""
    ex_page: int          # 1-based PDF page number containing diagrams
    sol_page: int         # 1-based PDF page containing solutions
    chapter_id: int       # canonical chapter number (after offset)
    short_title: str      # e.g. "LA NOTION D'AVANTAGE"
    long_title: str       # e.g. "la notion d'avantage"
    d_count: int = 0      # expected diagram count (0 = auto-detect)
    sol_page_end: int = 0 # if solutions span multiple pages, last page (0 = single page)


@dataclass
class LessonChapter:
    """Mapping of one chapter to its starting PDF page."""
    chapter_id: int
    page: int
    title: str
    category: str         # e.g. "generalites", "pions_de_base", etc.


@dataclass
class BookConfig:
    # ── Identity ────────────────────────────────────────────────────────────
    book_id: str                    # unique key used in DB and API: 'dubois_sens_du_jeu'
    title_fr: str                   # French title shown in the UI
    title_en: str                   # English title

    # ── Source ──────────────────────────────────────────────────────────────
    pdf_path: str                   # path relative to project root

    # ── ID allocation ───────────────────────────────────────────────────────
    exercise_id_offset: int         # DB id = offset + position_in_list (e.g. 500 → 501…)
    chapter_id_offset: int          # chapter numbers = real_chapter + offset (0 for book 1)

    # ── Content map ─────────────────────────────────────────────────────────
    exercise_chapters: List[ChapterExerciseBlock] = field(default_factory=list)
    lesson_chapters: List[LessonChapter] = field(default_factory=list)

    # ── Board detection ──────────────────────────────────────────────────────
    # 'border_lines'  : scan horizontal black border lines (≥ min_border_run px)
    #                   → works for gray/white boards (sens_du_jeu style)
    # 'dark_squares'  : detect checkerboard pattern from dark fill percentage
    #                   → works for classic dark/light boards (combinaisons style)
    board_style: str = 'border_lines'

    # Tuning for border_lines detection
    min_border_run: int = 400       # minimum run length (px) for a border line
    expected_board_px: int = 505    # expected board side (px) at 200 DPI

    # Tuning for piece detection (pixel mean of center patch)
    white_piece_threshold: float = 218.0   # center patch mean > this → white piece
    black_piece_threshold: float = 115.0   # center patch mean < this → black piece
    sample_radius: int = 9                 # half-size of center sample square

    # ── Solution parsing ─────────────────────────────────────────────────────
    # Pattern to split solution page into per-exercise sections.
    # Group 1 must capture the diagram number (integer string).
    solution_split_pattern: str = r'\nD(\d+)\s*[–\-]\s*'

    # ── Difficulty mapping ───────────────────────────────────────────────────
    # Map chapter_id → difficulty level 1–5.  Missing chapters get level 2.
    difficulty_map: Dict[int, int] = field(default_factory=dict)

    # ── Output paths (filled in by pipeline, can override) ───────────────────
    output_exercises_py: str = ''   # e.g. 'backend/db/sens_du_jeu_exercises.py'
    output_lessons_json: str = ''   # e.g. 'backend/sens_du_jeu_lessons.json'
    varname: str = ''               # Python variable name; auto-derived if empty

    def exercises_varname(self) -> str:
        """Python variable name for the exercises list."""
        if self.varname:
            return self.varname
        # Strip common author prefixes (dubois_, couttet_, etc.) for a clean name
        name = self.book_id.upper()
        for prefix in ('DUBOIS_', 'COUTTET_'):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        return name + '_EXERCISES'

    def get_difficulty(self, chapter_id: int) -> int:
        return self.difficulty_map.get(chapter_id, 2)
