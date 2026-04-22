from __future__ import annotations
import random
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

# Time budget per level (seconds). With transposition table, shorter times = same strength.
TIME_LIMITS = {1: 0.05, 2: 0.15, 3: 0.35, 4: 0.6, 5: 1.0, 6: 1.5, 7: 2.5, 8: 4.0}

# ── Zobrist hashing ──────────────────────────────────────────────────────────

_rng = random.Random(0xDEADBEEF_CAFEBABE)
_PIECES = [WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING]
_ZOBRIST: dict[tuple[int, int], int] = {
    (piece, sq): _rng.getrandbits(64)
    for piece in _PIECES
    for sq in range(1, 51)
}
_ZOBRIST_BLACK_TURN = _rng.getrandbits(64)


def _hash_state(state: GameState) -> int:
    h = 0
    for sq in range(1, 51):
        piece = state.board[sq]
        if piece != EMPTY:
            h ^= _ZOBRIST[(piece, sq)]
    if state.turn == 'black':
        h ^= _ZOBRIST_BLACK_TURN
    return h


# ── Transposition table ──────────────────────────────────────────────────────
# Entry: (depth, score, flag)  flag ∈ {'exact', 'lower', 'upper'}

_TT: dict[int, tuple[int, float, str]] = {}
_TT_MAX = 600_000


def _tt_clear() -> None:
    _TT.clear()


# ── Misc helpers ─────────────────────────────────────────────────────────────

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
            score += (9 - row) / 9.0 * 20
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
    zhash: int,
) -> float:
    if time.monotonic() > deadline:
        raise _Timeout()

    alpha_orig = alpha

    # Transposition table lookup
    tt_entry = _TT.get(zhash)
    if tt_entry is not None:
        tt_depth, tt_score, tt_flag = tt_entry
        if tt_depth >= depth:
            if tt_flag == 'exact':
                return tt_score
            if tt_flag == 'lower':
                alpha = max(alpha, tt_score)
            elif tt_flag == 'upper':
                beta = min(beta, tt_score)
            if beta <= alpha:
                return tt_score

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
            child = apply_move(state, move)
            child_hash = _hash_state(child)
            val = _minimax(child, depth - 1, alpha, beta, False, deadline, child_hash)
            if val > best:
                best = val
            if val > alpha:
                alpha = val
            if beta <= alpha:
                break
    else:
        best = float('inf')
        for move in moves:
            child = apply_move(state, move)
            child_hash = _hash_state(child)
            val = _minimax(child, depth - 1, alpha, beta, True, deadline, child_hash)
            if val < best:
                best = val
            if val < beta:
                beta = val
            if beta <= alpha:
                break

    # Store in TT
    if len(_TT) < _TT_MAX:
        if best <= alpha_orig:
            flag = 'upper'
        elif best >= beta:
            flag = 'lower'
        else:
            flag = 'exact'
        _TT[zhash] = (depth, best, flag)

    return best


def get_best_move(state: GameState, depth: int = 6) -> Optional[Move]:
    moves = get_legal_moves(state)
    if not moves:
        return None
    if len(moves) == 1:
        return moves[0]

    _tt_clear()

    time_limit = TIME_LIMITS.get(depth, 5.0)
    deadline = time.monotonic() + time_limit
    maximizing = (state.turn == 'white')

    ordered = _order_moves(moves)
    best_move = ordered[0]

    for d in range(1, depth + 1):
        if time.monotonic() >= deadline:
            break

        iteration_best: Optional[Move] = None
        iteration_best_val = float('-inf') if maximizing else float('inf')

        try:
            for move in ordered:
                child = apply_move(state, move)
                child_hash = _hash_state(child)
                val = _minimax(
                    child,
                    d - 1,
                    float('-inf'),
                    float('inf'),
                    not maximizing,
                    deadline,
                    child_hash,
                )
                if maximizing and val > iteration_best_val:
                    iteration_best_val = val
                    iteration_best = move
                elif not maximizing and val < iteration_best_val:
                    iteration_best_val = val
                    iteration_best = move

            if iteration_best is not None:
                best_move = iteration_best
                ordered = [best_move] + [m for m in ordered if m is not best_move]

        except _Timeout:
            break

    return best_move
