"""
Heuristic auto-correction of illegal first moves in SENS_DU_JEU_EXERCISES.

For each exercise whose stored first move is illegal in the FEN:
  1. If the from-square is occupied but the move is blocked (destination occupied
     by own piece): pick the legal move from the same source with the closest
     destination square number.
  2. If the from-square is empty:
     a. Try reversing from/to — catches OCR-transposed pairs (e.g. "23-28" → "28-23").
     b. Find the legal move whose from-square is numerically closest to the stored one.
  3. If no single candidate is unambiguous, mark the entry as UNCERTAIN.

Output:
  - A new corrected file written to backend/db/sens_du_jeu_exercises.py
  - A text log of every substitution printed to stdout
"""
from __future__ import annotations

import ast
import os
import sys
import textwrap

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, '..', 'backend'))
sys.path.insert(0, _BACKEND)

from game_engine import (
    fen_to_board, get_legal_moves,
    EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING,
)
from db.sens_du_jeu_exercises import SENS_DU_JEU_EXERCISES


# ── Move helpers ───────────────────────────────────────────────────────────────

def _parse(mv: str) -> tuple[int | None, int | None, str]:
    sep = 'x' if 'x' in mv else '-'
    parts = mv.split(sep)
    try:
        return int(parts[0]), int(parts[-1]), sep
    except (ValueError, IndexError):
        return None, None, sep


def _legal_pairs(fen: str) -> list[tuple[int, int, str]]:
    state = fen_to_board(fen)
    legal = get_legal_moves(state)
    return [(m.path[0], m.path[-1], 'x' if m.captures else '-') for m in legal]


def _is_legal(fen: str, mv: str) -> bool:
    frm, to, sep = _parse(mv)
    if frm is None:
        return False
    pairs = _legal_pairs(fen)
    return any(f == frm and t == to for f, t, _ in pairs)


def _src_occupied(fen: str, mv: str) -> bool:
    frm, _, _ = _parse(mv)
    if frm is None or not (1 <= frm <= 50):
        return False
    state = fen_to_board(fen)
    piece = state.board[frm]
    if state.turn == 'white':
        return piece in (WHITE_MAN, WHITE_KING)
    return piece in (BLACK_MAN, BLACK_KING)


def _fmt(f: int, t: int, s: str) -> str:
    return f"{f}{s}{t}"


# ── Heuristic fixer ────────────────────────────────────────────────────────────

def suggest(fen: str, stored: str) -> tuple[str | None, str]:
    """Return (suggested_move, reason) or (None, reason) if uncertain."""
    frm, to, sep = _parse(stored)
    pairs = _legal_pairs(fen)

    if not pairs:
        return None, "aucun coup légal dans la position"

    legal_strs = {_fmt(f, t, s) for f, t, s in pairs}

    # ── Case 1: source occupée mais coup absent (destination bloquée) ──────────
    if _src_occupied(fen, stored):
        from_source = [(f, t, s) for f, t, s in pairs if f == frm]
        if len(from_source) == 1:
            return _fmt(*from_source[0]), f"seul coup légal depuis la case {frm}"
        if len(from_source) > 1 and to is not None:
            best = min(from_source, key=lambda x: abs(x[1] - to))
            return _fmt(*best), f"coup légal depuis {frm} avec destination la plus proche de {to}"
        # No legal move exists from this source — treat as wrong source square
        # and fall through to heuristic search below

    # ── Case 2: source vide ───────────────────────────────────────────────────

    # 2a: inversion from/to
    if frm is not None and to is not None:
        reversed_mv = f"{to}{sep}{frm}"
        if reversed_mv in legal_strs:
            return reversed_mv, "from/to inversés (inversion OCR probable)"

    # 2b: from-sq le plus proche parmi les coups légaux
    if frm is not None:
        by_from = sorted(pairs, key=lambda x: abs(x[0] - frm))
        closest_from_sq = by_from[0][0]
        candidates = [p for p in by_from if p[0] == closest_from_sq]
        if len(candidates) == 1:
            return _fmt(*candidates[0]), f"from-sq {closest_from_sq} le plus proche de {frm}"
        # Multiple moves from the closest square — pick one with closest destination
        if to is not None:
            best = min(candidates, key=lambda x: abs(x[1] - to))
            return _fmt(*best), f"from-sq {closest_from_sq} le plus proche, to-sq {best[1]} le plus proche de {to}"
        return _fmt(*candidates[0]), f"from-sq {closest_from_sq} le plus proche (destination ambiguë)"

    return None, "impossible de déterminer le coup correct"


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    corrections: list[dict] = []
    ok = uncertain = 0

    for ex in SENS_DU_JEU_EXERCISES:
        name = ex["name"]
        fen = ex["initial_fen"]
        sol = list(ex.get("solution_moves", []))

        if not sol or _is_legal(fen, sol[0]):
            continue

        stored = sol[0]
        fix, reason = suggest(fen, stored)

        if fix is None or not _is_legal(fen, fix):
            uncertain += 1
            print(f"  [UNCERTAIN] {name}")
            print(f"             Stocké : {stored}")
            print(f"             Raison : {reason}")
            if fix:
                print(f"             Candidat : {fix} (toujours illégal !)")
            print()
            corrections.append({"name": name, "stored": stored, "fix": None, "reason": reason})
        else:
            ok += 1
            print(f"  [FIX] {name}")
            print(f"        {stored}  →  {fix}  ({reason})")
            corrections.append({"name": name, "stored": stored, "fix": fix, "reason": reason})

    print(f"\n{'─'*70}")
    print(f"  Corrigés automatiquement : {ok}")
    print(f"  Incertains               : {uncertain}")
    print(f"{'─'*70}\n")

    if uncertain:
        print("Les exercices UNCERTAIN nécessitent une vérification manuelle ou Scan.\n")

    # ── Apply corrections to the exercise list ────────────────────────────────
    fix_map = {c["name"]: c["fix"] for c in corrections if c["fix"]}

    corrected = []
    for ex in SENS_DU_JEU_EXERCISES:
        ex2 = dict(ex)
        if ex2["name"] in fix_map:
            sol = list(ex2["solution_moves"])
            sol[0] = fix_map[ex2["name"]]
            ex2["solution_moves"] = sol
        corrected.append(ex2)

    # ── Write corrected file ──────────────────────────────────────────────────
    out_path = os.path.join(_BACKEND, "db", "sens_du_jeu_exercises.py")
    _write_corrected(corrected, out_path)
    print(f"Fichier corrigé écrit : {out_path}")


def _write_corrected(exercises: list[dict], path: str) -> None:
    header = textwrap.dedent('''\
        from __future__ import annotations

        # Auto-extracted from dubois_apprendre_sens_du_jeu.pdf
        # Book ID : dubois_sens_du_jeu
        # Exercise IDs : 501 – 572
        # Chapter ID offset : +100 (avoids collision with other books)
        #
        # Chapters:
        #   102 – la notion d\'avantage
        #   103 – la liberté de mouvement relative
        #   104 – les échanges
        #   108 – le pion d\'angle 46 (1ère partie)
        #   109 – le pion d\'angle 46 (seconde partie)
        #   110 – le pion d\'angle 46 (3e partie)
        #   115 – les pions de base 49 et 50
        #   116 – le pion blanc 36
        #   117 – le pion de bande 26
        #   120 – le pion blanc 45
        #   121 – le pion blanc 35
        #   130 – la formation 45-40
        #   131 – la flèche 33-38-42
        #   132 – la formation 34-39-43
        # (first-move corrections applied by scripts/fix_illegal_exercises.py)

        SENS_DU_JEU_EXERCISES = [
    ''')

    lines = [header]
    for ex in exercises:
        lines.append("    {")
        for k, v in ex.items():
            lines.append(f"        {k!r}: {v!r},")
        lines.append("    },")
    lines.append("]\n")

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    main()
