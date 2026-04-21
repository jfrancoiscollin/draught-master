from __future__ import annotations
import time
from typing import Optional
from game_engine import (
    GameState, Move, get_legal_moves, apply_move, game_result,
    WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING, EMPTY,
)

CENTER_SQUARES = {23, 24, 27, 28}
NEAR_CENTER = {18, 19, 22, 23, 24, 25, 27, 28, 29, 32, 33}
WHITE_BACK_ROW = {46, 47, 48, 49, 50}
BLACK_BACK_ROW = {1, 2, 3, 4, 5}

MATERIAL = {
    WHITE_MAN: 100,
    WHITE_KING: 280,
    BLACK_MAN: -100,
    BLACK_KING: -280,
}

# Time budget per level (seconds). Iterative deepening uses this as a hard cap.
TIME_LIMITS = {1: 0.3, 2: 0.6, 3: 1.2, 4: 2.0, 5: 3.5, 6: 5.5, 7: 8.0, 8: 10.0}


class _Timeout(Exception):
    pass


def _sq_row(sq: int) -> int:
    return (sq - 1) // 5


def evaluate(state: GameState) -> float:
    result = game_result(state)
    if result == 'white':
        return 100000.0
    if result == 'black':
        return -100000.0
    if result == 'draw':
        return 0.0

    score = 0.0
    white_pieces = 0
    black_pieces = 0

    for sq in range(1, 51):
        piece = state.board[sq]
        if piece == EMPTY:
            continue
        score += MATERIAL.get(piece, 0)

        if piece == WHITE_MAN:
            white_pieces += 1
            row = _sq_row(sq)
            score += (9 - row) / 9.0 * 20  # advancement bonus
            if sq in CENTER_SQUARES:
                score += 15
            elif sq in NEAR_CENTER:
                score += 7
            if sq in WHITE_BACK_ROW:
                score += 8

        elif piece == WHITE_KING:
            white_pieces += 1
            if sq in CENTER_SQUARES:
                score += 15
            elif sq in NEAR_CENTER:
                score += 7

        elif piece == BLACK_MAN:
            black_pieces += 1
            row = _sq_row(sq)
            score -= row / 9.0 * 20
            if sq in CENTER_SQUARES:
                score -= 15
            elif sq in NEAR_CENTER:
                score -= 7
            if sq in BLACK_BACK_ROW:
                score -= 8

        elif piece == BLACK_KING:
            black_pieces += 1
            if sq in CENTER_SQUARES:
                score -= 15
            elif sq in NEAR_CENTER:
                score -= 7

    if white_pieces > 0 and black_pieces == 0:
        return 100000.0
    if black_pieces > 0 and white_pieces == 0:
        return -100000.0

    return score


def _order_moves(moves: list[Move]) -> list[Move]:
    """Captures first — dramatically improves alpha-beta pruning."""
    captures = [m for m in moves if m.captures]
    quiet = [m for m in moves if not m.captures]
    return captures + quiet


def _minimax(
    state: GameState,
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool,
    deadline: float,
) -> float:
    if time.monotonic() > deadline:
        raise _Timeout()

    result = game_result(state)
    if result is not None:
        if result == 'white':
            return 100000.0 + depth
        if result == 'black':
            return -100000.0 - depth
        return 0.0

    if depth == 0:
        return evaluate(state)

    moves = _order_moves(get_legal_moves(state))
    if not moves:
        return evaluate(state)

    if maximizing:
        best = float('-inf')
        for move in moves:
            val = _minimax(apply_move(state, move), depth - 1, alpha, beta, False, deadline)
            if val > best:
                best = val
            if val > alpha:
                alpha = val
            if beta <= alpha:
                break
        return best
    else:
        best = float('inf')
        for move in moves:
            val = _minimax(apply_move(state, move), depth - 1, alpha, beta, True, deadline)
            if val < best:
                best = val
            if val < beta:
                beta = val
            if beta <= alpha:
                break
        return best


def get_best_move(state: GameState, depth: int = 6) -> Optional[Move]:
    moves = get_legal_moves(state)
    if not moves:
        return None
    if len(moves) == 1:
        return moves[0]

    time_limit = TIME_LIMITS.get(depth, 5.0)
    deadline = time.monotonic() + time_limit
    maximizing = (state.turn == 'white')

    # Start with the first capture available, or first move — safe fallback
    ordered = _order_moves(moves)
    best_move = ordered[0]

    # Iterative deepening: search d=1,2,3,... until time runs out
    for d in range(1, depth + 1):
        if time.monotonic() >= deadline:
            break

        iteration_best: Optional[Move] = None
        iteration_best_val = float('-inf') if maximizing else float('inf')

        try:
            for move in ordered:
                val = _minimax(
                    apply_move(state, move),
                    d - 1,
                    float('-inf'),
                    float('inf'),
                    not maximizing,
                    deadline,
                )
                if maximizing and val > iteration_best_val:
                    iteration_best_val = val
                    iteration_best = move
                elif not maximizing and val < iteration_best_val:
                    iteration_best_val = val
                    iteration_best = move

            # Full iteration completed — update best move and re-order (best-first)
            if iteration_best is not None:
                best_move = iteration_best
                ordered = [best_move] + [m for m in ordered if m is not best_move]

        except _Timeout:
            # Time ran out mid-search — keep result from last completed iteration
            break

    return best_move
