"""
Exercise verification against the Scan draughts engine.

Two modes:
  --legality-only  (default when Scan not available)
    Checks every stored exercise solution against legal moves from the FEN.
    Catches: source square not occupied, illegal destination, etc.

  --scan  (requires Scan binary)
    Additionally queries Scan for the best move at a given search depth and
    compares it with the stored first move.  A mismatch does NOT necessarily
    mean the exercise is wrong (Scan may find an alternative winning line),
    but a mismatch combined with a legality failure always signals a bug.

Usage:
    # From the project root:
    python scripts/book_extraction/verify_exercises_scan.py
    python scripts/book_extraction/verify_exercises_scan.py --scan
    python scripts/book_extraction/verify_exercises_scan.py --scan --time 0.5
    python scripts/book_extraction/verify_exercises_scan.py --chapter "102"
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import re
from typing import Optional

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, '..', '..', 'backend'))
sys.path.insert(0, _BACKEND)

from game_engine import fen_to_board, get_legal_moves, EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING


# ── FEN → Hub position ────────────────────────────────────────────────────────

_PIECE_CHAR = {
    EMPTY: 'e',
    WHITE_MAN: 'w',
    WHITE_KING: 'W',
    BLACK_MAN: 'b',
    BLACK_KING: 'B',
}


def fen_to_hub(fen: str) -> str:
    """Convert a FEN string to a 51-char Scan Hub position string."""
    state = fen_to_board(fen)
    turn_char = 'W' if state.turn == 'white' else 'B'
    return turn_char + ''.join(_PIECE_CHAR[state.board[sq]] for sq in range(1, 51))


# ── Legal-move helpers ────────────────────────────────────────────────────────

def _parse_stored_move(mv: str):
    """Return (from_sq, to_sq) for a stored move string like '34-29' or '23x14'."""
    if '-' in mv:
        parts = mv.split('-')
    elif 'x' in mv:
        parts = mv.split('x')
    else:
        return None, None
    try:
        return int(parts[0]), int(parts[-1])
    except ValueError:
        return None, None


def check_legality(fen: str, stored_moves: list[str]) -> dict:
    """
    Check whether the stored solution's first move is legal in the position.

    Returns a dict with:
      'legal_first'  : bool — stored first move is in the legal-move list
      'first_legal_moves': list[str] — all legal moves as 'from-to' notation
      'source_occupied': bool — source square has a piece of the right colour
    """
    if not stored_moves:
        return {'legal_first': False, 'first_legal_moves': [], 'source_occupied': False}

    state = fen_to_board(fen)
    legal = get_legal_moves(state)
    legal_strs = set()
    for m in legal:
        frm, to = m.path[0], m.path[-1]
        sep = 'x' if m.captures else '-'
        legal_strs.add(f'{frm}{sep}{to}')

    first = stored_moves[0]
    frm, to = _parse_stored_move(first)

    # Normalise stored move to from-to form for comparison
    if frm is not None:
        sep = 'x' if 'x' in first else '-'
        normalised = f'{frm}{sep}{to}'
    else:
        normalised = first

    source_occupied = False
    if frm is not None:
        piece = state.board[frm] if 1 <= frm <= 50 else EMPTY
        if state.turn == 'white':
            source_occupied = piece in (WHITE_MAN, WHITE_KING)
        else:
            source_occupied = piece in (BLACK_MAN, BLACK_KING)

    return {
        'legal_first': normalised in legal_strs,
        'first_legal_moves': sorted(legal_strs),
        'source_occupied': source_occupied,
    }


# ── Scan verification ─────────────────────────────────────────────────────────

def _get_scan_engine(scan_path: str, use_book: bool = False):
    """Lazily import and create a ScanEngine (no-book for objective evaluation)."""
    sys.path.insert(0, _BACKEND)
    from scan_engine import ScanEngine
    return ScanEngine(scan_path, use_book=use_book)


def verify_with_scan(fen: str, stored_first_move: str, engine, movetime: float) -> dict:
    """
    Ask Scan for best move and compare with stored first move.

    Returns:
      'scan_move'  : str|None — move Scan recommends in Hub notation
      'match'      : bool     — Scan agrees with our stored first move
    """
    hub_pos = fen_to_hub(fen)
    scan_move = engine.best_move(hub_pos, movetime)
    if scan_move is None:
        return {'scan_move': None, 'match': False}

    # Normalise both to 'from-to' or 'from x to' for comparison
    def normalise(mv: str) -> tuple[int, int]:
        if '-' in mv:
            p = mv.split('-')
        else:
            p = mv.split('x')
        try:
            return int(p[0]), int(p[-1])
        except ValueError:
            return (-1, -1)

    scan_pair = normalise(scan_move)
    stored_pair = normalise(stored_first_move)
    return {
        'scan_move': scan_move,
        'match': scan_pair == stored_pair,
    }


# ── Main report ───────────────────────────────────────────────────────────────

def run_verification(
    exercises: list[dict],
    use_scan: bool = False,
    scan_path: str = '/usr/local/bin/scan',
    movetime: float = 0.3,
    chapter_filter: Optional[str] = None,
) -> None:
    if chapter_filter:
        exercises = [ex for ex in exercises if chapter_filter in ex.get('category', '')]

    engine = None
    if use_scan:
        if not os.path.isfile(scan_path) or os.path.getsize(scan_path) < 1000:
            print(f'  Scan binary not found at {scan_path!r} — falling back to legality-only mode')
            use_scan = False
        else:
            try:
                engine = _get_scan_engine(scan_path)
                print(f'  Scan engine started ({movetime}s per position)\n')
            except Exception as exc:
                print(f'  Could not start Scan: {exc} — falling back to legality-only mode\n')
                use_scan = False

    WIDTH = 70
    ok_count = 0
    illegal_count = 0
    scan_mismatch_count = 0
    results = []

    for ex in exercises:
        name = ex.get('name', '?')
        fen = ex.get('initial_fen', '')
        sol = ex.get('solution_moves', [])

        leg = check_legality(fen, sol)
        scan_result = None
        if use_scan and engine and sol:
            scan_result = verify_with_scan(fen, sol[0], engine, movetime)

        status = 'OK'
        notes = []

        if not leg['legal_first']:
            if not leg['source_occupied']:
                status = 'ILLEGAL'
                notes.append(f'first move {sol[0]!r}: source square not occupied by mover')
            else:
                status = 'ILLEGAL'
                notes.append(f'first move {sol[0]!r}: move not in legal list')
            notes.append(f'legal moves: {", ".join(leg["first_legal_moves"][:6])}...'
                         if len(leg["first_legal_moves"]) > 6
                         else f'legal moves: {", ".join(leg["first_legal_moves"])}')
            illegal_count += 1
        elif scan_result and not scan_result['match']:
            status = 'SCAN_MISMATCH'
            notes.append(f'stored: {sol[0]!r}  scan: {scan_result["scan_move"]!r}')
            scan_mismatch_count += 1
        else:
            ok_count += 1

        results.append((name, status, notes, fen, sol))

    # ── Print report ──────────────────────────────────────────────────────────
    print(f'\n{"─"*WIDTH}')
    mode = 'SCAN + LEGALITY' if use_scan else 'LEGALITY ONLY'
    print(f'EXERCISE VERIFICATION  ({len(exercises)} exercises) — {mode}')
    print(f'{"─"*WIDTH}')
    print(f'  OK             : {ok_count}')
    print(f'  Illegal move   : {illegal_count}')
    if use_scan:
        print(f'  Scan mismatch  : {scan_mismatch_count}')
    print(f'{"─"*WIDTH}')

    problems = [(n, s, notes, fen, sol) for n, s, notes, fen, sol in results if s != 'OK']
    if not problems:
        print('\n  ✓ All checks passed')
    else:
        print(f'\n  {len(problems)} problem(s) found:\n')
        for name, status, notes, fen, sol in problems:
            tag = '✗ ILLEGAL' if status == 'ILLEGAL' else '? SCAN MISMATCH'
            print(f'  [{tag}] {name}')
            print(f'    FEN : {fen}')
            print(f'    SOL : {sol}')
            for note in notes:
                print(f'    → {note}')
            print()

    print(f'{"─"*WIDTH}\n')


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description='Verify exercise solutions against Scan.')
    parser.add_argument('--scan', action='store_true', help='Use Scan engine for verification')
    parser.add_argument('--scan-path', default='/usr/local/bin/scan', help='Path to Scan binary')
    parser.add_argument('--time', type=float, default=0.3, metavar='SEC',
                        help='Search time per position in seconds (default 0.3)')
    parser.add_argument('--chapter', default=None, metavar='CATEGORY',
                        help='Filter by category substring, e.g. "sdj_ch102"')
    args = parser.parse_args()

    sys.path.insert(0, _BACKEND)
    from db.sens_du_jeu_exercises import SENS_DU_JEU_EXERCISES

    run_verification(
        exercises=SENS_DU_JEU_EXERCISES,
        use_scan=args.scan,
        scan_path=args.scan_path,
        movetime=args.time,
        chapter_filter=args.chapter,
    )


if __name__ == '__main__':
    main()
