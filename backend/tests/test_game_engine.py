"""
Tests unitaires pour game_engine.py — règles FMJD complètes.

Géométrie de référence (rangées 0-9, colonnes 0-9, cases sombres uniquement) :
  sq 32 → (6,3)   sq 27 → (5,2)   sq 21 → (4,1)   sq 16 → (3,0)
  sq 28 → (5,4)   sq 23 → (4,5)   sq 19 → (3,6)   sq  5 → (0,9)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from game_engine import (
    EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING,
    sq_to_rc, rc_to_sq,
    GameState, Move,
    initial_board, initial_state,
    get_legal_moves, apply_move, game_result,
    board_to_fen, fen_to_board, move_to_pdn,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def empty_board() -> list:
    return [EMPTY] * 51


def state_from(board: list, turn: str = 'white', clock: int = 0) -> GameState:
    return GameState(board=board, turn=turn, half_move_clock=clock)


def paths(moves) -> list:
    return [m.path for m in moves]


# ── Coordonnées ────────────────────────────────────────────────────────────────

class TestCoordinates:
    def test_sq_to_rc_first_square(self):
        assert sq_to_rc(1) == (0, 1)

    def test_sq_to_rc_fifth_square(self):
        assert sq_to_rc(5) == (0, 9)

    def test_sq_to_rc_sixth_square(self):
        # Rangée 1 (index paire → colonne décalée à gauche)
        assert sq_to_rc(6) == (1, 0)

    def test_sq_to_rc_last_square(self):
        assert sq_to_rc(50) == (9, 8)

    def test_rc_to_sq_roundtrip(self):
        for sq in range(1, 51):
            r, c = sq_to_rc(sq)
            assert rc_to_sq(r, c) == sq

    def test_rc_to_sq_out_of_bounds(self):
        assert rc_to_sq(-1, 0) is None
        assert rc_to_sq(0, 10) is None
        assert rc_to_sq(10, 0) is None

    def test_rc_to_sq_light_square(self):
        # (0,0) est une case claire → non jouable
        assert rc_to_sq(0, 0) is None


# ── Position initiale ──────────────────────────────────────────────────────────

class TestInitialPosition:
    def test_black_pieces_on_rows_1_to_4(self):
        board = initial_board()
        assert all(board[sq] == BLACK_MAN for sq in range(1, 21))

    def test_white_pieces_on_rows_7_to_10(self):
        board = initial_board()
        assert all(board[sq] == WHITE_MAN for sq in range(31, 51))

    def test_middle_rows_empty(self):
        board = initial_board()
        assert all(board[sq] == EMPTY for sq in range(21, 31))

    def test_total_pieces(self):
        board = initial_board()
        whites = sum(1 for sq in range(1, 51) if board[sq] == WHITE_MAN)
        blacks = sum(1 for sq in range(1, 51) if board[sq] == BLACK_MAN)
        assert whites == 20
        assert blacks == 20

    def test_initial_turn_is_white(self):
        assert initial_state().turn == 'white'


# ── Déplacements simples ───────────────────────────────────────────────────────

class TestSimpleMoves:
    def test_white_man_moves_forward(self):
        """Pion blanc isolé au centre : deux coups diagonaux vers l'avant."""
        board = empty_board()
        board[32] = WHITE_MAN           # (6,3) → peut aller à 27 et 28
        moves = get_legal_moves(state_from(board))
        assert set(m.path[-1] for m in moves) == {27, 28}
        assert all(not m.captures for m in moves)

    def test_black_man_moves_forward(self):
        """Pion noir avance vers les rangées 46-50."""
        board = empty_board()
        board[19] = BLACK_MAN           # (3,6) → peut aller à 23 et 24
        moves = get_legal_moves(state_from(board, 'black'))
        assert set(m.path[-1] for m in moves) == {23, 24}

    def test_white_man_blocked_at_edge(self):
        """Pion blanc en case 1 (coin) : aucun coup simple possible."""
        board = empty_board()
        board[1] = WHITE_MAN
        moves = get_legal_moves(state_from(board))
        assert moves == []

    def test_king_slides_full_diagonal(self):
        """Dame blanche en 32 : peut atteindre la case 5 (3 diagonales) sans obstacle."""
        board = empty_board()
        board[32] = WHITE_KING
        moves = get_legal_moves(state_from(board))
        # Diagonale NE depuis 32 → 28, 23, 19, 14, 10, 5
        assert [32, 5] in paths(moves)

    def test_king_blocked_by_own_piece(self):
        """Dame bloquée par un pion ami : ne peut pas passer ni atterrir dessus."""
        board = empty_board()
        board[32] = WHITE_KING
        board[27] = WHITE_MAN           # bloque la diagonale NW depuis 32
        moves = get_legal_moves(state_from(board))
        # Filtrer uniquement les coups de la DAME (source = 32), pas du pion en 27
        king_dests = {m.path[-1] for m in moves if m.path[0] == 32}
        assert 27 not in king_dests   # case occupée par pion ami
        assert 21 not in king_dests   # au-delà du blocage
        assert 16 not in king_dests   # encore plus loin

    def test_initial_position_legal_moves_count(self):
        """Position initiale : 7 coups légaux pour les blancs (pions des rangées 6-7)."""
        state = initial_state()
        moves = get_legal_moves(state)
        assert len(moves) == 9   # 9 pions peuvent avancer, chacun avec 1-2 coups


# ── Prise obligatoire ──────────────────────────────────────────────────────────

class TestMandatoryCapture:
    def test_capture_is_mandatory(self):
        """Pion blanc peut capturer ou avancer : seule la capture est légale."""
        board = empty_board()
        board[32] = WHITE_MAN
        board[28] = BLACK_MAN   # en diagonale (-1,1) depuis 32 → landing sq 23
        moves = get_legal_moves(state_from(board))
        assert all(m.captures for m in moves)
        assert all(23 in m.path for m in moves)

    def test_man_captures_jump_over_enemy(self):
        """Le pion saute exactement par-dessus l'ennemi vers la case libre derrière."""
        board = empty_board()
        board[32] = WHITE_MAN
        board[27] = BLACK_MAN   # diagonale (-1,-1) depuis 32 → landing 21
        moves = get_legal_moves(state_from(board))
        assert len(moves) == 1
        assert moves[0].path == [32, 21]
        assert moves[0].captures == [27]

    def test_king_capture_multiple_landing_squares(self):
        """Dame capture un pion adverse et peut atterrir sur plusieurs cases derrière."""
        board = empty_board()
        board[32] = WHITE_KING
        board[23] = BLACK_MAN   # diagonale NE depuis 32, landing: 19,14,10,5
        moves = get_legal_moves(state_from(board))
        assert all(23 in m.captures for m in moves)
        landing = {m.path[-1] for m in moves}
        assert landing == {19, 14, 10, 5}


# ── Prise maximale ─────────────────────────────────────────────────────────────

class TestMaxCapture:
    def test_longer_sequence_wins(self):
        """Quand une séquence de 2 prises et une de 1 sont disponibles, seule la 2-prise est légale."""
        board = empty_board()
        board[32] = WHITE_MAN
        # Séquence 2 prises : 32 → capture 27 → landing 21 → capture 17 → landing 12
        board[27] = BLACK_MAN
        board[17] = BLACK_MAN
        # Séquence 1 prise  : 32 → capture 28 → landing 23
        board[28] = BLACK_MAN
        moves = get_legal_moves(state_from(board))
        assert all(len(m.captures) == 2 for m in moves)
        assert [32, 21, 12] in paths(moves)

    def test_equal_length_sequences_both_legal(self):
        """Deux séquences de même longueur sont toutes les deux légales."""
        board = empty_board()
        board[32] = WHITE_MAN
        board[27] = BLACK_MAN   # séquence A: 32 → 21
        board[28] = BLACK_MAN   # séquence B: 32 → 23
        moves = get_legal_moves(state_from(board))
        assert len(moves) == 2
        assert all(len(m.captures) == 1 for m in moves)


# ── Appliquer un coup ──────────────────────────────────────────────────────────

class TestApplyMove:
    def test_piece_moves_to_destination(self):
        board = empty_board()
        board[32] = WHITE_MAN
        state = state_from(board)
        move = Move(path=[32, 27], captures=[])
        new = apply_move(state, move)
        assert new.board[27] == WHITE_MAN
        assert new.board[32] == EMPTY

    def test_captured_piece_removed(self):
        board = empty_board()
        board[32] = WHITE_MAN
        board[27] = BLACK_MAN
        state = state_from(board)
        move = Move(path=[32, 21], captures=[27])
        new = apply_move(state, move)
        assert new.board[27] == EMPTY
        assert new.board[21] == WHITE_MAN

    def test_turn_switches(self):
        board = empty_board()
        board[32] = WHITE_MAN
        state = state_from(board, 'white')
        move = Move(path=[32, 27], captures=[])
        new = apply_move(state, move)
        assert new.turn == 'black'

    def test_white_man_promotes_on_row_1(self):
        """Pion blanc atteignant les cases 1-5 doit être promu en dame."""
        board = empty_board()
        board[6] = WHITE_MAN    # (1,0) → peut avancer vers 1 (0,1)
        state = state_from(board)
        move = Move(path=[6, 1], captures=[])
        new = apply_move(state, move)
        assert new.board[1] == WHITE_KING

    def test_black_man_promotes_on_row_10(self):
        """Pion noir atteignant les cases 46-50 doit être promu en dame."""
        board = empty_board()
        board[45] = BLACK_MAN   # (8,9) → peut avancer vers 50 (9,8)
        state = state_from(board, 'black')
        move = Move(path=[45, 50], captures=[])
        new = apply_move(state, move)
        assert new.board[50] == BLACK_KING

    def test_half_move_clock_resets_on_capture(self):
        board = empty_board()
        board[32] = WHITE_MAN
        board[27] = BLACK_MAN
        state = state_from(board, clock=10)
        move = Move(path=[32, 21], captures=[27])
        new = apply_move(state, move)
        assert new.half_move_clock == 0

    def test_half_move_clock_resets_on_man_move(self):
        board = empty_board()
        board[32] = WHITE_MAN
        state = state_from(board, clock=10)
        move = Move(path=[32, 27], captures=[])
        new = apply_move(state, move)
        assert new.half_move_clock == 0

    def test_half_move_clock_increments_on_king_quiet_move(self):
        board = empty_board()
        board[32] = WHITE_KING
        state = state_from(board, clock=5)
        move = Move(path=[32, 27], captures=[])
        new = apply_move(state, move)
        assert new.half_move_clock == 6

    def test_original_state_unchanged(self):
        """apply_move ne modifie pas l'état source (immutabilité)."""
        board = empty_board()
        board[32] = WHITE_MAN
        state = state_from(board)
        move = Move(path=[32, 27], captures=[])
        apply_move(state, move)
        assert state.board[32] == WHITE_MAN
        assert state.board[27] == EMPTY


# ── Résultat de la partie ──────────────────────────────────────────────────────

class TestGameResult:
    def test_ongoing_game_returns_none(self):
        state = initial_state()
        assert game_result(state) is None

    def test_white_wins_when_black_has_no_pieces(self):
        board = empty_board()
        board[32] = WHITE_MAN
        state = state_from(board, 'black')
        assert game_result(state) == 'white'

    def test_black_wins_when_white_has_no_pieces(self):
        board = empty_board()
        board[19] = BLACK_MAN
        state = state_from(board, 'white')
        assert game_result(state) == 'black'

    def test_black_wins_when_white_is_blocked(self):
        """Blancs sans coup légal → les noirs gagnent."""
        board = empty_board()
        # Pion blanc coincé en coin case 1, bloqué par deux pions noirs
        board[1] = WHITE_MAN
        board[6] = BLACK_MAN    # bloque la seule case accessible
        state = state_from(board, 'white')
        assert game_result(state) == 'black'

    def test_draw_at_50_half_moves_with_men(self):
        board = empty_board()
        board[32] = WHITE_MAN
        board[19] = BLACK_MAN
        state = state_from(board, clock=50)
        assert game_result(state) == 'draw'

    def test_not_draw_at_49_half_moves(self):
        board = empty_board()
        board[32] = WHITE_MAN
        board[19] = BLACK_MAN
        state = state_from(board, clock=49)
        assert game_result(state) is None

    def test_draw_at_32_half_moves_kings_only(self):
        """Finale de dames seulement : nulle après 32 demi-coups (pas 50)."""
        board = empty_board()
        board[32] = WHITE_KING
        board[19] = BLACK_KING
        state = state_from(board, clock=32)
        assert game_result(state) == 'draw'

    def test_no_draw_at_32_when_men_present(self):
        """Avec des pions sur le plateau, le seuil est 50, pas 32."""
        board = empty_board()
        board[32] = WHITE_KING
        board[19] = BLACK_MAN   # un pion → seuil reste 50
        state = state_from(board, clock=32)
        assert game_result(state) is None


# ── FEN sérialisation ──────────────────────────────────────────────────────────

class TestFen:
    def test_fen_roundtrip_initial(self):
        state = initial_state()
        fen = board_to_fen(state)
        restored = fen_to_board(fen)
        assert restored.board == state.board
        assert restored.turn == state.turn

    def test_fen_roundtrip_custom_position(self):
        board = empty_board()
        board[32] = WHITE_KING
        board[19] = BLACK_MAN
        board[5]  = WHITE_MAN
        state = state_from(board, 'black')
        restored = fen_to_board(board_to_fen(state))
        assert restored.board == board
        assert restored.turn == 'black'

    def test_fen_turn_character(self):
        assert board_to_fen(state_from(empty_board(), 'white')).startswith('W:')
        assert board_to_fen(state_from(empty_board(), 'black')).startswith('B:')

    def test_fen_king_prefix(self):
        board = empty_board()
        board[32] = WHITE_KING
        fen = board_to_fen(state_from(board))
        assert 'K32' in fen

    def test_fen_to_board_invalid_graceful(self):
        """FEN malformé ne lève pas d'exception."""
        state = fen_to_board('INVALID')
        assert isinstance(state, GameState)


# ── Notation PDN ──────────────────────────────────────────────────────────────

class TestPdn:
    def test_simple_move_notation(self):
        move = Move(path=[32, 27], captures=[])
        assert move_to_pdn(move) == '32-27'

    def test_single_capture_notation(self):
        move = Move(path=[32, 21], captures=[27])
        assert move_to_pdn(move) == '32x21'

    def test_multi_capture_notation(self):
        move = Move(path=[32, 21, 12], captures=[27, 17])
        assert move_to_pdn(move) == '32x21x12'


# ── Move equality ─────────────────────────────────────────────────────────────

class TestMoveEquality:
    def test_equal_moves(self):
        a = Move(path=[32, 21], captures=[27])
        b = Move(path=[32, 21], captures=[27])
        assert a == b

    def test_different_paths(self):
        a = Move(path=[32, 21], captures=[27])
        b = Move(path=[32, 23], captures=[28])
        assert a != b

    def test_capture_order_irrelevant(self):
        """L'ordre des captures dans la liste n'importe pas pour l'égalité."""
        a = Move(path=[32, 12], captures=[27, 17])
        b = Move(path=[32, 12], captures=[17, 27])
        assert a == b
