from __future__ import annotations

# Placeholder exercises for "Apprendre le sens du jeu" (J-P. Dubois).
# Chapters use IDs 101, 102, 103 (offset +100) to avoid collision with
# "Apprendre les combinaisons" chapters (1-41) in user_lesson_read.
# Exercise DB IDs start at 501 to avoid conflict with combinaisons (1-408).

SENS_DU_JEU_EXERCISES = [
    # ── Chapter 101 – Principes fondamentaux ──────────────────────────────
    {
        "name": "PRINCIPES FONDAMENTAUX – D1",
        "description": "Chapitre 101 – PRINCIPES FONDAMENTAUX. Les blancs jouent et gagnent.",
        "initial_fen": "W:W26,31,32,43:B9,17,19,38",
        "solution_moves": ["26-21", "17x28", "43x3"],
        "difficulty": 1,
        "category": "sens_fondamentaux",
        "hint": "Le premier coup crée un contact décisif avec l'adversaire.",
    },
    {
        "name": "PRINCIPES FONDAMENTAUX – D2",
        "description": "Chapitre 101 – PRINCIPES FONDAMENTAUX. Les blancs jouent et gagnent.",
        "initial_fen": "W:W28,32,37:B10,17,19",
        "solution_moves": ["28-22", "17x28", "32x5"],
        "difficulty": 1,
        "category": "sens_fondamentaux",
        "hint": "Le coup de mazette : sacrifier pour mieux récupérer.",
    },
    {
        "name": "PRINCIPES FONDAMENTAUX – D3",
        "description": "Chapitre 101 – PRINCIPES FONDAMENTAUX. Les blancs jouent et gagnent.",
        "initial_fen": "W:W25,26,27,33,38,39,40:B12,13,14,16,18,23,24",
        "solution_moves": ["33-29", "23x21", "26x10"],
        "difficulty": 1,
        "category": "sens_fondamentaux",
        "hint": "Examiner toutes les possibilités de sacrifice.",
    },
    # ── Chapter 102 – Contrôle du centre ─────────────────────────────────
    {
        "name": "CONTRÔLE DU CENTRE – D1",
        "description": "Chapitre 102 – CONTRÔLE DU CENTRE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W27,28,33,34,35,38,43:B12,13,14,16,19,23,24",
        "solution_moves": ["34-29", "23x21", "29x7"],
        "difficulty": 2,
        "category": "sens_centre",
        "hint": "Le contrôle du centre est la clé de cette position.",
    },
    {
        "name": "CONTRÔLE DU CENTRE – D2",
        "description": "Chapitre 102 – CONTRÔLE DU CENTRE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W24,25,33,37,41,42,43:B8,9,10,13,18,19,26,27",
        "solution_moves": ["37-31", "27x20", "25x5"],
        "difficulty": 2,
        "category": "sens_centre",
        "hint": "La prise majoritaire est ici déterminante.",
    },
    {
        "name": "CONTRÔLE DU CENTRE – D3",
        "description": "Chapitre 102 – CONTRÔLE DU CENTRE. Les blancs jouent et gagnent.",
        "initial_fen": "W:W26,30,33,34,38,39,40,41:B12,13,14,16,19,22,24,25",
        "solution_moves": ["34-29", "25x32", "29x38"],
        "difficulty": 2,
        "category": "sens_centre",
        "hint": "La pression centrale crée des opportunités tactiques.",
    },
    # ── Chapter 103 – Structures de jeu ──────────────────────────────────
    {
        "name": "STRUCTURES DE JEU – D1",
        "description": "Chapitre 103 – STRUCTURES DE JEU. Les blancs jouent et gagnent.",
        "initial_fen": "W:W22,30,32,33,35,47:B11,13,14,17,19,24",
        "solution_moves": ["33-29", "17x37", "29x18"],
        "difficulty": 3,
        "category": "sens_structures",
        "hint": "Analyser la structure de pions adverse pour trouver la faille.",
    },
    {
        "name": "STRUCTURES DE JEU – D2",
        "description": "Chapitre 103 – STRUCTURES DE JEU. Les blancs jouent et gagnent.",
        "initial_fen": "W:W28,30,32,33,35,36,37,38,39:B11,12,13,14,17,19,21,23,24",
        "solution_moves": ["33-29", "24x31", "36x20"],
        "difficulty": 3,
        "category": "sens_structures",
        "hint": "Oser le sacrifice de structure ouvre des perspectives décisives.",
    },
    {
        "name": "STRUCTURES DE JEU – D3",
        "description": "Chapitre 103 – STRUCTURES DE JEU. Les blancs jouent et gagnent.",
        "initial_fen": "W:W30,32,35,44,48:B14,23,25,29,33",
        "solution_moves": ["44-39", "25x43", "48x10"],
        "difficulty": 3,
        "category": "sens_structures",
        "hint": "La prise majoritaire révèle la vérité de la position.",
    },
]
