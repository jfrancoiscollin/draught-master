"""
Config for 'Apprendre le sens du jeu' — J-P. Dubois
PDF: docs/livres/apprentissage/dubois_apprendre_sens_du_jeu.pdf

Board style: gray/white squares with black border lines.
  Boards are detected by finding horizontal black lines (border_lines strategy).
  Pieces: white pieces ≈ cv 226-232, empty gray squares ≈ 192, black pieces < 115.

Chapter ID offset: +100 so chapters 1-35 of this book become IDs 101-135.
  This avoids collision with combinaisons chapters (1-41) in user_lesson_read.

Exercise ID offset: 500 → exercises get DB IDs 501-572.
  Combinaisons exercises occupy IDs 1-408.

Solution pages: parsed with default D(\d+) pattern.
  D1 parsing fix: prepend \\n before split (see solution_parsing.py).

──────────────────────────────────────────────────────────────
Verified extraction:  72 exercises, 35 lesson chapters.
──────────────────────────────────────────────────────────────
"""
from sys import path as _path
from os.path import dirname as _dir, abspath as _abs, join as _join

# Allow importing from the scripts/book_extraction package
_path.insert(0, _dir(_dir(_abs(__file__))))

from config import BookConfig, ChapterExerciseBlock, LessonChapter

CONFIG = BookConfig(
    book_id='dubois_sens_du_jeu',
    title_fr='Apprendre le sens du jeu',
    title_en='Learning the sense of the game',
    pdf_path='docs/livres/apprentissage/dubois_apprendre_sens_du_jeu.pdf',

    exercise_id_offset=500,
    chapter_id_offset=100,

    # ── Board detection ──────────────────────────────────────────────────────
    # Gray/white boards with black border lines.
    board_style='border_lines',
    min_border_run=400,
    expected_board_px=505,

    # ── Piece detection ──────────────────────────────────────────────────────
    white_piece_threshold=218.0,
    black_piece_threshold=115.0,
    sample_radius=9,

    # ── Difficulty map ───────────────────────────────────────────────────────
    difficulty_map={
        102: 1, 103: 1, 104: 1,          # Partie 1: généralités
        108: 2, 109: 2, 110: 2, 115: 2,  # Partie 2: pions de base
        116: 3, 117: 3, 120: 3, 121: 3,  # Partie 3: pions de bande
        130: 4, 131: 4, 132: 4,          # Partie 5: les formations
    },

    # ── Exercise chapters ────────────────────────────────────────────────────
    # (ex_page, sol_page, chapter_id, short_title, long_title, d_count)
    exercise_chapters=[
        ChapterExerciseBlock(12,  13,  102, "LA NOTION D'AVANTAGE",    "la notion d'avantage",              6),
        ChapterExerciseBlock(17,  18,  103, "LIBERTÉ DE MOUVEMENT",    "la liberté de mouvement relative",  6),
        ChapterExerciseBlock(22,  23,  104, "LES ÉCHANGES",            "les échanges",                      6),
        ChapterExerciseBlock(45,  47,  108, "LE PION D'ANGLE 46 (1)",  "le pion d'angle 46 (1ère partie)",  4),
        ChapterExerciseBlock(51,  52,  109, "LE PION D'ANGLE 46 (2)",  "le pion d'angle 46 (seconde partie)", 5),
        ChapterExerciseBlock(58,  60,  110, "LE PION D'ANGLE 46 (3)",  "le pion d'angle 46 (3e partie)",    4),
        ChapterExerciseBlock(77,  79,  115, "LES PIONS 49 ET 50",      "les pions de base 49 et 50",        6),
        ChapterExerciseBlock(84,  85,  116, "LE PION BLANC 36",        "le pion blanc 36",                  6),
        ChapterExerciseBlock(91,  92,  117, "LE PION DE BANDE 26",     "le pion de bande 26",               5),
        ChapterExerciseBlock(99,  101, 120, "LE PION BLANC 45",        "le pion blanc 45",                  4),
        ChapterExerciseBlock(104, 106, 121, "LE PION BLANC 35",        "le pion blanc 35",                  4),
        ChapterExerciseBlock(132, 134, 130, "LA FORMATION 45-40",      "la formation 45-40",                4),
        ChapterExerciseBlock(141, 142, 131, "LA FLÈCHE 33-38-42",      "la flèche 33-38-42",                6),
        ChapterExerciseBlock(146, 147, 132, "LA FORMATION 34-39-43",   "la formation 34-39-43",             6),
    ],

    # ── Lesson chapters ──────────────────────────────────────────────────────
    # Full list of 35 chapters (101-135). Pages are approximate start pages.
    # Chapters 134-135 had no text ("en création") and produce empty lessons.
    lesson_chapters=[
        LessonChapter(101, 7,   "Chapitre 101 : la notion d'espace",                   "generalites"),
        LessonChapter(102, 11,  "Chapitre 102 : la notion d'avantage",                 "generalites"),
        LessonChapter(103, 16,  "Chapitre 103 : la liberté de mouvement relative",     "generalites"),
        LessonChapter(104, 21,  "Chapitre 104 : les échanges",                         "generalites"),
        LessonChapter(105, 26,  "Chapitre 105 : la domination",                        "generalites"),
        LessonChapter(106, 29,  "Chapitre 106 : le plan de jeu",                       "generalites"),
        LessonChapter(107, 33,  "Chapitre 107 : la stratégie de jeu",                  "generalites"),
        LessonChapter(108, 38,  "Chapitre 108 : le pion d'angle 46 (1ère partie)",     "pions_de_base"),
        LessonChapter(109, 48,  "Chapitre 109 : le pion d'angle 46 (seconde partie)",  "pions_de_base"),
        LessonChapter(110, 54,  "Chapitre 110 : le pion d'angle 46 (3e partie)",       "pions_de_base"),
        LessonChapter(111, 62,  "Chapitre 111 : le pion de base 45",                   "pions_de_base"),
        LessonChapter(112, 65,  "Chapitre 112 : le pion de base 50",                   "pions_de_base"),
        LessonChapter(113, 68,  "Chapitre 113 : le pion de base 46",                   "pions_de_base"),
        LessonChapter(114, 71,  "Chapitre 114 : les pions de base 45 et 50",           "pions_de_base"),
        LessonChapter(115, 74,  "Chapitre 115 : les pions de base 49 et 50",           "pions_de_base"),
        LessonChapter(116, 82,  "Chapitre 116 : le pion blanc 36",                     "pions_de_bande"),
        LessonChapter(117, 88,  "Chapitre 117 : le pion de bande 26",                  "pions_de_bande"),
        LessonChapter(118, 95,  "Chapitre 118 : le pion blanc 31",                     "pions_de_bande"),
        LessonChapter(119, 98,  "Chapitre 119 : le pion blanc 30",                     "pions_de_bande"),
        LessonChapter(120, 97,  "Chapitre 120 : le pion blanc 45",                     "pions_de_bande"),
        LessonChapter(121, 102, "Chapitre 121 : le pion blanc 35",                     "pions_de_bande"),
        LessonChapter(122, 108, "Chapitre 122 : les pions offensifs 26 et 31",         "pions_offensifs"),
        LessonChapter(123, 113, "Chapitre 123 : les pions offensifs 25, 30 et 35",     "pions_offensifs"),
        LessonChapter(124, 118, "Chapitre 124 : les pions offensifs 36 et 41",         "pions_offensifs"),
        LessonChapter(125, 122, "Chapitre 125 : le pion offensif 37",                  "pions_offensifs"),
        LessonChapter(126, 126, "Chapitre 126 : les pions offensifs 32 et 37",         "pions_offensifs"),
        LessonChapter(127, 128, "Chapitre 127 : le trèfle 25-30-35",                   "pions_offensifs"),
        LessonChapter(128, 130, "Chapitre 128 : la flèche 29-34-40",                   "pions_offensifs"),
        LessonChapter(129, 132, "Chapitre 129 : le pion offensif 44",                  "pions_offensifs"),
        LessonChapter(130, 136, "Chapitre 130 : la formation 45-40",                   "formations"),
        LessonChapter(131, 138, "Chapitre 131 : la flèche 33-38-42",                   "formations"),
        LessonChapter(132, 143, "Chapitre 132 : la formation 34-39-43",                "formations"),
        LessonChapter(133, 149, "Chapitre 133 : le tour",                              "formations"),
        LessonChapter(134, 152, "Chapitre 134 : la formation 3-8 (en création)",       "formations"),
        LessonChapter(135, 153, "Chapitre 135 : la formation 4-9 (en création)",       "formations"),
    ],

    output_exercises_py='backend/db/sens_du_jeu_exercises.py',
    output_lessons_json='backend/sens_du_jeu_lessons.json',
)
