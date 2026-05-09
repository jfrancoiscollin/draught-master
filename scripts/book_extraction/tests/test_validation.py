"""
Unit tests for validation.py.

Covers exercise validation (FEN, solution, duplicates) and lesson validation
(empty text, suspiciously short content for real chapters).
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from validation import (
    validate_exercises,
    validate_lessons,
    _validate_fen,
    _is_valid_move,
)


# ── _validate_fen ─────────────────────────────────────────────────────────────

class TestValidateFen:
    def test_valid_fen(self):
        ok, _ = _validate_fen('W:W32,28,27:B18,13,9')
        assert ok

    def test_black_to_move(self):
        ok, _ = _validate_fen('B:W32,28:B18,13')
        assert ok

    def test_wrong_format(self):
        ok, _ = _validate_fen('notafen')
        assert not ok

    def test_square_out_of_range(self):
        ok, _ = _validate_fen('W:W51,28:B18,13')
        assert not ok

    def test_square_zero(self):
        ok, _ = _validate_fen('W:W0,28:B18,13')
        assert not ok

    def test_duplicate_squares(self):
        ok, reason = _validate_fen('W:W28,28:B18,13')
        assert not ok

    def test_no_white_pieces(self):
        ok, _ = _validate_fen('W:W:B18,13')
        assert not ok

    def test_no_black_pieces(self):
        ok, _ = _validate_fen('W:W28,32:B')
        assert not ok


# ── validate_exercises ────────────────────────────────────────────────────────

def _ex(name='Ch1 – D1', fen='W:W32,28:B18,13', moves=None):
    return {
        'name': name,
        'description': 'desc',
        'initial_fen': fen,
        'solution_moves': moves if moves is not None else ['32-28'],
        'difficulty': 2,
        'category': 'cat',
    }


class TestValidateExercises:
    def test_valid_exercise_no_issues(self):
        assert validate_exercises([_ex()]) == []

    def test_empty_solution_flagged(self):
        issues = validate_exercises([_ex(moves=[])])
        assert any('EMPTY solution' in i for i in issues)

    def test_duplicate_fen_flagged(self):
        fen = 'W:W32,28:B18,13'
        issues = validate_exercises([_ex('D1', fen), _ex('D2', fen)])
        assert any('Duplicate FEN' in i for i in issues)

    def test_invalid_fen_flagged(self):
        issues = validate_exercises([_ex(fen='BADFEN')])
        assert any('Invalid FEN' in i for i in issues)

    def test_suspicious_move_flagged(self):
        issues = validate_exercises([_ex(moves=['32-28-24'])])
        assert any('Suspicious move' in i for i in issues)

    def test_missing_field_flagged(self):
        ex = _ex()
        del ex['category']
        issues = validate_exercises([ex])
        assert any('Missing field' in i for i in issues)

    def test_multiple_exercises_checked_independently(self):
        exercises = [
            _ex('D1', fen='W:W32,28:B18,13'),
            _ex('D2', fen='W:W33,27:B19,14', moves=[]),  # unique FEN, empty solution
            _ex('D3', fen='W:W34,26:B20,15'),
        ]
        issues = validate_exercises(exercises)
        # Only D2 should raise an issue (empty solution)
        assert len(issues) == 1
        assert 'D2' in issues[0]


# ── _is_valid_move (validation.py copy) ──────────────────────────────────────

class TestValidationIsValidMove:
    def test_valid_quiet_move(self):
        assert _is_valid_move('32-28')

    def test_valid_capture(self):
        assert _is_valid_move('34x23')

    def test_position_notation_rejected(self):
        assert not _is_valid_move('32-28-24')

    def test_mixed_rejected(self):
        assert not _is_valid_move('32-23x14')


# ── validate_lessons ──────────────────────────────────────────────────────────

def _lesson(ch_id, title, text, category='cat'):
    return {str(ch_id): {'title': title, 'text': text, 'category': category}}


class TestValidateLessons:
    def test_good_lesson_no_issues(self):
        lessons = {
            '1': {'title': 'Ch 1', 'text': 'x' * 500, 'category': 'cat'},
        }
        issues = validate_lessons(lessons)
        assert issues == []

    def test_empty_text_flagged(self):
        lessons = {'1': {'title': 'Ch 1', 'text': '', 'category': 'cat'}}
        issues = validate_lessons(lessons)
        assert any('Empty text' in i for i in issues)

    def test_missing_title_flagged(self):
        lessons = {'1': {'title': '', 'text': 'content', 'category': 'cat'}}
        issues = validate_lessons(lessons)
        assert any('Missing title' in i for i in issues)

    def test_missing_category_flagged(self):
        lessons = {'1': {'title': 'Ch 1', 'text': 'content', 'category': ''}}
        issues = validate_lessons(lessons)
        assert any('Missing category' in i for i in issues)

    def test_short_text_real_chapter_flagged(self):
        # A real chapter (no "en création") with suspiciously little text
        lessons = {'5': {'title': 'Chapitre 5 : les temps d\'avance', 'text': 'x' * 50, 'category': 'cat'}}
        issues = validate_lessons(lessons)
        assert any('short' in i.lower() or 'page' in i.lower() for i in issues)

    def test_short_text_creation_chapter_not_flagged(self):
        # "en création" chapters are expected to have minimal text
        lessons = {'18': {'title': 'Chapitre 18 : le pion de bande 16 (en création)', 'text': 'x' * 50, 'category': 'cat'}}
        issues = validate_lessons(lessons)
        # Should NOT flag short text for "en création" chapters
        assert not any('short' in i.lower() or 'page' in i.lower() for i in issues)

    def test_placeholder_text_flagged(self):
        placeholder = '*(Contenu de la leçon à venir)*'
        lessons = {'2': {'title': 'Ch 2', 'text': placeholder, 'category': 'cat'}}
        issues = validate_lessons(lessons)
        assert issues  # something should be flagged
