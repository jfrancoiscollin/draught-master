"""Bridge between game_engine types and dilf (pedagogy) types.

Provides:
  - ge_state_to_dilf   : game_engine.GameState  → pedagogy.game.GameState
  - ge_move_to_dilf    : game_engine.Move        → pedagogy.game.Move
  - dilf_state_to_ge   : pedagogy.game.GameState → game_engine.GameState
  - GameEngineAdapter  : EngineProtocol impl wrapping game_engine
"""
from __future__ import annotations

from game_engine import (
    BLACK_KING,
    BLACK_MAN,
    EMPTY,
    WHITE_KING,
    WHITE_MAN,
    GameState as GEState,
    Move as GEMove,
    apply_move as ge_apply_move,
    get_legal_moves as ge_legal_moves,
)
from pedagogy.game import GameState as DState, Move as DMove
from pedagogy.protocols import EngineProtocol


# ---------------------------------------------------------------------------
# State bridge
# ---------------------------------------------------------------------------

def ge_state_to_dilf(s: GEState) -> DState:
    wm: set[int] = set()
    wk: set[int] = set()
    bm: set[int] = set()
    bk: set[int] = set()
    for sq in range(1, 51):
        p = s.board[sq]
        if p == WHITE_MAN:
            wm.add(sq)
        elif p == WHITE_KING:
            wk.add(sq)
        elif p == BLACK_MAN:
            bm.add(sq)
        elif p == BLACK_KING:
            bk.add(sq)
    return DState(
        white_men=frozenset(wm),
        white_kings=frozenset(wk),
        black_men=frozenset(bm),
        black_kings=frozenset(bk),
        turn=s.turn,  # type: ignore[arg-type]
    )


def ge_move_to_dilf(m: GEMove, board: list[int]) -> DMove:
    path = tuple(m.path)
    captures = tuple(m.captures)
    from_sq = path[0]
    to_sq = path[-1]
    piece = board[from_sq]
    promotion = (
        (piece == WHITE_MAN and to_sq in range(1, 6))
        or (piece == BLACK_MAN and to_sq in range(46, 51))
    )
    return DMove(path=path, captures=captures, promotion=promotion)


def dilf_state_to_ge(s: DState) -> GEState:
    board = [EMPTY] * 51
    for sq in s.white_men:
        board[sq] = WHITE_MAN
    for sq in s.white_kings:
        board[sq] = WHITE_KING
    for sq in s.black_men:
        board[sq] = BLACK_MAN
    for sq in s.black_kings:
        board[sq] = BLACK_KING
    return GEState(board=board, turn=s.turn)


# ---------------------------------------------------------------------------
# EngineProtocol adapter
# ---------------------------------------------------------------------------

class GameEngineAdapter:
    """Adapts game_engine to pedagogy.protocols.EngineProtocol.

    Used by assemble_verdict to compute is_forced and mobility features.
    """

    def legal_moves(self, state: DState) -> list[DMove]:
        ge_state = dilf_state_to_ge(state)
        ge_moves = ge_legal_moves(ge_state)
        return [ge_move_to_dilf(m, ge_state.board) for m in ge_moves]

    def apply_move(self, state: DState, move: DMove) -> DState:
        ge_state = dilf_state_to_ge(state)
        # Match to an exact legal GE move first (preserves any internal state)
        for gm in ge_legal_moves(ge_state):
            if tuple(gm.path) == move.path and tuple(gm.captures) == move.captures:
                return ge_state_to_dilf(ge_apply_move(ge_state, gm))
        # Fallback: construct GEMove directly (shouldn't happen in normal flow)
        gm = GEMove(path=list(move.path), captures=list(move.captures))
        return ge_state_to_dilf(ge_apply_move(ge_state, gm))
