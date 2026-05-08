#!/usr/bin/env python3
"""Investigate broken exercises and find fixes."""
import sys
sys.path.insert(0, '/home/user/Ai-draught')
from backend.game_engine import fen_to_board, get_legal_moves, move_to_pdn, apply_move, GameState

def parse_pdn_move(s, state):
    """Try to find a move matching PDN string s in current state."""
    legal = get_legal_moves(state)
    for m in legal:
        if move_to_pdn(m) == s:
            return m
    return None

def trace_solution(fen, solution, label=""):
    """Trace a solution and report where it breaks."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  FEN: {fen}")
    print(f"  Solution: {solution}")
    print(f"{'='*60}")
    state = fen_to_board(fen)
    for step, move_str in enumerate(solution):
        legal = get_legal_moves(state)
        legal_strs = sorted(set(move_to_pdn(m) for m in legal))
        m = parse_pdn_move(move_str, state)
        if m is None:
            print(f"  FAIL at step {step} ({state.turn}): '{move_str}' not found")
            print(f"    Legal moves: {legal_strs[:15]}")
            # Show board state
            print(f"    Board (turn={state.turn}):")
            whites = [sq for sq in range(1,51) if state.board[sq] in (1,2)]
            wkings = [sq for sq in range(1,51) if state.board[sq] == 2]
            blacks = [sq for sq in range(1,51) if state.board[sq] in (3,4)]
            bkings = [sq for sq in range(1,51) if state.board[sq] == 4]
            print(f"    White men: {whites}")
            print(f"    White kings: {wkings}")
            print(f"    Black men: {blacks}")
            print(f"    Black kings: {bkings}")
            return state, step
        else:
            print(f"  step {step} ({state.turn}): {move_str} OK  captures={m.captures}")
            state = apply_move(state, m)
    print("  Solution completed successfully!")
    return state, -1

def find_captures_for_piece(sq, state):
    """Find all captures starting from a specific square."""
    from backend.game_engine import _capture_sequences_man, _capture_sequences_king, _is_king
    piece = state.board[sq]
    if piece == 0:
        return []
    if _is_king(piece):
        return _capture_sequences_king(sq, state.board, state.turn, frozenset(), [sq])
    else:
        return _capture_sequences_man(sq, state.board, state.turn, frozenset(), [sq])

def show_piece_at(sq, state):
    from backend.game_engine import WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING, EMPTY
    p = state.board[sq]
    names = {EMPTY: 'empty', WHITE_MAN: 'white_man', WHITE_KING: 'white_king', BLACK_MAN: 'black_man', BLACK_KING: 'black_king'}
    return names.get(p, f'unknown({p})')

# ==========================================
# EXERCISE 203
# ==========================================
print("\n\n### EXERCISE 203 ###")
fen203 = "B:W27,28,30,31,32,33,35,37,38,39,40,48:B3,6,13,15,16,17,18,19,20,23,24,26"
sol203 = ['3x45', '25x41', '17-22', '28x17', '23-28', '32x25', '6-11', '30x8', '3x45']
trace_solution(fen203, sol203, "EX 203")

# Check: what's at sq 3 in black's turn?
state203 = fen_to_board(fen203)
print(f"\n  Piece at sq 3: {show_piece_at(3, state203)}")
print(f"  '3x45' would need a king at sq3. Is it B: (black to move)?")
print(f"  FEN starts with B:, so black moves. sq3=BLACK_MAN, not king.")
print(f"  FIX: Add K prefix to sq 3 in black pieces: B:W27,28,30,31,32,33,35,37,38,39,40,48:BK3,6,13,...")

# Try with K3:
fen203_fix = "B:W27,28,30,31,32,33,35,37,38,39,40,48:BK3,6,13,15,16,17,18,19,20,23,24,26"
trace_solution(fen203_fix, sol203, "EX 203 FIX with K3")

# Also check step 8 (3x45 again) - after applying all previous moves, is there still a king at 3?
# Let's trace partially
print("\n  Checking 3x45 final step - need a king at 3 after 8 moves:")
state_tmp = fen_to_board(fen203_fix)
for i, ms in enumerate(sol203[:8]):
    m = parse_pdn_move(ms, state_tmp)
    if m is None:
        legal = get_legal_moves(state_tmp)
        legal_strs = sorted(set(move_to_pdn(x) for x in legal))
        print(f"  Broke at step {i}: {ms}, legal={legal_strs[:10]}")
        break
    state_tmp = apply_move(state_tmp, m)
    print(f"  step {i}: {ms}")

# ==========================================
# EXERCISE 269
# ==========================================
print("\n\n### EXERCISE 269 ###")
fen269 = "W:W22,28,30,32,33,34,35,36,38,42,48:B8,9,11,13,14,16,18,19,21,23,24"
sol269 = ['22-17', '11x22', '28x26', '21x12', '28-22', '18x27', '32x21', '16x27', '33-29', '24x33', '38x16']
trace_solution(fen269, sol269, "EX 269")

# ==========================================
# EXERCISE 286
# ==========================================
print("\n\n### EXERCISE 286 ###")
fen286 = "W:W22,27,32,33,34,37,38,39,40,41,43,45:B8,9,11,12,13,15,16,18,19,20,21,25"
sol286 = ['34-40', '32-28', '21x23', '18x27', '32x21', '16x27', '34-30', '25x34', '40x16']
trace_solution(fen286, sol286, "EX 286")

state286 = fen_to_board(fen286)
print(f"\n  Piece at sq 34: {show_piece_at(34, state286)}")
print(f"  '34-40': white man at 34 cannot move to 40 (would need to go down-board = toward higher numbers)")
# On 10x10, rows 1-5 are top, rows 46-50 are bottom.
# sq 34 is in row (34-1)//5=6 (0-indexed), col...
# White men move toward lower numbers (toward row 0)
# 34-40: going from row 6 to row 7 = moving FORWARD for black pieces
# So 34 is white and cannot move to 40 as white man
print(f"  White man moves toward rows 1-5 (lower squares). 34->40 is impossible for white man.")
print(f"  Hypothesis: sq34 should be a WHITE KING")

fen286_fix = "W:W22,27,32,33,K34,37,38,39,40,41,43,45:B8,9,11,12,13,15,16,18,19,20,21,25"
trace_solution(fen286_fix, sol286, "EX 286 FIX with K34")

# ==========================================
# EXERCISE 310
# ==========================================
print("\n\n### EXERCISE 310 ###")
fen310 = "B:W25,26,27,28,32,33,34,38,39,41,42,43,44,48,49,50:B1,3,5,6,8,9,10,13,14,16,17,18,19,21,23,24"
sol310 = ['23-29', '34x12', '19-23', '28x30', '13-18', '12x23', '25x14', '10x46', '19x46']
trace_solution(fen310, sol310, "EX 310")

# step 6: '25x14' fails. Let's see what state we're in
state310 = fen_to_board(fen310)
for i, ms in enumerate(sol310[:6]):
    m = parse_pdn_move(ms, state310)
    if m is None:
        legal = get_legal_moves(state310)
        legal_strs = sorted(set(move_to_pdn(x) for x in legal))
        print(f"  STOPPED at step {i}: {ms}")
        print(f"  Legal: {legal_strs[:15]}")
        print(f"  Whites: {[sq for sq in range(1,51) if state310.board[sq] in (1,2)]}")
        print(f"  Wkings: {[sq for sq in range(1,51) if state310.board[sq] == 2]}")
        print(f"  Blacks: {[sq for sq in range(1,51) if state310.board[sq] in (3,4)]}")
        break
    state310 = apply_move(state310, m)
    print(f"  Applied step {i}: {ms}")

print(f"\n  At step 6, whites={[sq for sq in range(1,51) if state310.board[sq] in (1,2)]}")
print(f"  Wkings={[sq for sq in range(1,51) if state310.board[sq] == 2]}")
print(f"  Blacks={[sq for sq in range(1,51) if state310.board[sq] in (3,4)]}")
print(f"  Bkings={[sq for sq in range(1,51) if state310.board[sq] == 4]}")
print(f"  Turn={state310.turn}")
legal310 = get_legal_moves(state310)
legal310_strs = sorted(set(move_to_pdn(m) for m in legal310))
print(f"  Legal moves: {legal310_strs[:20]}")

# ==========================================
# EXERCISE 367
# ==========================================
print("\n\n### EXERCISE 367 ###")
fen367 = "W:W28,29,31,33,35,36,37,38,39,41,42,43,44,46,47,48,49,50:B1,2,3,4,6,7,8,9,10,12,13,16,17,18,19,20,24,26"
sol367 = ['41x5']
trace_solution(fen367, sol367, "EX 367")

state367 = fen_to_board(fen367)
print(f"\n  Piece at sq 41: {show_piece_at(41, state367)}")
print(f"  '41x5' would need a king at 41.")
fen367_fix = "W:W28,29,31,33,35,36,37,38,39,K41,42,43,44,46,47,48,49,50:B1,2,3,4,6,7,8,9,10,12,13,16,17,18,19,20,24,26"
trace_solution(fen367_fix, sol367, "EX 367 FIX with K41")

# ==========================================
# EXERCISE 397
# ==========================================
print("\n\n### EXERCISE 397 ###")
fen397 = "B:W25,28,29,33,35,37,38,39,40,41,44,48:B3,4,5,8,9,10,17,19,21,22,24,27"
sol397 = ['21-26', '29x20', '19-23', '28x19', '26-31', '37x26', '26x28', '9-14', '20x9', '3x45']
trace_solution(fen397, sol397, "EX 397")

# step 6: '26x28' fails. Let's see what we have
state397 = fen_to_board(fen397)
for i, ms in enumerate(sol397[:6]):
    m = parse_pdn_move(ms, state397)
    if m is None:
        legal = get_legal_moves(state397)
        legal_strs = sorted(set(move_to_pdn(x) for x in legal))
        print(f"  STOPPED at step {i}: {ms}")
        print(f"  Legal: {legal_strs[:15]}")
        break
    state397 = apply_move(state397, m)
    print(f"  Applied step {i}: {ms}")

print(f"\n  At step 6:")
print(f"  Whites={[sq for sq in range(1,51) if state397.board[sq] in (1,2)]}")
print(f"  Wkings={[sq for sq in range(1,51) if state397.board[sq] == 2]}")
print(f"  Blacks={[sq for sq in range(1,51) if state397.board[sq] in (3,4)]}")
print(f"  Bkings={[sq for sq in range(1,51) if state397.board[sq] == 4]}")
print(f"  Turn={state397.turn}")
legal397 = get_legal_moves(state397)
legal397_strs = sorted(set(move_to_pdn(m) for m in legal397))
print(f"  Legal: {legal397_strs[:20]}")
print(f"  Full legal: {[(move_to_pdn(m), m.captures) for m in legal397][:20]}")

# '26x28' - at step 6 it's white's turn (W plays odd steps: 1,3,5 and black plays even: 0,2,4,6...)
# Wait: B: FEN means black starts, so step 0 = black, step 1 = white, step 2 = black, ...
# step 6 = black's move
# But white just captured at step 5 ('37x26') - captured piece at 26?
# Then '26x28' would be white capturing again from 26... that can't be right if white already moved

# ==========================================
# EXERCISE 401
# ==========================================
print("\n\n### EXERCISE 401 ###")
fen401 = "B:W23,24,26,27,29,32,34,35,39,41,44,49:B5,8,10,12,13,14,15,16,17,18,20,25"
sol401 = ['25-30', '34x25', '18-22', '27x7', '7x9', '14x3', '25x14', '10x46']
trace_solution(fen401, sol401, "EX 401")

state401 = fen_to_board(fen401)
for i, ms in enumerate(sol401[:4]):
    m = parse_pdn_move(ms, state401)
    if m is None:
        legal = get_legal_moves(state401)
        legal_strs = sorted(set(move_to_pdn(x) for x in legal))
        print(f"  STOPPED at step {i}: {ms}")
        print(f"  Legal: {legal_strs[:15]}")
        break
    state401 = apply_move(state401, m)
    print(f"  Applied step {i}: {ms}")

print(f"\n  At step 4:")
print(f"  Whites={[sq for sq in range(1,51) if state401.board[sq] in (1,2)]}")
print(f"  Wkings={[sq for sq in range(1,51) if state401.board[sq] == 2]}")
print(f"  Blacks={[sq for sq in range(1,51) if state401.board[sq] in (3,4)]}")
print(f"  Bkings={[sq for sq in range(1,51) if state401.board[sq] == 4]}")
print(f"  Turn={state401.turn}")
legal401 = get_legal_moves(state401)
legal401_strs = sorted(set(move_to_pdn(m) for m in legal401))
print(f"  Legal: {legal401_strs[:20]}")
print(f"  Full legal: {[(move_to_pdn(m), m.captures) for m in legal401][:20]}")

# ==========================================
# EXERCISE 406
# ==========================================
print("\n\n### EXERCISE 406 ###")
fen406 = "W:W31,33,34,35,36,38,42,43,47,48:B2,3,11,12,13,15,18,22,23,25,27"
sol406 = ['48x6', '34-30', '25x34', '43-39', '34x32', '33-28', '22x33', '31x22', '18x27', '42-38', '33x42', '48x6']
trace_solution(fen406, sol406, "EX 406")

state406 = fen_to_board(fen406)
print(f"\n  Piece at sq 48: {show_piece_at(48, state406)}")
print(f"  '48x6' would need a king at 48.")
fen406_fix = "W:W31,33,34,35,36,38,42,43,47,K48:B2,3,11,12,13,15,18,22,23,25,27"
trace_solution(fen406_fix, sol406, "EX 406 FIX with K48")

# ==========================================
# EXERCISE 407
# ==========================================
print("\n\n### EXERCISE 407 ###")
fen407 = "B:W16,25,28,30,33,35,39,41,48,49,50:B2,3,4,6,7,8,12,14,18,19,24"
sol407 = ['3x34', '25x23', '18x38', '30x19', '7-11', '16x18', '38-43', '49x38', '8-13', '19x8', '3x34']
trace_solution(fen407, sol407, "EX 407")

state407 = fen_to_board(fen407)
print(f"\n  Piece at sq 3: {show_piece_at(3, state407)}")
print(f"  '3x34' would need a black king at sq 3. B: FEN = black to move.")
fen407_fix = "B:W16,25,28,30,33,35,39,41,48,49,50:BK3,2,4,6,7,8,12,14,18,19,24"
trace_solution(fen407_fix, sol407, "EX 407 FIX with K3")

# Also try K3 at end of solution (3x34 appears at step 10 too)
print("\n  Checking if the LAST step also needs king at sq 3...")
