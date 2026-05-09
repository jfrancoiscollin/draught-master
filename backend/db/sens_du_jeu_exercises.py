from __future__ import annotations

# Placeholder exercises for "Apprendre le sens du jeu" (J-P. Dubois).
# Chapters use IDs 101-133 (offset +100) to avoid collision with
# "Apprendre les combinaisons" chapters (1-41) in user_lesson_read.
# Exercise DB IDs start at 501 to avoid conflict with combinaisons (1-408).
#
# Real book structure (5 parties, 33 chapters):
#   1re partie : généralités         → chapters 101-107
#   2e partie : les pions de base    → chapters 108-115
#   3e partie : les pions de bande   → chapters 116-123
#   4e partie : les pions offensifs  → chapters 124-129
#   5e partie : les formations       → chapters 130-133

SENS_DU_JEU_EXERCISES = [
    # ── Chapter 101 – 1re partie, Ch. 1 : la notion d'espace ─────────────
    {
        "name": "LA NOTION D'ESPACE – D1",
        "description": "Chapitre 101 – LA NOTION D'ESPACE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W26,31,32,43:B9,17,19,38",
        "solution_moves": ["26-21", "17x28", "43x3"],
        "difficulty": 1,
        "category": "sens_generalites",
        "hint": "Le premier coup crée un contact décisif avec l'adversaire.",
    },
    {
        "name": "LA NOTION D'ESPACE – D2",
        "description": "Chapitre 101 – LA NOTION D'ESPACE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W28,32,37:B10,17,19",
        "solution_moves": ["28-22", "17x28", "32x5"],
        "difficulty": 1,
        "category": "sens_generalites",
        "hint": "Le coup de mazette : sacrifier pour mieux récupérer.",
    },
    {
        "name": "LA NOTION D'ESPACE – D3",
        "description": "Chapitre 101 – LA NOTION D'ESPACE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W25,26,27,33,38,39,40:B12,13,14,16,18,23,24",
        "solution_moves": ["33-29", "23x21", "26x10"],
        "difficulty": 1,
        "category": "sens_generalites",
        "hint": "Examiner toutes les possibilités de sacrifice.",
    },
    # ── Chapter 102 – 1re partie, Ch. 2 : la notion d'avantage ──────────
    {
        "name": "LA NOTION D'AVANTAGE – D1",
        "description": "Chapitre 102 – LA NOTION D'AVANTAGE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W27,28,33,34,35,38,43:B12,13,14,16,19,23,24",
        "solution_moves": ["34-29", "23x21", "29x7"],
        "difficulty": 1,
        "category": "sens_generalites",
        "hint": "Le contrôle du centre est la clé de cette position.",
    },
    {
        "name": "LA NOTION D'AVANTAGE – D2",
        "description": "Chapitre 102 – LA NOTION D'AVANTAGE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W24,25,33,37,41,42,43:B8,9,10,13,18,19,26,27",
        "solution_moves": ["37-31", "27x20", "25x5"],
        "difficulty": 1,
        "category": "sens_generalites",
        "hint": "La prise majoritaire est ici déterminante.",
    },
    {
        "name": "LA NOTION D'AVANTAGE – D3",
        "description": "Chapitre 102 – LA NOTION D'AVANTAGE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W26,30,33,34,38,39,40,41:B12,13,14,16,19,22,24,25",
        "solution_moves": ["34-29", "25x32", "29x38"],
        "difficulty": 1,
        "category": "sens_generalites",
        "hint": "La pression centrale crée des opportunités tactiques.",
    },
    # ── Chapter 103 – 1re partie, Ch. 3 : la liberté de mouvement relative
    {
        "name": "LIBERTÉ DE MOUVEMENT – D1",
        "description": "Chapitre 103 – LIBERTÉ DE MOUVEMENT RELATIVE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W22,30,32,33,35,47:B11,13,14,17,19,24",
        "solution_moves": ["33-29", "17x37", "29x18"],
        "difficulty": 2,
        "category": "sens_generalites",
        "hint": "Analyser la liberté de mouvement de chaque camp.",
    },
    {
        "name": "LIBERTÉ DE MOUVEMENT – D2",
        "description": "Chapitre 103 – LIBERTÉ DE MOUVEMENT RELATIVE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W28,30,32,33,35,36,37,38,39:B11,12,13,14,17,19,21,23,24",
        "solution_moves": ["33-29", "24x31", "36x20"],
        "difficulty": 2,
        "category": "sens_generalites",
        "hint": "Oser le sacrifice de structure ouvre des perspectives décisives.",
    },
    {
        "name": "LIBERTÉ DE MOUVEMENT – D3",
        "description": "Chapitre 103 – LIBERTÉ DE MOUVEMENT RELATIVE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W30,32,35,44,48:B14,23,25,29,33",
        "solution_moves": ["44-39", "25x43", "48x10"],
        "difficulty": 2,
        "category": "sens_generalites",
        "hint": "La prise majoritaire révèle la vérité de la position.",
    },
]
