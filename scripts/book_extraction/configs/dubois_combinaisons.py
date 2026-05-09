"""
Config for 'Apprendre les combinaisons' — J-P. Dubois
PDF: docs/livres/apprentissage/dubois_apprendre_combinaisons.pdf

Board style: classic dark/light board.
  Boards are detected by the dark_squares strategy (checkerboard fill pattern).
  Pieces: white pieces on light squares, black pieces on dark squares.

Chapter ID offset: 0 (this is the first/reference book, chapters 1-41).
Exercise ID offset: 0 (exercises get DB IDs 1-408).

NOTE: This book's extraction was done manually before the automated pipeline
existed. The exercises are in backend/db/exercises_data.py and lessons in
backend/lessons.json.  This config exists as a reference / for re-extraction.

──────────────────────────────────────────────────────────────
Verified extraction:  408 exercises, 41 lesson chapters.
──────────────────────────────────────────────────────────────
"""
from sys import path as _path
from os.path import dirname as _dir, abspath as _abs

_path.insert(0, _dir(_dir(_abs(__file__))))

from config import BookConfig, ChapterExerciseBlock, LessonChapter

# ── Chapter structure for combinaisons ──────────────────────────────────────
# 1re partie:  chapitres 1-6   (combinaisons en N temps)
# 2e partie:   chapitres 7-19  (sacrifices et prises)
# 3e partie:   chapitres 20-41 (thèmes tactiques)
#
# Each chapter has ~6-12 exercises (D1…Dn).
# Solution pages directly follow exercise pages.
#
# ── Board detection notes ────────────────────────────────────────────────────
# Classic dark/light boards: dark squares are clearly filled (~30 px mean).
# Use dark_squares strategy with dark_threshold=80.
# Expected board size at 200 DPI: ~480px (slightly smaller than sens_du_jeu).
#
# ── IMPORTANT ───────────────────────────────────────────────────────────────
# This config's exercise_chapters list is INCOMPLETE.
# It contains only the first 3 chapters as an example.
# A full re-extraction would require mapping all 41 chapters to their PDF pages.

CONFIG = BookConfig(
    book_id='dubois_combinaisons',
    title_fr='Apprendre les combinaisons',
    title_en='Learning combinations',
    pdf_path='docs/livres/apprentissage/dubois_apprendre_combinaisons.pdf',

    exercise_id_offset=0,
    chapter_id_offset=0,

    # ── Board detection ──────────────────────────────────────────────────────
    board_style='dark_squares',
    expected_board_px=480,

    # ── Piece thresholds (classic dark/light board) ──────────────────────────
    # White pieces sit on dark squares and appear very bright (cv ~240-255).
    # Black pieces appear very dark (cv ~20-40).
    # Empty dark squares: cv ~80-120.
    white_piece_threshold=200.0,
    black_piece_threshold=60.0,
    sample_radius=8,

    difficulty_map={
        1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1,   # combinaisons en N temps
        7: 2, 8: 2, 9: 2, 10: 2, 11: 2, 12: 2, 13: 2, 14: 2, 15: 2, 16: 2, 17: 2, 18: 2, 19: 2,
        **{ch: 3 for ch in range(20, 42)},
    },

    # Partial list — extend for full re-extraction
    exercise_chapters=[
        ChapterExerciseBlock(8,   9,   1, "COMBINAISONS EN 2 TEMPS",   "combinaisons en 2 temps",   6),
        ChapterExerciseBlock(13,  14,  2, "COMBINAISONS EN 3 TEMPS",   "combinaisons en 3 temps",   6),
        ChapterExerciseBlock(17,  18,  3, "COMBINAISONS EN 4 TEMPS",   "combinaisons en 4 temps",   6),
        # … add remaining 38 chapters …
    ],

    lesson_chapters=[
        LessonChapter(1,  6,  "Chapitre 1 : combinaisons en 2 temps",   "combinaisons"),
        LessonChapter(2,  11, "Chapitre 2 : combinaisons en 3 temps",   "combinaisons"),
        LessonChapter(3,  15, "Chapitre 3 : combinaisons en 4 temps",   "combinaisons"),
        # … add remaining 38 chapters …
    ],

    output_exercises_py='backend/db/exercises_data.py',   # existing file
    output_lessons_json='backend/lessons.json',            # existing file
)
