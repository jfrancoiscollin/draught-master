from __future__ import annotations
import random
import time
from typing import Optional
from game_engine import (
    GameState, Move, get_legal_moves, apply_move, game_result,
    WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING, EMPTY,
)

# ── Material & time limits ────────────────────────────────────────────────────

CENTER_SQUARES  = frozenset({23, 24, 27, 28})
NEAR_CENTER     = frozenset({18, 19, 22, 23, 24, 25, 27, 28, 29, 32, 33})
WHITE_BACK_ROW  = frozenset({46, 47, 48, 49, 50})
BLACK_BACK_ROW  = frozenset({1, 2, 3, 4, 5})
EDGE_SQUARES    = frozenset({5, 6, 15, 16, 25, 26, 35, 36, 45, 46})
WHITE_PROMO_ROW = frozenset({6, 7, 8, 9, 10})
BLACK_PROMO_ROW = frozenset({41, 42, 43, 44, 45})

MATERIAL = {WHITE_MAN: 100, WHITE_KING: 325, BLACK_MAN: -100, BLACK_KING: -325}

TIME_LIMITS = {1: 0.05, 2: 0.15, 3: 0.35, 4: 0.6, 5: 1.0, 6: 1.5, 7: 2.5, 8: 4.0}

# ── Board geometry (precomputed at import time) ───────────────────────────────

def _sq_row(sq: int) -> int:
    return (sq - 1) // 5

def _sq_col(sq: int) -> int:
    idx = sq - 1
    row = idx // 5
    return (idx % 5) * 2 + (1 if row % 2 == 0 else 0)

def _rc_to_sq(row: int, col: int) -> Optional[int]:
    if row < 0 or row > 9 or col < 0 or col > 9:
        return None
    if (row + col) % 2 == 0:
        return None
    return row * 5 + (col // 2) + 1

def _diag_neighbors(sq: int, row_offsets: list[int]) -> list[int]:
    r, c = _sq_row(sq), _sq_col(sq)
    return [n for dr in row_offsets for dc in (-1, 1)
            for n in (_rc_to_sq(r + dr, c + dc),) if n is not None]

# White advances toward row 0, black toward row 9
_WHITE_FWD = {sq: _diag_neighbors(sq, [-1]) for sq in range(1, 51)}
_WHITE_BWD = {sq: _diag_neighbors(sq, [+1]) for sq in range(1, 51)}
_BLACK_FWD = {sq: _diag_neighbors(sq, [+1]) for sq in range(1, 51)}
_BLACK_BWD = {sq: _diag_neighbors(sq, [-1]) for sq in range(1, 51)}

# ── Zobrist hashing ───────────────────────────────────────────────────────────

_rng = random.Random(0xDEADBEEF_CAFEBABE)
_PIECES = [WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING]
_ZOBRIST: dict[tuple[int, int], int] = {
    (p, sq): _rng.getrandbits(64) for p in _PIECES for sq in range(1, 51)
}
_ZOBRIST_BLACK = _rng.getrandbits(64)

def _hash_state(state: GameState) -> int:
    h = 0
    for sq in range(1, 51):
        p = state.board[sq]
        if p != EMPTY:
            h ^= _ZOBRIST[(p, sq)]
    if state.turn == 'black':
        h ^= _ZOBRIST_BLACK
    return h

# ── Transposition table ───────────────────────────────────────────────────────
# Entry: (depth, score, flag, best_move_path)

_TT: dict[int, tuple[int, float, str, Optional[tuple[int, ...]]]] = {}
_TT_MAX = 1_000_000

def _tt_clear() -> None:
    _TT.clear()

# ── Killers + History heuristic ───────────────────────────────────────────────

_MAX_PLY = 64
_killers: list[list[Optional[tuple[int, ...]]]] = [[None, None] for _ in range(_MAX_PLY)]
_HISTORY: dict[tuple[int, int], int] = {}

def _killers_clear() -> None:
    for slot in _killers:
        slot[0] = slot[1] = None

def _history_age() -> None:
    for k in _HISTORY:
        _HISTORY[k] >>= 1

def _store_killer(depth: int, path: tuple[int, ...]) -> None:
    if depth < _MAX_PLY and _killers[depth][0] != path:
        _killers[depth][1] = _killers[depth][0]
        _killers[depth][0] = path

def _update_history(move: Move, depth: int) -> None:
    key = (move.path[0], move.path[-1])
    _HISTORY[key] = _HISTORY.get(key, 0) + depth * depth

# ── Move ordering ─────────────────────────────────────────────────────────────

def _order_moves(
    moves: list[Move],
    tt_path: Optional[tuple[int, ...]],
    depth: int,
) -> list[Move]:
    tt: list[Move] = []
    captures: list[Move] = []
    killers: list[Move] = []
    rest: list[Move] = []
    k1 = _killers[depth][0] if depth < _MAX_PLY else None
    k2 = _killers[depth][1] if depth < _MAX_PLY else None

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

    # Multi-jump captures first, then single captures
    captures.sort(key=lambda m: len(m.captures), reverse=True)
    # Quiet moves sorted by history score
    rest.sort(key=lambda m: _HISTORY.get((m.path[0], m.path[-1]), 0), reverse=True)

    return tt + captures + killers + rest

# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate(state: GameState) -> float:
    result = game_result(state)
    if result == 'white': return 100000.0
    if result == 'black': return -100000.0
    if result == 'draw':  return 0.0

    board = state.board
    score = 0.0
    wm = wk = bm = bk = 0

    for sq in range(1, 51):
        piece = board[sq]
        if piece == EMPTY:
            continue
        score += MATERIAL[piece]

        if piece == WHITE_MAN:
            wm += 1
            row = _sq_row(sq)
            score += (9 - row) / 9.0 * 25          # advancement
            if sq in CENTER_SQUARES:  score += 18
            elif sq in NEAR_CENTER:   score += 8
            if sq in WHITE_BACK_ROW:  score += 10   # anchor
            if sq in EDGE_SQUARES:    score -= 12
            if sq in WHITE_PROMO_ROW: score += 20
            # Protection: friendly piece in backward diagonal
            for bsq in _WHITE_BWD[sq]:
                if board[bsq] in (WHITE_MAN, WHITE_KING):
                    score += 8; break
            # Forward mobility
            for fsq in _WHITE_FWD[sq]:
                if board[fsq] == EMPTY:
                    score += 4

        elif piece == WHITE_KING:
            wk += 1
            if sq in CENTER_SQUARES: score += 22
            elif sq in NEAR_CENTER:  score += 11
            if sq in EDGE_SQUARES:   score -= 10
            # King mobility: open diagonals (1 step)
            for nsq in _WHITE_FWD[sq] + _WHITE_BWD[sq]:
                if board[nsq] == EMPTY:
                    score += 3

        elif piece == BLACK_MAN:
            bm += 1
            row = _sq_row(sq)
            score -= row / 9.0 * 25
            if sq in CENTER_SQUARES:  score -= 18
            elif sq in NEAR_CENTER:   score -= 8
            if sq in BLACK_BACK_ROW:  score -= 10
            if sq in EDGE_SQUARES:    score += 12
            if sq in BLACK_PROMO_ROW: score -= 20
            for bsq in _BLACK_BWD[sq]:
                if board[bsq] in (BLACK_MAN, BLACK_KING):
                    score -= 8; break
            for fsq in _BLACK_FWD[sq]:
                if board[fsq] == EMPTY:
                    score -= 4

        elif piece == BLACK_KING:
            bk += 1
            if sq in CENTER_SQUARES: score -= 22
            elif sq in NEAR_CENTER:  score -= 11
            if sq in EDGE_SQUARES:   score += 10
            for nsq in _BLACK_FWD[sq] + _BLACK_BWD[sq]:
                if board[nsq] == EMPTY:
                    score -= 3

    total_w, total_b = wm + wk, bm + bk
    if total_w > 0 and total_b == 0: return 100000.0
    if total_b > 0 and total_w == 0: return -100000.0

    # Endgame: kings gain value as board empties
    total = total_w + total_b
    if total <= 14 and (wk or bk):
        score += (wk - bk) * 45 * (14 - total) / 14.0

    score += 5 if state.turn == 'white' else -5
    return score

# ── Quiescence search ─────────────────────────────────────────────────────────

_MAX_QDEPTH = 16

class _Timeout(Exception):
    pass

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

    captures.sort(key=lambda m: len(m.captures), reverse=True)

    if maximizing:
        best = float('-inf')
        for move in captures:
            val = _quiescence(apply_move(state, move), alpha, beta, False, deadline, qdepth + 1)
            if val > best: best = val
            if val > alpha: alpha = val
            if beta <= alpha: break
        return best
    else:
        best = float('inf')
        for move in captures:
            val = _quiescence(apply_move(state, move), alpha, beta, True, deadline, qdepth + 1)
            if val < best: best = val
            if val < beta: beta = val
            if beta <= alpha: break
        return best

# ── Alpha-beta with TT + PVS + LMR ───────────────────────────────────────────

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

    # TT lookup (also extracts best move for ordering)
    tt_path: Optional[tuple[int, ...]] = None
    tt_entry = _TT.get(zhash)
    if tt_entry is not None:
        tt_depth, tt_score, tt_flag, tt_path = tt_entry
        if tt_depth >= depth:
            if tt_flag == 'exact': return tt_score
            if tt_flag == 'lower': alpha = max(alpha, tt_score)
            elif tt_flag == 'upper': beta = min(beta, tt_score)
            if beta <= alpha: return tt_score

    result = game_result(state)
    if result is not None:
        if result == 'white': return 100000.0 + depth
        if result == 'black': return -100000.0 - depth
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
        for i, move in enumerate(moves):
            child = apply_move(state, move)
            ch = _hash_state(child)
            mp = tuple(move.path)
            is_killer = depth < _MAX_PLY and (mp == _killers[depth][0] or mp == _killers[depth][1])

            if i == 0:
                # PV move: full window, full depth
                val = _minimax(child, depth - 1, alpha, beta, False, deadline, ch)
            elif depth >= 3 and i >= 4 and not move.captures and not is_killer:
                # LMR: reduced depth + null window
                val = _minimax(child, depth - 2, alpha, alpha + 1, False, deadline, ch)
                if val > alpha:
                    val = _minimax(child, depth - 1, alpha, beta, False, deadline, ch)
            else:
                # PVS: full depth, null window
                val = _minimax(child, depth - 1, alpha, alpha + 1, False, deadline, ch)
                if val > alpha:
                    val = _minimax(child, depth - 1, alpha, beta, False, deadline, ch)

            if val > best:
                best = val
                best_path = mp
            if val > alpha:
                alpha = val
            if beta <= alpha:
                if not move.captures:
                    _store_killer(depth, mp)
                    _update_history(move, depth)
                break

    else:  # minimizing
        best = float('inf')
        for i, move in enumerate(moves):
            child = apply_move(state, move)
            ch = _hash_state(child)
            mp = tuple(move.path)
            is_killer = depth < _MAX_PLY and (mp == _killers[depth][0] or mp == _killers[depth][1])

            if i == 0:
                val = _minimax(child, depth - 1, alpha, beta, True, deadline, ch)
            elif depth >= 3 and i >= 4 and not move.captures and not is_killer:
                # LMR: reduced depth + null window
                val = _minimax(child, depth - 2, beta - 1, beta, True, deadline, ch)
                if val < beta:
                    val = _minimax(child, depth - 1, alpha, beta, True, deadline, ch)
            else:
                # PVS: full depth, null window
                val = _minimax(child, depth - 1, beta - 1, beta, True, deadline, ch)
                if val < beta:
                    val = _minimax(child, depth - 1, alpha, beta, True, deadline, ch)

            if val < best:
                best = val
                best_path = mp
            if val < beta:
                beta = val
            if beta <= alpha:
                if not move.captures:
                    _store_killer(depth, mp)
                    _update_history(move, depth)
                break

    # TT store
    if len(_TT) < _TT_MAX:
        flag = 'upper' if best <= alpha_orig else 'lower' if best >= beta else 'exact'
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
    _history_age()

    time_limit = TIME_LIMITS.get(depth, 5.0)
    deadline = time.monotonic() + time_limit
    maximizing = (state.turn == 'white')

    # Captures first at root, multi-jumps before single jumps
    ordered = sorted(moves, key=lambda m: (0 if m.captures else 1, -len(m.captures)))
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
                    child, d - 1,
                    float('-inf'), float('inf'),
                    not maximizing, deadline, child_hash,
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


def rank_moves(state: GameState, n: int = 5, depth: int = 5) -> list[tuple[Move, float]]:
    """Score all legal moves with proper alpha-beta search and return the top N."""
    moves = get_legal_moves(state)
    if not moves:
        return []

    _tt_clear()
    _killers_clear()
    _history_age()

    maximizing = state.turn == 'white'
    deadline = time.monotonic() + TIME_LIMITS.get(depth, 1.5)

    scored: list[tuple[float, Move]] = []
    for m in moves:
        child = apply_move(state, m)
        ch = _hash_state(child)
        try:
            val = _minimax(
                child, depth - 1,
                float('-inf'), float('inf'),
                not maximizing, deadline, ch,
            )
        except (_Timeout, Exception):
            val = evaluate(child)
        scored.append((val, m))

    scored.sort(key=lambda x: x[0], reverse=maximizing)
    return [(m, val) for val, m in scored[:n]]
