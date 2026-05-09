"""
Full exercise extraction pipeline: combines board detection, FEN analysis, and solution parsing.

For each ChapterExerciseBlock in the config:
  1. Render the exercise page to a grayscale image
  2. Detect all boards
  3. For each board, extract FEN
  4. Parse solutions from the solution page
  5. Combine into exercise dicts
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List

from config import BookConfig, ChapterExerciseBlock
from pdf_utils import extract_text_pages, render_page_gray
from board_detection import find_boards
from fen_extraction import analyze_board_fen
from solution_parsing import parse_solution_page, get_turn_from_page

log = logging.getLogger(__name__)


def extract_all_exercises(
    cfg: BookConfig,
    cwd: str = '.',
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    Extract all exercises for all chapters in cfg.exercise_chapters.

    Returns a list of exercise dicts ready to be written to a Python file.
    Each dict has keys: name, description, initial_fen, solution_moves,
                        difficulty, category, hint.
    """
    log.info('Extracting full PDF text…')
    pages = extract_text_pages(cfg.pdf_path, cwd=cwd)

    all_exercises: List[Dict[str, Any]] = []

    for block in cfg.exercise_chapters:
        if verbose:
            print(f'\n── Chapter {block.chapter_id}: {block.short_title} ──')

        exercises = _extract_chapter(cfg, block, pages, cwd=cwd, verbose=verbose)
        all_exercises.extend(exercises)
        log.info('  Chapter %d: %d exercises extracted', block.chapter_id, len(exercises))

    return all_exercises


def _extract_chapter(
    cfg: BookConfig,
    block: ChapterExerciseBlock,
    pages: List[str],
    cwd: str,
    verbose: bool,
) -> List[Dict[str, Any]]:
    """Extract exercises for a single chapter block."""
    ex_text = pages[block.ex_page - 1]

    # Collect solution text (may span multiple pages)
    sol_end = block.sol_page_end if block.sol_page_end else block.sol_page
    sol_text = '\n'.join(pages[p - 1] for p in range(block.sol_page, sol_end + 1))

    # Parse solutions
    solutions = parse_solution_page(sol_text, split_pattern=cfg.solution_split_pattern)
    if verbose:
        print(f'  Solutions found: {sorted(solutions.keys())}')

    # Render exercise page and detect boards
    gray = render_page_gray(cfg.pdf_path, block.ex_page, cwd=cwd)
    boards = find_boards(
        gray,
        style=cfg.board_style,
        min_border_run=cfg.min_border_run,
        expected_board_px=cfg.expected_board_px,
    )
    if verbose:
        print(f'  Boards detected: {len(boards)}')

    if block.d_count and len(boards) != block.d_count:
        log.warning(
            'Chapter %d: expected %d boards, got %d',
            block.chapter_id, block.d_count, len(boards),
        )

    exercises: List[Dict[str, Any]] = []
    for i, (x1, y1, x2, y2) in enumerate(boards):
        d_num = i + 1
        turn = get_turn_from_page(ex_text, d_num)
        fen = analyze_board_fen(
            gray, x1, y1, x2, y2, to_move=turn,
            sample_radius=cfg.sample_radius,
            white_threshold=cfg.white_piece_threshold,
            black_threshold=cfg.black_piece_threshold,
        )
        sol_moves = solutions.get(d_num, [])
        if not sol_moves:
            log.warning('Chapter %d D%d: no solution found', block.chapter_id, d_num)

        side = 'blancs' if turn == 'W' else 'noirs'
        exercises.append({
            'name': f'{block.short_title} – D{d_num}',
            'description': (
                f'Chapitre {block.chapter_id} – {block.short_title}. '
                f'Les {side} jouent et gagnent.'
            ),
            'initial_fen': fen,
            'solution_moves': sol_moves,
            'difficulty': cfg.get_difficulty(block.chapter_id),
            'category': f'sdj_ch{block.chapter_id}',
            'hint': '',
        })

    return exercises
