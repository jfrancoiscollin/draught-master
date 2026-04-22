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
# Men on edge columns have halved mobility (col 0: 6,16,26,36,46 / col 9: 5,15,25,35,45)
EDGE_SQUARES   = frozenset({5, 6, 15, 16, 25, 26, 35, 36, 45, 46})
# One row from promotion
WHITE_PROMO_ROW = frozenset({6, 7, 8, 9, 10})   # row 1 → promote to row 0
BLACK_PROMO_ROW = frozenset({41, 42, 43, 44, 45}) # row 8 → promote to row 9

MATERIAL = {
    WHITE_MAN:  100,
    WHITE_KING: 325,
    BLACK_MAN: -100,
    BLACK_KING: -325,
}

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
# Entry: (depth, score, flag, best_move_path)
# best_move_path: tuple(move.path) of the best move found at this node, or None.
# Storing the best move allows ordering at internal nodes (hash-move ordering),
# the single most effective alpha-beta improvement after captures-first.

_TT: dict[int, tuple[int, float, str, Optional[tuple[int, ...]]]] = {}
_TT_MAX = 800_000


def _tt_clear() -> None:
    _TT.clear()


# ── Killer moves ─────────────────────────────────────────────────────────────
# Two killer slots per depth: quiet moves that caused a beta cutoff.
# Tried after TT move and captures, before the rest of quiet moves.

_MAX_DEPTH = 60
_killers: list[list[Optional[tuple[int, ...]]]] = [[None, None] for _ in range(_MAX_DEPTH)]


def _killers_clear() -> None:
    for slot in _killers:
        slot[0] = slot[1] = None


def _store_killer(depth: int, path: tuple[int, ...]) -> None:
    if depth < _MAX_DEPTH and _killers[depth][0] != path:
        _killers[depth][1] = _killers[depth][0]
        _killers[depth][0] = path


# ── Helpers ──────────────────────────────────────────────────────────────────

class _Timeout(Exception):
    pass


def _sq_row(sq: int) -> int:
    return (sq - 1) // 5


# ── Move ordering ─────────────────────────────────────────────────────────────

def _order_moves(
    moves: list[Move],
    tt_path: Optional[tuple[int, ...]],
    depth: int,
) -> list[Move]:
    """TT move → captures → killers → rest."""
    tt: list[Move] = []
    captures: list[Move] = []
    killers: list[Move] = []
    rest: list[Move] = []

    k1 = _killers[depth][0] if depth < _MAX_DEPTH else None
    k2 = _killers[depth][1] if depth < _MAX_DEPTH else None

    for m in moves:
        mp = tuple(m.path)
        if tt_path and mp == tt_path:
            tt.append(m)
        elif m.captures:
            captures.append(m)
        elif mp == k1 or mp == k2:
            killers.append(m)
        else:
            rest.append(m)

    return tt + captures + killers + rest


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
            score += (9 - row) / 9.0 * 25      # advancement
            if sq in CENTER_SQUARES:
                score += 18
            elif sq in NEAR_CENTER:
                score += 8
            if sq in WHITE_BACK_ROW:
                score += 10                      # anchor prevents easy opponent promotion
            if sq in EDGE_SQUARES:
                score -= 12
            if sq in WHITE_PROMO_ROW:
                score += 20                      # one step from becoming a king

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
            if sq in BLACK_PROMO_ROW:
                score -= 20

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

    # Endgame: kings centralise and grow in value relative to men
    total = total_w + total_b
    if total <= 14 and (white_kings or black_kings):
        ef = (14 - total) / 14.0
        score += (white_kings - black_kings) * 45 * ef

    # Side-to-move tempo
    score += 5 if state.turn == 'white' else -5

    return score


# ── Quiescence search ─────────────────────────────────────────────────────────
# In draughts captures are mandatory — a depth-0 node with pending captures
# is not quiet.  Follow all forced capture chains before calling evaluate().

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


# ── Alpha-beta minimax with TT + killers ─────────────────────────────────────

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

    # TT lookup — also extracts best move for ordering even when depth is insufficient
    tt_path: Optional[tuple[int, ...]] = None
    tt_entry = _TT.get(zhash)
    if tt_entry is not None:
        tt_depth, tt_score, tt_flag, tt_path = tt_entry
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
        return _quiescence(state, alpha, beta, maximizing, deadline, 0)

    raw_moves = get_legal_moves(state)
    if not raw_moves:
        return evaluate(state)

    moves = _order_moves(raw_moves, tt_path, depth)

    best_path: Optional[tuple[int, ...]] = None

    if maximizing:
        best = float('-inf')
        for move in moves:
            child = apply_move(state, move)
            child_hash = _hash_state(child)
            val = _minimax(child, depth - 1, alpha, beta, False, deadline, child_hash)
            if val > best:
                best = val
                best_path = tuple(move.path)
            if val > alpha:
                alpha = val
            if beta <= alpha:
                if not move.captures:
                    _store_killer(depth, tuple(move.path))
                break
    else:
        best = float('inf')
        for move in moves:
            child = apply_move(state, move)
            child_hash = _hash_state(child)
            val = _minimax(child, depth - 1, alpha, beta, True, deadline, child_hash)
            if val < best:
                best = val
                best_path = tuple(move.path)
            if val < beta:
                beta = val
            if beta <= alpha:
                if not move.captures:
                    _store_killer(depth, tuple(move.path))
                break

    # TT store — include best move for future ordering
    if len(_TT) < _TT_MAX:
        if best <= alpha_orig:
            flag = 'upper'
        elif best >= beta:
            flag = 'lower'
        else:
            flag = 'exact'
        _TT[zhash] = (depth, best, flag, best_path)

    return best


# ── Public API ────────────────────────────────────────────────────────────────

def get_best_move(state: GameState, depth: int = 6) -> Optional[Move]:
    moves = get_legal_moves(state)
    if not moves:
        return None
    if len(moves) == 1:
        return moves[0]

    _tt_clear()
    _killers_clear()

    time_limit = TIME_LIMITS.get(depth, 5.0)
    deadline = time.monotonic() + time_limit
    maximizing = (state.turn == 'white')

    # Captures first at root too
    ordered = sorted(moves, key=lambda m: (0 if m.captures else 1))
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
