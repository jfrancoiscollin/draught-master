"""
Validation of extracted exercises and lessons.

Run this after extraction to catch problems before writing to the backend.
Prints a structured report and returns a list of issues.

Two levels of exercise validation are available:

  validate_exercises(exercises)
      Fast structural checks: FEN format, duplicate FENs, move notation,
      and a lightweight legality check (source square must be in the mover's
      piece list according to the raw FEN string).

  validate_exercises_with_engine(exercises, backend_path)
      Full legality check using the game engine.  Catches all illegal first
      moves — not just wrong source squares but also blocked destinations,
      forced-capture violations, etc.  Requires the backend on sys.path.
      Falls back gracefully if the engine is not importable.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from config import BookConfig


# ── Exercise validation ───────────────────────────────────────────────────────

def validate_exercises(exercises: List[Dict[str, Any]]) -> List[str]:
    """
    Validate all extracted exercises.  Returns a list of issue strings.
    An empty list means everything passed.
    """
    issues: List[str] = []
    seen_fens: Dict[str, int] = {}

    for i, ex in enumerate(exercises):
        name = ex.get('name', f'exercise[{i}]')
        prefix = f'[{name}]'

        # FEN validation
        fen = ex.get('initial_fen', '')
        ok, reason = _validate_fen(fen)
        if not ok:
            issues.append(f'{prefix} Invalid FEN: {reason} — {fen!r}')

        # Duplicate FEN check
        if fen in seen_fens:
            issues.append(
                f'{prefix} Duplicate FEN (same as exercise[{seen_fens[fen]}])'
            )
        else:
            seen_fens[fen] = i

        # Solution validation
        sol = ex.get('solution_moves', [])
        if not sol:
            issues.append(f'{prefix} EMPTY solution moves')
        else:
            for mv in sol:
                if not _is_valid_move(mv):
                    issues.append(f'{prefix} Suspicious move in solution: {mv!r}')
            # First-move legality: source square must exist in the mover's pieces
            first_move = sol[0]
            src = _first_move_source(first_move)
            if src is not None and fen:
                m_fen = re.match(r'^([WB]):W([\d,]*):B([\d,]*)$', fen)
                if m_fen:
                    turn = m_fen.group(1)
                    pieces = [int(x) for x in m_fen.group(2 if turn == 'W' else 3).split(',') if x]
                    if src not in pieces:
                        issues.append(
                            f'{prefix} First move {first_move!r} starts on sq{src} '
                            f'but that square is not occupied by {turn} — likely wrong FEN'
                        )

        # Required fields
        for field in ('name', 'description', 'initial_fen', 'solution_moves', 'difficulty', 'category'):
            if field not in ex:
                issues.append(f'{prefix} Missing field: {field}')

    return issues


def print_validation_report(exercises: List[Dict[str, Any]]) -> bool:
    """
    Print a human-readable validation report.  Returns True if no issues.
    """
    issues = validate_exercises(exercises)
    total = len(exercises)
    empty_sol = sum(1 for ex in exercises if not ex.get('solution_moves'))

    print(f'\n{"─"*60}')
    print(f'VALIDATION REPORT  ({total} exercises)')
    print(f'{"─"*60}')
    print(f'  Exercises with solutions : {total - empty_sol}/{total}')
    print(f'  Issues found             : {len(issues)}')

    if issues:
        print('\n  Issues:')
        for issue in issues:
            print(f'    ✗ {issue}')
    else:
        print('\n  ✓ All checks passed')

    print(f'{"─"*60}\n')
    return len(issues) == 0


# ── Engine-based legality check ───────────────────────────────────────────────

def validate_exercises_with_engine(
    exercises: List[Dict[str, Any]],
    backend_path: Optional[str] = None,
) -> List[str]:
    """
    Full game-engine legality check on every exercise's first move.

    Catches errors that the lightweight FEN-string check misses:
      - Destination occupied by own piece
      - Non-capture move when a capture is forced
      - Move not geometrically reachable

    Returns a list of issue strings (empty = all OK).
    Falls back to empty list with a warning if the engine cannot be imported.
    """
    import sys
    import os

    if backend_path:
        sys.path.insert(0, backend_path)
    else:
        # Try common relative paths
        for candidate in [
            os.path.join(os.path.dirname(__file__), '..', '..', 'backend'),
        ]:
            p = os.path.normpath(candidate)
            if os.path.isdir(p):
                sys.path.insert(0, p)
                break

    try:
        from game_engine import (
            fen_to_board, get_legal_moves,
            WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING,
        )
    except ImportError as exc:
        import warnings
        warnings.warn(
            f'game_engine not importable — skipping engine legality check: {exc}',
            stacklevel=2,
        )
        return []

    issues: List[str] = []
    for ex in exercises:
        name = ex.get('name', '?')
        fen = ex.get('initial_fen', '')
        sol = ex.get('solution_moves', [])
        if not sol or not fen:
            continue

        first = sol[0]
        sep = 'x' if 'x' in first else '-'
        parts = first.split(sep)
        try:
            frm, to = int(parts[0]), int(parts[-1])
        except (ValueError, IndexError):
            continue

        try:
            state = fen_to_board(fen)
            legal = get_legal_moves(state)
        except Exception as exc:
            issues.append(f'[{name}] Engine error for FEN {fen!r}: {exc}')
            continue

        legal_strs = {
            f"{m.path[0]}{'x' if m.captures else '-'}{m.path[-1]}"
            for m in legal
        }
        norm = f'{frm}{sep}{to}'
        if norm not in legal_strs:
            # Determine why it failed for a helpful message
            src_ok = any(m.path[0] == frm for m in legal)
            if not src_ok:
                reason = f'case {frm} non occupée par le joueur actif'
            else:
                reason = f'coup impossible depuis {frm} (destination {to} bloquée ou capture forcée)'
            issues.append(
                f'[{name}] Premier coup illégal {first!r}: {reason}. '
                f'Coups légaux: {sorted(legal_strs)[:6]}'
            )

    return issues


def print_legality_report(
    exercises: List[Dict[str, Any]],
    backend_path: Optional[str] = None,
) -> bool:
    """Print engine legality report.  Returns True if no issues."""
    issues = validate_exercises_with_engine(exercises, backend_path)
    print(f'\n{"─"*60}')
    print(f'ENGINE LEGALITY CHECK  ({len(exercises)} exercises)')
    print(f'{"─"*60}')
    if issues:
        print(f'  Issues: {len(issues)}')
        for issue in issues:
            print(f'    ✗ {issue}')
    else:
        print('  ✓ All first moves are legal')
    print(f'{"─"*60}\n')
    return len(issues) == 0


# ── Heuristic first-move fixer ────────────────────────────────────────────────

def fix_illegal_first_moves(
    exercises: List[Dict[str, Any]],
    backend_path: Optional[str] = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Attempt to correct illegal first moves using heuristics.

    Returns (corrected_exercises, corrections_log) where corrections_log is a
    list of dicts with keys: name, stored, fix, reason.

    For each illegal exercise:
      1. Source occupied, but destination blocked: find legal move from same
         source with closest destination.
      2. Source empty: try reversing from/to (catches OCR transpositions),
         then find legal move with closest from-square.
    """
    import sys
    import os

    if backend_path:
        sys.path.insert(0, backend_path)
    else:
        for candidate in [
            os.path.join(os.path.dirname(__file__), '..', '..', 'backend'),
        ]:
            p = os.path.normpath(candidate)
            if os.path.isdir(p):
                sys.path.insert(0, p)
                break

    try:
        from game_engine import (
            fen_to_board, get_legal_moves,
            WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING,
        )
    except ImportError as exc:
        import warnings
        warnings.warn(f'game_engine not importable — cannot fix illegal moves: {exc}', stacklevel=2)
        return exercises, []

    def _pairs(fen):
        state = fen_to_board(fen)
        legal = get_legal_moves(state)
        return [(m.path[0], m.path[-1], 'x' if m.captures else '-') for m in legal]

    def _is_legal(fen, mv):
        sep = 'x' if 'x' in mv else '-'
        parts = mv.split(sep)
        try:
            frm, to = int(parts[0]), int(parts[-1])
        except (ValueError, IndexError):
            return False
        return any(f == frm and t == to for f, t, _ in _pairs(fen))

    def _src_occupied(fen, mv):
        sep = 'x' if 'x' in mv else '-'
        parts = mv.split(sep)
        try:
            frm = int(parts[0])
        except (ValueError, IndexError):
            return False
        if not (1 <= frm <= 50):
            return False
        state = fen_to_board(fen)
        piece = state.board[frm]
        if state.turn == 'white':
            return piece in (WHITE_MAN, WHITE_KING)
        return piece in (BLACK_MAN, BLACK_KING)

    def _suggest(fen, stored):
        sep = 'x' if 'x' in stored else '-'
        parts = stored.split(sep)
        try:
            frm, to = int(parts[0]), int(parts[-1])
        except (ValueError, IndexError):
            return None, 'move format unrecognised'

        pairs = _pairs(fen)
        if not pairs:
            return None, 'no legal moves in position'

        legal_strs = {f"{f}{'x' if s == 'x' else '-'}{t}" for f, t, s in pairs}

        if _src_occupied(fen, stored):
            from_source = [(f, t, s) for f, t, s in pairs if f == frm]
            if len(from_source) == 1:
                f2, t2, s2 = from_source[0]
                return f"{f2}{s2}{t2}", f"seul coup légal depuis {frm}"
            if len(from_source) > 1:
                best = min(from_source, key=lambda x: abs(x[1] - to))
                f2, t2, s2 = best
                return f"{f2}{s2}{t2}", f"coup légal depuis {frm} avec to le plus proche de {to}"
            # Source occupied but no legal moves from it — fall through

        # Try reversal
        rev = f"{to}{sep}{frm}"
        if rev in legal_strs:
            return rev, "from/to inversés (inversion OCR probable)"

        # Closest from-square
        by_from = sorted(pairs, key=lambda x: abs(x[0] - frm))
        cf = by_from[0][0]
        candidates = [p for p in by_from if p[0] == cf]
        if len(candidates) == 1:
            f2, t2, s2 = candidates[0]
            return f"{f2}{s2}{t2}", f"from-sq {cf} le plus proche de {frm}"
        best = min(candidates, key=lambda x: abs(x[1] - to))
        f2, t2, s2 = best
        return f"{f2}{s2}{t2}", f"from-sq {cf} le plus proche, to-sq {t2} le plus proche de {to}"

    corrected = []
    log_entries = []
    for ex in exercises:
        ex2 = dict(ex)
        fen = ex2.get('initial_fen', '')
        sol = list(ex2.get('solution_moves', []))
        if sol and not _is_legal(fen, sol[0]):
            stored = sol[0]
            fix, reason = _suggest(fen, stored)
            if fix and _is_legal(fen, fix):
                sol[0] = fix
                ex2['solution_moves'] = sol
                log_entries.append({
                    'name': ex2.get('name', '?'),
                    'stored': stored,
                    'fix': fix,
                    'reason': reason,
                })
            else:
                log_entries.append({
                    'name': ex2.get('name', '?'),
                    'stored': stored,
                    'fix': None,
                    'reason': f'UNCERTAIN — {reason}',
                })
        corrected.append(ex2)

    return corrected, log_entries


# ── Lesson validation ─────────────────────────────────────────────────────────

# Chapters with this string in their title are expected to have minimal text.
_PLACEHOLDER_TITLE_MARKER = 'en création'

# Placeholder text written by hand before real extraction was done.
_PLACEHOLDER_TEXT_FRAGMENTS = [
    '*(Contenu de la leçon à venir)*',
    'contenu de la leçon à venir',
]

# Real chapters below this threshold are almost certainly using a wrong start page.
_MIN_CONTENT_CHARS = 200


def validate_lessons(lessons: Dict[str, Dict[str, Any]]) -> List[str]:
    """
    Validate extracted lessons.  Returns a list of issue strings.

    In addition to structural checks, warns when:
    - A real chapter (not 'en création') has very short text — likely a wrong
      start page number in the config.
    - Text is a known hand-written placeholder ('*(Contenu de la leçon à venir)*').
    """
    issues: List[str] = []
    for ch_id, lesson in lessons.items():
        prefix = f'[chapter {ch_id}]'
        title = lesson.get('title', '')
        text = lesson.get('text', '').strip()
        is_placeholder_chapter = _PLACEHOLDER_TITLE_MARKER in title.lower()

        if not title:
            issues.append(f'{prefix} Missing title')

        if not text:
            issues.append(f'{prefix} Empty text (lesson text not extracted)')
        else:
            # Check for hand-written placeholder text
            for fragment in _PLACEHOLDER_TEXT_FRAGMENTS:
                if fragment in text.lower():
                    issues.append(
                        f'{prefix} Placeholder text detected — lesson was never extracted'
                    )
                    break
            # Check for suspiciously short text in real chapters
            if not is_placeholder_chapter and len(text) < _MIN_CONTENT_CHARS:
                issues.append(
                    f'{prefix} Very short text ({len(text)} chars) for a real chapter'
                    f' — check the start page number in the config'
                )

        if not lesson.get('category'):
            issues.append(f'{prefix} Missing category')

    return issues


def print_lesson_report(lessons: Dict[str, Dict[str, Any]]) -> bool:
    """Print a human-readable lesson validation report.  Returns True if no issues."""
    issues = validate_lessons(lessons)
    real_chapters = sum(
        1 for l in lessons.values()
        if _PLACEHOLDER_TITLE_MARKER not in l.get('title', '').lower()
    )
    empty_count = sum(1 for l in lessons.values() if not l.get('text', '').strip())

    print(f'\n{"─"*60}')
    print(f'LESSON REPORT  ({len(lessons)} chapters, {real_chapters} with content)')
    print(f'{"─"*60}')
    print(f'  Chapters with text : {len(lessons) - empty_count}/{len(lessons)}')
    print(f'  Issues found       : {len(issues)}')

    if issues:
        print('\n  Issues:')
        for issue in issues:
            print(f'    ✗ {issue}')
    else:
        print('\n  ✓ All lesson checks passed')

    print(f'{"─"*60}\n')
    return len(issues) == 0


# ── Config validation ────────────────────────────────────────────────────────

def validate_config(cfg: 'BookConfig') -> List[str]:
    """
    Validate a BookConfig before running extraction.  Returns a list of issues.

    Key checks:
    - Chapter titles must NOT embed the internal chapter_id (offset ID).
      The display title should use the book-relative chapter number, not the
      DB id.  E.g. "Chapitre 2 : ..." is correct; "Chapitre 102 : ..." leaks
      the chapter_id_offset into the UI.
    - Exercise and lesson chapter IDs must be consistent.
    - Exercise page must come after (or equal to) the lesson chapter start page.
    """
    issues: List[str] = []
    offset = cfg.chapter_id_offset

    for lc in cfg.lesson_chapters:
        display_num = lc.chapter_id - offset
        # Only flag when there IS an offset and the title embeds the raw DB id
        # (when offset=0, chapter_id == display_num so the title is correct)
        if offset != 0 and display_num != lc.chapter_id:
            ch_id_str = str(lc.chapter_id)
            if re.search(rf'\b[Cc]hapitre\s+{re.escape(ch_id_str)}\b', lc.title):
                issues.append(
                    f'[chapter {lc.chapter_id}] Title contains raw DB id "{ch_id_str}" '
                    f'— use the display number "{display_num}" instead. '
                    f'Current: "{lc.title}"'
                )
        # Start page must be positive
        if lc.page < 1:
            issues.append(f'[chapter {lc.chapter_id}] Invalid start page: {lc.page}')

    # Exercise chapter IDs must all appear in lesson_chapters (or at least be sane)
    lesson_ids = {lc.chapter_id for lc in cfg.lesson_chapters}
    for block in cfg.exercise_chapters:
        if lesson_ids and block.chapter_id not in lesson_ids:
            issues.append(
                f'[exercise chapter {block.chapter_id}] No matching lesson chapter — '
                f'add a LessonChapter entry or check the chapter_id'
            )
        if block.ex_page < 1 or block.sol_page < 1:
            issues.append(
                f'[exercise chapter {block.chapter_id}] Invalid page numbers '
                f'(ex_page={block.ex_page}, sol_page={block.sol_page})'
            )
        if block.sol_page < block.ex_page:
            issues.append(
                f'[exercise chapter {block.chapter_id}] sol_page ({block.sol_page}) '
                f'is before ex_page ({block.ex_page})'
            )

    return issues


def print_config_report(cfg: 'BookConfig') -> bool:
    """Print config validation report.  Returns True if no issues."""
    issues = validate_config(cfg)
    print(f'\n{"─"*60}')
    print(f'CONFIG VALIDATION  ({cfg.book_id})')
    print(f'{"─"*60}')
    if issues:
        for issue in issues:
            print(f'  ✗ {issue}')
    else:
        print('  ✓ Config looks good')
    print(f'{"─"*60}\n')
    return len(issues) == 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_fen(fen: str) -> Tuple[bool, str]:
    m = re.match(r'^([WB]):W([\d,]*):B([\d,]*)$', fen)
    if not m:
        return False, 'format mismatch'
    def parse(s: str):
        return [int(x) for x in s.split(',') if x]
    white = parse(m.group(2))
    black = parse(m.group(3))
    all_sq = white + black
    for sq in all_sq:
        if not 1 <= sq <= 50:
            return False, f'square {sq} out of range'
    if len(all_sq) != len(set(all_sq)):
        return False, 'duplicate squares'
    if not white:
        return False, 'no white pieces'
    if not black:
        return False, 'no black pieces'
    return True, 'ok'


def _first_move_source(mv: str) -> int | None:
    """Return the source square of a move string, or None if unparseable."""
    try:
        if '-' in mv and 'x' not in mv:
            return int(mv.split('-')[0])
        if 'x' in mv and '-' not in mv:
            return int(mv.split('x')[0])
    except (ValueError, IndexError):
        pass
    return None


def _is_valid_move(mv: str) -> bool:
    if '-' in mv and 'x' not in mv:
        parts = mv.split('-')
        if len(parts) != 2:
            return False
        try:
            a, b = int(parts[0]), int(parts[1])
            return 1 <= a <= 50 and 1 <= b <= 50 and a != b
        except ValueError:
            return False
    if 'x' in mv and '-' not in mv:
        parts = mv.split('x')
        try:
            nums = [int(p) for p in parts if p]
            return all(1 <= n <= 50 for n in nums) and len(nums) >= 2
        except ValueError:
            return False
    return False
