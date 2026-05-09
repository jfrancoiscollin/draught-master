"""
Unit tests for solution_parsing.py.

Covers every parsing bug encountered during extraction:
  1. D1 at start of text with no preceding newline
  2. Multi-line bracketed comments [...]
  3. Multi-step position notation A-B-C must NOT be a move
  4. Multi-jump captures AxBxC must be accepted
  5. Mixed separators (A-BxC) must be rejected
  6. Parenthesised opponent replies included in search scope
  7. Out-of-range and repeated-square captures rejected
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from solution_parsing import (
    _is_valid_move,
    _parse_moves,
    extract_moves,
    parse_solution_page,
)


# ── _is_valid_move ────────────────────────────────────────────────────────────

class TestIsValidMove:
    def test_simple_move(self):
        assert _is_valid_move('32-28')

    def test_simple_move_small_squares(self):
        assert _is_valid_move('1-6')

    def test_simple_move_large_squares(self):
        assert _is_valid_move('45-50')

    def test_single_capture(self):
        assert _is_valid_move('34x23')

    def test_multi_jump(self):
        assert _is_valid_move('34x23x12')

    def test_multi_jump_four_squares(self):
        assert _is_valid_move('9x18x27x36')

    # — invalid cases —

    def test_position_notation_rejected(self):
        # A-B-C is a position sequence, not a move
        assert not _is_valid_move('32-28-24')

    def test_mixed_separators_rejected(self):
        assert not _is_valid_move('32-23x14')

    def test_out_of_range_low(self):
        assert not _is_valid_move('0-5')

    def test_out_of_range_high(self):
        assert not _is_valid_move('5-51')

    def test_same_square_rejected(self):
        assert not _is_valid_move('10-10')

    def test_repeated_capture_square_rejected(self):
        assert not _is_valid_move('10x20x10')

    def test_no_separator(self):
        assert not _is_valid_move('32')

    def test_empty_string(self):
        assert not _is_valid_move('')


# ── _parse_moves ──────────────────────────────────────────────────────────────

class TestParseMoves:
    def test_extracts_simple_move(self):
        assert _parse_moves('34-29') == ['34-29']

    def test_extracts_multi_jump(self):
        assert _parse_moves('34x23x12') == ['34x23x12']

    def test_skips_position_notation(self):
        # 16-22-26 is a multi-step position, must be skipped
        assert _parse_moves('16-22-26') == []

    def test_extracts_sequence(self):
        moves = _parse_moves('34-29 (23x34) 39x30')
        assert '34-29' in moves
        assert '39x30' in moves

    def test_max_moves_respected(self):
        text = ' '.join(f'1-{i}' for i in range(2, 20))
        assert len(_parse_moves(text, max_moves=5)) == 5

    def test_position_notation_not_first_move(self):
        # 37-38-42-47 must be skipped even if it appears alongside valid moves
        moves = _parse_moves('34-29 37-38-42-47 23x34')
        assert '37-38-42-47' not in moves
        assert '34-29' in moves


# ── extract_moves ─────────────────────────────────────────────────────────────

class TestExtractMoves:
    def test_basic_solution_marker(self):
        text = 'Solution : 34-29 (23x34) 39x30.'
        moves = extract_moves(text)
        # parens are expanded: (23x34) → ' 23x34 ', so 23x34 is captured as a valid capture
        assert moves == ['34-29', '23x34', '39x30']

    def test_solution_marker_case_insensitive(self):
        text = 'solution : 32-28 19x30'
        moves = extract_moves(text)
        assert '32-28' in moves

    def test_solution_with_number(self):
        # "Solution 1 :" format
        text = 'Solution 1 : 34-29 39x30.'
        moves = extract_moves(text)
        assert '34-29' in moves
        assert '39x30' in moves

    def test_bracketed_comment_removed(self):
        # [plus fort que 34-30] should not contribute moves
        text = 'Solution : 34-29 [plus fort que 34-30] (23x34) 39x30.'
        moves = extract_moves(text)
        assert '34-30' not in moves
        assert '34-29' in moves
        assert '39x30' in moves

    def test_multiline_bracket_removed(self):
        # Brackets spanning multiple lines must be fully removed
        text = (
            'Solution : 34-29\n'
            '[ce coup est meilleur\n'
            'que 34-30 car 39x30] (23x34) 39x30.'
        )
        moves = extract_moves(text)
        assert '34-30' not in moves
        assert '34-29' in moves
        assert '39x30' in moves

    def test_parenthesised_reply_included(self):
        # Opponent reply (23x34) — the 23x34 capture should still be extractable
        text = 'Solution : 34-29 (23x34) 39x30.'
        moves = extract_moves(text)
        assert '23x34' in moves

    def test_no_marker_falls_back_to_first_lines(self):
        text = '34-29 (23x34) 39x30.'
        moves = extract_moves(text)
        assert '34-29' in moves

    def test_max_lines_limits_capture(self):
        # A long analysis block after the solution line must not bleed in
        lines = ['Solution : 34-29 39x30.'] + [f'{i}-{i+1}' for i in range(1, 40)]
        text = '\n'.join(lines)
        moves = extract_moves(text)
        # Only the first 3 lines are searched; line-by-line noise should be absent
        assert len(moves) <= 10


# ── parse_solution_page ───────────────────────────────────────────────────────

class TestParseSolutionPage:
    TYPICAL_PAGE = (
        'SOLUTIONS :\n'
        'D1 – Solution : 34-29 (23x34) 39x30.\n'
        'D2 – Solution : 32-28 19x30.\n'
        'D3 – Solution : 27x38 42x33.\n'
    )

    def test_parses_all_diagrams(self):
        result = parse_solution_page(self.TYPICAL_PAGE)
        assert set(result.keys()) == {1, 2, 3}

    def test_d1_parsed_without_preceding_newline(self):
        # D1 immediately follows SOLUTIONS header with no blank line — regression test
        text = 'SOLUTIONS :\nD1 – Solution : 34-29 (23x34) 39x30.\nD2 – Solution : 32-28.'
        result = parse_solution_page(text)
        assert 1 in result
        assert result[1] != []

    def test_solutions_header_stripped(self):
        result = parse_solution_page(self.TYPICAL_PAGE)
        # No spurious diagram 0 from the header
        assert 0 not in result

    def test_moves_extracted_per_diagram(self):
        result = parse_solution_page(self.TYPICAL_PAGE)
        assert '34-29' in result[1]
        assert '32-28' in result[2]
        assert '27x38' in result[3]

    def test_multi_page_solutions(self):
        page1 = 'SOLUTIONS :\nD1 – Solution : 34-29 (23x34) 39x30.\n'
        page2 = 'D2 – Solution : 32-28 19x30.\n'
        result = parse_solution_page(page1 + page2)
        assert 1 in result and 2 in result

    def test_custom_split_pattern(self):
        # Some books use plain "D1:" without dash
        text = 'SOLUTIONS\nD1: Solution : 34-29.\nD2: Solution : 32-28.'
        result = parse_solution_page(text, split_pattern=r'\nD(\d+):\s*')
        assert 1 in result and 2 in result

    def test_unicode_dash_accepted(self):
        # En-dash (–) used in many French PDFs
        text = 'SOLUTIONS :\nD1 – Solution : 34-29.\n'
        result = parse_solution_page(text)
        assert 1 in result

    def test_bracketed_description_not_in_moves(self):
        text = (
            'SOLUTIONS :\n'
            'D1 – Le thème. Solution : 34-29 [plus fort que 34-30] (23x34) 39x30.\n'
        )
        result = parse_solution_page(text)
        assert '34-30' not in result[1]
        assert '34-29' in result[1]


# ── New robustness tests (issues discovered during real extraction) ───────────

class TestExtractMovesRobustness:
    def test_attribution_line_with_date_skipped(self):
        # "27-12" in a date "27-12-1975" must not be treated as move 27-12.
        text = (
            'Agafonow - Baba Sy (Suiker GMA, 27-12-1975)\n'
            '32-27 21x32 43-38 32x34\n'
        )
        moves = extract_moves(text)
        assert moves[0] == '32-27', 'first move must be 32-27, not the date fragment 27-12'
        assert '27-12' not in moves

    def test_standalone_annotation_line_skipped(self):
        # "5-10 ?!" on its own line is a questionable-move annotation, not a solution.
        text = (
            '5-10 ?!\n\n'
            'Les blancs dament par 27-22 (18x27) 38-33 (27x29) 34x5\n'
        )
        moves = extract_moves(text)
        assert moves[0] == '27-22', 'annotation line must be skipped; real solution starts with 27-22'
        assert '5-10' not in moves

    def test_jouant_marker_used_as_solution_start(self):
        # "jouant :" is used in French books as an informal solution marker.
        text = (
            'Le dernier coup des Noirs (23-28) est fautif.\n'
            'Les Blancs gagnent en jouant : 33-29.\n'
        )
        moves = extract_moves(text)
        assert moves[0] == '33-29', '"jouant :" must act as a solution marker'
        assert '23-28' not in moves

    def test_numbered_game_notation_normalised(self):
        # "38.32-27" (game-move notation) must yield move 32-27, not fail.
        text = '38.32-27 21x32 39.43-38 32x34\n'
        moves = extract_moves(text)
        assert '32-27' in moves
        assert '43-38' in moves

    def test_fallback_skips_single_move_context_lines(self):
        # When there's no Solution marker, single-move context lines (10-14,
        # 12x21) must be skipped; the first paragraph with 2+ moves is the solution.
        text = (
            '10-14\n\n'
            '12x21\n\n'
            '33-29 (10-14) 29-24 (20-25) 27-22\n'
        )
        moves = extract_moves(text)
        assert moves[0] == '33-29', 'single-move context paragraphs must be skipped'
