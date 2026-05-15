"""Conversion BeginnerPosition (manuel Débutant) → ligne `exercises`.

Le seed statique précédent (`INITIAL_EXERCISES` / `SENS_DU_JEU_EXERCISES`)
a été retiré (voir l'historique git). Les exercices viennent désormais
des manuels préprocessés dans dilf — pour l'instant uniquement le
manuel Débutant (`fixtures_debutant.py`).

Convention d'ID :
    Les rangées DB ont des IDs entiers à partir de 2001, attribués dans
    l'ordre lexicographique des identifiants `BEG_CHnn_mmm`. Les IDs
    1-572 ont été utilisés historiquement par les anciens livres Dubois
    statiques ; on laisse un trou pour éviter toute collision avec un
    enregistrement persistant côté Railway.

Conversion :
    - `name`        ← `title`
    - `description` ← "Chapitre X – {title}. {concept}"  (parsable par
                       `_extract_chapter` côté DB)
    - `initial_fen` ← `state_to_fen(state)` via dilf
    - `solution_moves` ← `published_notation` parsée en liste de coups
                          (parens enlevées, tokens non-coups filtrés)
    - `difficulty` ← 1 pour CH01-02 (règles), 2 pour CH03-08
                      (mécanismes), 3 pour CH09-16 (coups nommés)
    - `category`   ← `theme` (ex. "coup_express", "envoi_a_dame")
    - `hint`       ← `concept`
    - `book_id`    ← "manuel_debutant"

Sont exclues :
    - les fixtures sans `published_notation` (chapitres 1-2 illustratifs,
      9 fixtures concernées).
    - les fixtures avec `(ad lib)` (captures forcées équivalentes,
      non-déterministes : 1 fixture, BEG_CH07_012).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pedagogy.game import state_to_fen

from . import fixtures_debutant as fx
from .fixtures_debutant import BeginnerPosition


MANUEL_DEBUTANT_BOOK_ID = "manuel_debutant"
DEBUTANT_ID_OFFSET = 2000  # IDs 2001+ for manuel_debutant exercises


def _parse_solution_moves(notation: str) -> Optional[List[str]]:
    """Parse `published_notation` into a list of move strings.

    Returns None if the notation contains untranslatable tokens (e.g.
    `(ad lib)`) or yields no moves.
    """
    if not notation:
        return None
    moves: List[str] = []
    for tok in re.findall(r"\([^)]+\)|\S+", notation):
        inside = tok.startswith("(") and tok.endswith(")")
        body = tok[1:-1] if inside else tok
        if "ad lib" in body.lower():
            return None
        if "-" not in body and "x" not in body:
            continue
        if " " in body or any(c.isalpha() for c in body.replace("x", "").replace("-", "")):
            continue
        moves.append(body)
    return moves or None


def _difficulty_for_chapter(chapter: int) -> int:
    if chapter <= 2:
        return 1   # règles
    if chapter <= 8:
        return 2   # mécanismes
    return 3       # coups nommés


def _beginner_to_exercise(pos: BeginnerPosition) -> Optional[Dict[str, Any]]:
    moves = _parse_solution_moves(pos.published_notation)
    if moves is None:
        return None
    m = re.match(r"BEG_CH(\d+)_(\d+)", pos.id)
    if not m:
        return None
    chapter = int(m.group(1))
    return {
        "name": pos.title,
        "description": f"Chapitre {chapter} – {pos.title}. {pos.concept}".strip(),
        "initial_fen": state_to_fen(pos.state),
        "solution_moves": moves,
        "difficulty": _difficulty_for_chapter(chapter),
        "category": pos.theme,
        "hint": pos.concept,
        "book_id": MANUEL_DEBUTANT_BOOK_ID,
    }


def _first_move_is_legal(initial_fen: str, first_move: str) -> bool:
    """Check that `first_move` is in `get_legal_moves(initial_fen)`.

    Filters out the small minority of manuel fixtures whose
    `published_notation` starts with an opponent setup move in parens —
    the position is correct, the solution is valid in print, but it
    cannot be played from `state` in the side-alternating UI flow.
    """
    from game_engine import fen_to_board, get_legal_moves
    state = fen_to_board(initial_fen)
    if "x" in first_move:
        parts = [int(s) for s in first_move.split("x")]
    else:
        parts = [int(s) for s in first_move.split("-")]
    if len(parts) < 2:
        return False
    target = (parts[0], parts[-1])
    return any(m.path[0] == target[0] and m.path[-1] == target[1] for m in get_legal_moves(state))


def all_debutant_exercises() -> List[Dict[str, Any]]:
    """Return the list of (id-less) exercise dicts ready for DB upsert.

    Caller assigns sequential IDs starting at `DEBUTANT_ID_OFFSET + 1`
    in the order returned here (lexicographic BEG_CHnn_mmm).

    Fixtures whose first solution move isn't legal under
    `game_engine.get_legal_moves` are silently dropped — they exist in
    the manuel as trap demonstrations but don't fit the linear "play
    the solution" UI pattern.
    """
    fixtures = sorted(
        (v for v in vars(fx).values() if isinstance(v, BeginnerPosition)),
        key=lambda p: p.id,
    )
    out: List[Dict[str, Any]] = []
    for p in fixtures:
        ex = _beginner_to_exercise(p)
        if ex is None:
            continue
        if not _first_move_is_legal(ex["initial_fen"], ex["solution_moves"][0]):
            continue
        out.append(ex)
    return out
