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
    # Full list of 35 chapters (101-135). Pages are exact PDF start pages.
    # "en création" chapters have only a title page and produce near-empty lessons.
    lesson_chapters=[
        LessonChapter(101,   5, "Chapitre 1 : la notion d'espace",                      "generalites"),
        LessonChapter(102,   8, "Chapitre 2 : la notion d'avantage",                    "generalites"),
        LessonChapter(103,  14, "Chapitre 3 : la liberté de mouvement relative",        "generalites"),
        LessonChapter(104,  19, "Chapitre 4 : les échanges",                            "generalites"),
        LessonChapter(105,  24, "Chapitre 5 : les temps d'avance",                      "generalites"),
        LessonChapter(106,  32, "Chapitre 6 : les temps de réserve",                    "generalites"),
        LessonChapter(107,  36, "Chapitre 7 : les pions « arrière » ou « suspendus »",  "generalites"),
        LessonChapter(108,  40, "Chapitre 8 : le pion d'angle 46 (1ère partie)",        "pions_de_base"),
        LessonChapter(109,  48, "Chapitre 9 : le pion d'angle 46 (seconde partie)",     "pions_de_base"),
        LessonChapter(110,  53, "Chapitre 10 : le pion d'angle 46 (3e partie)",         "pions_de_base"),
        LessonChapter(111,  61, "Chapitre 11 : le pion de base 47 (1ère partie)",       "pions_de_base"),
        LessonChapter(112,  64, "Chapitre 12 : le pion de base 47 (2e partie)",         "pions_de_base"),
        LessonChapter(113,  68, "Chapitre 13 : le pion savant (1ère partie)",           "pions_de_base"),
        LessonChapter(114,  71, "Chapitre 14 : le pion savant (2e partie)",             "pions_de_base"),
        LessonChapter(115,  74, "Chapitre 15 : les pions de base 49 et 50",             "pions_de_base"),
        LessonChapter(116,  81, "Chapitre 16 : le pion blanc 36",                       "pions_de_bande"),
        LessonChapter(117,  86, "Chapitre 17 : le pion de bande 26",                    "pions_de_bande"),
        LessonChapter(118,  93, "Chapitre 18 : le pion de bande 16 (en création)",      "pions_de_bande"),
        LessonChapter(119,  94, "Chapitre 19 : le pion de bande 6 (en création)",       "pions_de_bande"),
        LessonChapter(120,  95, "Chapitre 20 : le pion blanc 45",                       "pions_de_bande"),
        LessonChapter(121, 102, "Chapitre 21 : le pion blanc 35",                       "pions_de_bande"),
        LessonChapter(122, 107, "Chapitre 22 : le pion blanc 25 (en création)",         "pions_de_bande"),
        LessonChapter(123, 108, "Chapitre 23 : le pion 15 - les spécificités",          "pions_de_bande"),
        LessonChapter(124, 116, "Chapitre 24 : le pion 27 (en création)",               "pions_offensifs"),
        LessonChapter(125, 117, "Chapitre 25 : le pion 28 (en création)",               "pions_offensifs"),
        LessonChapter(126, 118, "Chapitre 26 : le pion 29 (en création)",               "pions_offensifs"),
        LessonChapter(127, 119, "Chapitre 27 : le pion 22 (en création)",               "pions_offensifs"),
        LessonChapter(128, 120, "Chapitre 28 : le pion 23 (en création)",               "pions_offensifs"),
        LessonChapter(129, 121, "Chapitre 29 : le pion 24 appelé « pion taquin »",      "pions_offensifs"),
        LessonChapter(130, 127, "Chapitre 30 : la formation 45-40",                     "formations"),
        LessonChapter(131, 135, "Chapitre 31 : la flèche 33-38-42",                     "formations"),
        LessonChapter(132, 143, "Chapitre 32 : la formation 34-39-43",                  "formations"),
        LessonChapter(133, 148, "Chapitre 33 : la flèche 27-31-36 (en création)",       "formations"),
        LessonChapter(134, 149, "Chapitre 34 : la formation du marchand de bois (en création)", "formations"),
        LessonChapter(135, 150, "Chapitre 35 : la formation 34-35-40-45 (en création)", "formations"),
    ],

    output_exercises_py='backend/db/sens_du_jeu_exercises.py',
    output_lessons_json='backend/sens_du_jeu_lessons.json',
)
