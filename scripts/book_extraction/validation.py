"""
Validation of extracted exercises and lessons.

Run this after extraction to catch problems before writing to the backend.
Prints a structured report and returns a list of issues.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple


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


# ── Lesson validation ─────────────────────────────────────────────────────────

def validate_lessons(lessons: Dict[str, Dict[str, Any]]) -> List[str]:
    """Validate extracted lessons.  Returns a list of issue strings."""
    issues: List[str] = []
    for ch_id, lesson in lessons.items():
        prefix = f'[chapter {ch_id}]'
        if not lesson.get('title'):
            issues.append(f'{prefix} Missing title')
        if not lesson.get('text', '').strip():
            issues.append(f'{prefix} Empty text (lesson text not extracted)')
        if not lesson.get('category'):
            issues.append(f'{prefix} Missing category')
    return issues


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
