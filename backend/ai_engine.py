from __future__ import annotations
import random
import time
from typing import Optional
from game_engine import (
    GameState, Move, get_legal_moves, apply_move, game_result,
    WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING, EMPTY,
)

CENTER_SQUARES = frozenset({23, 24, 27, 28})
NEAR_CENTER    = frozenset({18, 19, 22, 23, 24, 25, 27, 28, 29, 32, 33})
WHITE_BACK_ROW = frozenset({46, 47, 48, 49, 50})
BLACK_BACK_ROW = frozenset({1, 2, 3, 4, 5})

# Squares on the left/right edge: men here have halved mobility.
# col 0 (odd rows, col_in_row=0): 6,16,26,36,46
# col 9 (even rows, col_in_row=4): 5,15,25,35,45
EDGE_SQUARES = frozenset({5, 6, 15, 16, 25, 26, 35, 36, 45, 46})

MATERIAL = {
    WHITE_MAN:  100,
    WHITE_KING: 320,   # kings are very powerful in 10×10
    BLACK_MAN: -100,
    BLACK_KING: -320,
}

# Time budget per level. With TT + quiescence the effective depth is much higher.
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

_TT: dict[int, tuple[int, float, str]] = {}
_TT_MAX = 700_000


def _tt_clear() -> None:
    _TT.clear()


# ── Helpers ──────────────────────────────────────────────────────────────────

class _Timeout(Exception):
    pass


def _sq_row(sq: int) -> int:
    return (sq - 1) // 5


# ── Evaluation ───────────────────────────────────────────────────────────────

def evaluate(state: GameState) -> float:
    result = game_result(state)
    if result == 'white':
        return 100000.0
    if result == 'black':
        return -100000.0
    if result == 'draw':
        return 0.0

    score = 0.0
    white_men = white_kings = black_men = black_kings = 0

    for sq in range(1, 51):
        piece = state.board[sq]
        if piece == EMPTY:
            continue

        score += MATERIAL[piece]

        if piece == WHITE_MAN:
            white_men += 1
            row = _sq_row(sq)
            score += (9 - row) / 9.0 * 25   # advancement
            if sq in CENTER_SQUARES:
                score += 18
            elif sq in NEAR_CENTER:
                score += 8
            if sq in WHITE_BACK_ROW:
                score += 10  # anchor / back-rank guard
            if sq in EDGE_SQUARES:
                score -= 12  # edge men are less mobile

        elif piece == WHITE_KING:
            white_kings += 1
            if sq in CENTER_SQUARES:
                score += 20
            elif sq in NEAR_CENTER:
                score += 10
            if sq in EDGE_SQUARES:
                score -= 8

        elif piece == BLACK_MAN:
            black_men += 1
            row = _sq_row(sq)
            score -= row / 9.0 * 25
            if sq in CENTER_SQUARES:
                score -= 18
            elif sq in NEAR_CENTER:
                score -= 8
            if sq in BLACK_BACK_ROW:
                score -= 10
            if sq in EDGE_SQUARES:
                score += 12

        elif piece == BLACK_KING:
            black_kings += 1
            if sq in CENTER_SQUARES:
                score -= 20
            elif sq in NEAR_CENTER:
                score -= 10
            if sq in EDGE_SQUARES:
                score += 8

    total_w = white_men + white_kings
    total_b = black_men + black_kings

    if total_w > 0 and total_b == 0:
        return 100000.0
    if total_b > 0 and total_w == 0:
        return -100000.0

    # Endgame: kings become relatively more valuable and should centralise
    total = total_w + total_b
    if total <= 14 and (white_kings or black_kings):
        endgame_factor = (14 - total) / 14.0
        score += (white_kings - black_kings) * 40 * endgame_factor

    # Slight bonus for having the move (tempo)
    if state.turn == 'white':
        score += 5
    else:
        score -= 5

    return score


# ── Quiescence search ────────────────────────────────────────────────────────
# In draughts captures are MANDATORY, so depth-0 nodes with captures pending
# are not quiet. We must follow all forced capture chains before evaluating.

_MAX_QDEPTH = 14


def _quiescence(
    state: GameState,
    alpha: float,
    beta: float,
    maximizing: bool,
    deadline: float,
    qdepth: int,
) -> float:
    if time.monotonic() > deadline:
        raise _Timeout()

    moves = get_legal_moves(state)
    if not moves:
        return evaluate(state)

    captures = [m for m in moves if m.captures]
    if not captures or qdepth >= _MAX_QDEPTH:
        return evaluate(state)

    # Follow mandatory captures
    if maximizing:
        best = float('-inf')
        for move in captures:
            val = _quiescence(
                apply_move(state, move), alpha, beta, False, deadline, qdepth + 1
            )
            if val > best:
                best = val
            if val > alpha:
                alpha = val
            if beta <= alpha:
                break
        return best
    else:
        best = float('inf')
        for move in captures:
            val = _quiescence(
                apply_move(state, move), alpha, beta, True, deadline, qdepth + 1
            )
            if val < best:
                best = val
            if val < beta:
                beta = val
            if beta <= alpha:
                break
        return best


# ── Alpha-beta minimax with TT ───────────────────────────────────────────────

def _order_moves(moves: list[Move]) -> list[Move]:
    captures = [m for m in moves if m.captures]
    quiet    = [m for m in moves if not m.captures]
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

    # TT lookup
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
        # Use quiescence to resolve forced capture chains before evaluating
        return _quiescence(state, alpha, beta, maximizing, deadline, 0)

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

    # TT store
    if len(_TT) < _TT_MAX:
        if best <= alpha_orig:
            flag = 'upper'
        elif best >= beta:
            flag = 'lower'
        else:
            flag = 'exact'
        _TT[zhash] = (depth, best, flag)

    return best


# ── Public API ───────────────────────────────────────────────────────────────

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
