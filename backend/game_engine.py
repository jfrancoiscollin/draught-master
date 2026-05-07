from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
import copy

EMPTY = 0
WHITE_MAN = 1
WHITE_KING = 2
BLACK_MAN = 3
BLACK_KING = 4


def sq_to_rc(sq: int) -> Tuple[int, int]:
    idx = sq - 1
    row = idx // 5
    col_in_row = idx % 5
    col = col_in_row * 2 + (1 if row % 2 == 0 else 0)
    return (row, col)


def rc_to_sq(row: int, col: int) -> Optional[int]:
    if row < 0 or row > 9 or col < 0 or col > 9:
        return None
    if (row + col) % 2 == 0:
        return None
    col_in_row = col // 2
    sq = row * 5 + col_in_row + 1
    if sq < 1 or sq > 50:
        return None
    return sq


def _build_neighbors() -> Dict[int, Dict[Tuple[int, int], int]]:
    result: Dict[int, Dict[Tuple[int, int], int]] = {}
    for sq in range(1, 51):
        r, c = sq_to_rc(sq)
        nbrs: Dict[Tuple[int, int], int] = {}
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nr, nc = r + dr, c + dc
            nsq = rc_to_sq(nr, nc)
            if nsq is not None:
                nbrs[(dr, dc)] = nsq
        result[sq] = nbrs
    return result


def _build_extended() -> Dict[int, Dict[Tuple[int, int], List[int]]]:
    result: Dict[int, Dict[Tuple[int, int], List[int]]] = {}
    for sq in range(1, 51):
        r, c = sq_to_rc(sq)
        ext: Dict[Tuple[int, int], List[int]] = {}
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            line: List[int] = []
            nr, nc = r + dr, c + dc
            while 0 <= nr <= 9 and 0 <= nc <= 9:
                nsq = rc_to_sq(nr, nc)
                if nsq is not None:
                    line.append(nsq)
                nr += dr
                nc += dc
            if line:
                ext[(dr, dc)] = line
        result[sq] = ext
    return result


NEIGHBORS: Dict[int, Dict[Tuple[int, int], int]] = _build_neighbors()
EXTENDED: Dict[int, Dict[Tuple[int, int], List[int]]] = _build_extended()

MAN_DIRS = {
    'white': [(-1, -1), (-1, 1)],
    'black': [(1, -1), (1, 1)],
}


@dataclass
class Move:
    path: List[int]
    captures: List[int] = field(default_factory=list)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Move):
            return False
        return self.path == other.path and set(self.captures) == set(other.captures)

    def __hash__(self) -> int:
        return hash((tuple(self.path), frozenset(self.captures)))


@dataclass
class GameState:
    board: List[int]
    turn: str
    half_move_clock: int = 0
    move_history: List[Move] = field(default_factory=list)

    def copy(self) -> 'GameState':
        return GameState(
            board=self.board[:],
            turn=self.turn,
            half_move_clock=self.half_move_clock,
            move_history=self.move_history[:],
        )


def initial_board() -> List[int]:
    board = [EMPTY] * 51
    for sq in range(1, 21):
        board[sq] = BLACK_MAN
    for sq in range(31, 51):
        board[sq] = WHITE_MAN
    return board


def initial_state() -> GameState:
    return GameState(board=initial_board(), turn='white')


def _is_white(piece: int) -> bool:
    return piece in (WHITE_MAN, WHITE_KING)


def _is_black(piece: int) -> bool:
    return piece in (BLACK_MAN, BLACK_KING)


def _is_king(piece: int) -> bool:
    return piece in (WHITE_KING, BLACK_KING)


def _is_enemy(piece: int, turn: str) -> bool:
    if turn == 'white':
        return _is_black(piece)
    return _is_white(piece)


def _is_friendly(piece: int, turn: str) -> bool:
    if turn == 'white':
        return _is_white(piece)
    return _is_black(piece)


def _capture_sequences_man(
    sq: int,
    board: List[int],
    turn: str,
    captured_so_far: frozenset,
    path: List[int],
) -> List[Move]:
    results: List[Move] = []
    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        nbrs = NEIGHBORS.get(sq, {})
        if (dr, dc) not in nbrs:
            continue
        mid_sq = nbrs[(dr, dc)]
        mid_piece = board[mid_sq]
        if mid_sq in captured_so_far:
            continue
        if not _is_enemy(mid_piece, turn):
            continue
        mid_nbrs = NEIGHBORS.get(mid_sq, {})
        if (dr, dc) not in mid_nbrs:
            continue
        land_sq = mid_nbrs[(dr, dc)]
        if board[land_sq] != EMPTY and land_sq != path[0]:
            continue
        new_captured = captured_so_far | {mid_sq}
        new_path = path + [land_sq]
        sub = _capture_sequences_man(land_sq, board, turn, new_captured, new_path)
        if sub:
            results.extend(sub)
        else:
            results.append(Move(path=new_path, captures=list(new_captured)))
    return results


def _capture_sequences_king(
    sq: int,
    board: List[int],
    turn: str,
    captured_so_far: frozenset,
    path: List[int],
) -> List[Move]:
    results: List[Move] = []
    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        line = EXTENDED.get(sq, {}).get((dr, dc), [])
        enemy_found: Optional[int] = None
        enemy_sq: Optional[int] = None
        for s in line:
            if s in captured_so_far:
                break
            piece = board[s]
            if _is_friendly(piece, turn):
                break
            if _is_enemy(piece, turn):
                if enemy_found is not None:
                    break
                enemy_found = piece
                enemy_sq = s
                continue
            if enemy_found is not None and enemy_sq is not None:
                new_captured = captured_so_far | {enemy_sq}
                new_path = path + [s]
                sub = _capture_sequences_king(s, board, turn, new_captured, new_path)
                if sub:
                    results.extend(sub)
                else:
                    results.append(Move(path=new_path, captures=list(new_captured)))
    return results


def _all_captures(state: GameState) -> List[Move]:
    moves: List[Move] = []
    for sq in range(1, 51):
        piece = state.board[sq]
        if not _is_friendly(piece, state.turn):
            continue
        if _is_king(piece):
            seqs = _capture_sequences_king(sq, state.board, state.turn, frozenset(), [sq])
        else:
            seqs = _capture_sequences_man(sq, state.board, state.turn, frozenset(), [sq])
        moves.extend(seqs)
    return moves


def _all_simple_moves(state: GameState) -> List[Move]:
    moves: List[Move] = []
    for sq in range(1, 51):
        piece = state.board[sq]
        if not _is_friendly(piece, state.turn):
            continue
        if _is_king(piece):
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                for dest in EXTENDED.get(sq, {}).get((dr, dc), []):
                    if state.board[dest] != EMPTY:
                        break
                    moves.append(Move(path=[sq, dest], captures=[]))
        else:
            dirs = MAN_DIRS[state.turn]
            for dr, dc in dirs:
                nbrs = NEIGHBORS.get(sq, {})
                if (dr, dc) in nbrs:
                    dest = nbrs[(dr, dc)]
                    if state.board[dest] == EMPTY:
                        moves.append(Move(path=[sq, dest], captures=[]))
    return moves


def get_legal_moves(state: GameState) -> List[Move]:
    captures = _all_captures(state)
    if captures:
        max_len = max(len(m.captures) for m in captures)
        return [m for m in captures if len(m.captures) == max_len]
    return _all_simple_moves(state)


def apply_move(state: GameState, move: Move) -> GameState:
    new_state = state.copy()
    board = new_state.board
    from_sq = move.path[0]
    to_sq = move.path[-1]
    piece = board[from_sq]
    board[from_sq] = EMPTY
    board[to_sq] = piece
    for cap_sq in move.captures:
        board[cap_sq] = EMPTY
    if piece == WHITE_MAN and to_sq in range(1, 6):
        board[to_sq] = WHITE_KING
    elif piece == BLACK_MAN and to_sq in range(46, 51):
        board[to_sq] = BLACK_KING
    # Reset on capture OR man move (FMJD rule: clock counts king-only quiet moves)
    if move.captures or piece in (WHITE_MAN, BLACK_MAN):
        new_state.half_move_clock = 0
    else:
        new_state.half_move_clock += 1
    new_state.turn = 'black' if state.turn == 'white' else 'white'
    new_state.move_history = state.move_history + [move]
    return new_state


def game_result(state: GameState) -> Optional[str]:
    legal = get_legal_moves(state)
    if not legal:
        if state.turn == 'white':
            return 'black'
        return 'white'
    whites = sum(1 for sq in range(1, 51) if state.board[sq] in (WHITE_MAN, WHITE_KING))
    blacks = sum(1 for sq in range(1, 51) if state.board[sq] in (BLACK_MAN, BLACK_KING))
    if whites == 0:
        return 'black'
    if blacks == 0:
        return 'white'
    has_men = any(
        state.board[sq] in (WHITE_MAN, BLACK_MAN) for sq in range(1, 51)
    )
    # Kings-only endgame: draw after 32 half-moves (16 full moves) without capture
    # Normal game: draw after 50 half-moves (25 full moves) without capture
    draw_threshold = 50 if has_men else 32
    if state.half_move_clock >= draw_threshold:
        return 'draw'
    return None


def board_to_fen(state: GameState) -> str:
    turn_char = 'W' if state.turn == 'white' else 'B'
    white_men = []
    white_kings = []
    black_men = []
    black_kings = []
    for sq in range(1, 51):
        p = state.board[sq]
        if p == WHITE_MAN:
            white_men.append(str(sq))
        elif p == WHITE_KING:
            white_kings.append('K' + str(sq))
        elif p == BLACK_MAN:
            black_men.append(str(sq))
        elif p == BLACK_KING:
            black_kings.append('K' + str(sq))
    white_parts = white_kings + white_men
    black_parts = black_kings + black_men
    w_str = ','.join(white_parts) if white_parts else ''
    b_str = ','.join(black_parts) if black_parts else ''
    return f"{turn_char}:W{w_str}:B{b_str}"


def fen_to_board(fen: str) -> GameState:
    board = [EMPTY] * 51
    parts = fen.strip().split(':')
    turn_char = parts[0].strip()
    turn = 'white' if turn_char == 'W' else 'black'
    for section in parts[1:]:
        if not section:
            continue
        color = section[0]
        pieces_str = section[1:]
        if not pieces_str:
            continue
        for token in pieces_str.split(','):
            token = token.strip()
            if not token:
                continue
            is_king = token.startswith('K')
            num_str = token[1:] if is_king else token
            try:
                sq = int(num_str)
            except ValueError:
                continue
            if sq < 1 or sq > 50:
                continue
            if color == 'W':
                board[sq] = WHITE_KING if is_king else WHITE_MAN
            else:
                board[sq] = BLACK_KING if is_king else BLACK_MAN
    return GameState(board=board, turn=turn)


def move_to_pdn(move: Move) -> str:
    if move.captures:
        return 'x'.join(str(s) for s in move.path)
    return '-'.join(str(s) for s in move.path)
