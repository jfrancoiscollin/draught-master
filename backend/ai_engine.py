from __future__ import annotations
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
    WHITE_KING: 250,
    BLACK_MAN: -100,
    BLACK_KING: -250,
}


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
            advancement = (9 - row) / 9.0 * 20
            score += advancement
            if sq in CENTER_SQUARES:
                score += 15
            elif sq in NEAR_CENTER:
                score += 7
            if sq in WHITE_BACK_ROW:
                score += 10

        elif piece == WHITE_KING:
            white_pieces += 1
            if sq in CENTER_SQUARES:
                score += 15
            elif sq in NEAR_CENTER:
                score += 7

        elif piece == BLACK_MAN:
            black_pieces += 1
            row = _sq_row(sq)
            advancement = row / 9.0 * 20
            score -= advancement
            if sq in CENTER_SQUARES:
                score -= 15
            elif sq in NEAR_CENTER:
                score -= 7
            if sq in BLACK_BACK_ROW:
                score -= 10

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


def minimax(
    state: GameState,
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool,
) -> float:
    result = game_result(state)
    if result is not None:
        if result == 'white':
            return 100000.0 + depth
        if result == 'black':
            return -100000.0 - depth
        return 0.0

    if depth == 0:
        return evaluate(state)

    moves = get_legal_moves(state)
    if not moves:
        return evaluate(state)

    if maximizing:
        best = float('-inf')
        for move in moves:
            new_state = apply_move(state, move)
            val = minimax(new_state, depth - 1, alpha, beta, False)
            best = max(best, val)
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        return best
    else:
        best = float('inf')
        for move in moves:
            new_state = apply_move(state, move)
            val = minimax(new_state, depth - 1, alpha, beta, True)
            best = min(best, val)
            beta = min(beta, val)
            if beta <= alpha:
                break
        return best


def get_best_move(state: GameState, depth: int = 6) -> Optional[Move]:
    moves = get_legal_moves(state)
    if not moves:
        return None

    best_move = None
    if state.turn == 'white':
        best_val = float('-inf')
        for move in moves:
            new_state = apply_move(state, move)
            val = minimax(new_state, depth - 1, float('-inf'), float('inf'), False)
            if val > best_val:
                best_val = val
                best_move = move
    else:
        best_val = float('inf')
        for move in moves:
            new_state = apply_move(state, move)
            val = minimax(new_state, depth - 1, float('-inf'), float('inf'), True)
            if val < best_val:
                best_val = val
                best_move = move

    return best_move
