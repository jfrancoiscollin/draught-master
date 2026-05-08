"""
Test chaque exercice en simulant exactement la logique de l'application
(check_exercise + exercise_legal_moves_endpoint de main.py).
"""
import sys, re
sys.path.insert(0, '/home/user/Ai-draught')
from backend.game_engine import fen_to_board, get_legal_moves, move_to_pdn, apply_move, GameState
from typing import List, Optional

# --- Réplication exacte des helpers de main.py ---

def find_move_by_pdn(pdn: str, legal_moves):
    """Même logique que _find_move_by_pdn dans main.py."""
    pdn_norm = pdn.strip()
    for move in legal_moves:
        if move_to_pdn(move) == pdn_norm:
            return move
    try:
        if 'x' in pdn_norm:
            parts = [int(p) for p in pdn_norm.split('x') if p]
        elif '-' in pdn_norm:
            parts = [int(p) for p in pdn_norm.split('-') if p]
        else:
            return None
        start, end = parts[0], parts[-1]
    except (ValueError, IndexError):
        return None
    for move in legal_moves:
        if move.path[0] == start and move.path[-1] == end:
            return move
    return None

def reconstruct_state(initial_fen: str, solution: List, move_count: int):
    """Même logique que _reconstruct_state dans main.py."""
    state = fen_to_board(initial_fen)
    for i in range(move_count):
        if i >= len(solution) or solution[i] is None:
            break
        legal = get_legal_moves(state)
        move = find_move_by_pdn(solution[i], legal)
        if move is None:
            return None
        state = apply_move(state, move)
    return state

def moves_match(submitted: str, expected: str) -> bool:
    """Même logique que _moves_match dans main.py."""
    s = submitted.strip().lstrip('K')
    e = expected.strip().lstrip('K')
    if s == e:
        return True
    def parse(pdn):
        try:
            if 'x' in pdn:
                parts = [int(p) for p in pdn.split('x') if p]
            elif '-' in pdn:
                parts = [int(p) for p in pdn.split('-') if p]
            else:
                return None, None
            return parts[0], parts[-1]
        except:
            return None, None
    ss, se = parse(s)
    es, ee = parse(e)
    return ss is not None and ss == es and se == ee

# --- Test principal ---

def test_exercise(ex, ex_id):
    """
    Simule l'exercice complet : coups blancs (utilisateur) et coups noirs (auto).
    Retourne (status, details) où status = 'OK' | 'BROKEN_WHITE' | 'BROKEN_BLACK' | 'FREE_MODE'
    """
    solution = ex['solution_moves']
    fen = ex['initial_fen']
    issues = []

    for step in range(len(solution)):
        pdn = solution[step]
        is_white = (step % 2 == 0)

        if pdn is None:
            # None : l'app ignore ce coup (continuation libre)
            issues.append(f"step {step}: None (coup manquant, mode libre)")
            continue

        # Reconstruire l'état après `step` coups
        state = reconstruct_state(fen, solution, step)
        if state is None:
            issues.append(f"step {step} ({'blanc' if is_white else 'noir'}): reconstruction impossible → '{pdn}'")
            # L'app entre en mode libre (free-move) après step>0
            break

        legal = get_legal_moves(state)
        m = find_move_by_pdn(pdn, legal)

        if m is None:
            legal_str = [move_to_pdn(x) for x in legal]
            if is_white:
                issues.append(f"step {step} (blanc/utilisateur): '{pdn}' introuvable. Légaux: {legal_str[:5]}")
            else:
                # Fallback de l'app : cherche capture depuis même case départ
                fallback = None
                if 'x' in pdn:
                    try:
                        sq = int(pdn.split('x')[0])
                        fallback = next((x for x in legal if x.path[0]==sq and x.captures), None)
                    except:
                        pass
                if fallback:
                    issues.append(f"step {step} (noir/auto): '{pdn}' → fallback '{move_to_pdn(fallback)}'")
                else:
                    issues.append(f"step {step} (noir/auto): '{pdn}' introuvable. Légaux: {legal_str[:5]}")

    if not issues:
        return 'OK', []
    # Determine severity
    severe = [i for i in issues if 'blanc/utilisateur' in i or ('reconstruction impossible' in i)]
    if severe:
        return 'BROKEN', issues
    return 'WARN', issues  # noir/auto problème ou None

# --- Chargement des exercices ---
content = open('backend/database.py').read()
start = content.index('INITIAL_EXERCISES = [')
depth = 0
i = start + len('INITIAL_EXERCISES = ')
for j in range(i, len(content)):
    if content[j] == '[': depth += 1
    elif content[j] == ']':
        depth -= 1
        if depth == 0:
            block_end = j + 1; break
exercises = eval(content[start:block_end].replace('INITIAL_EXERCISES = ', ''))

# --- Exécution ---
broken, warn, ok = [], [], []
for idx, ex in enumerate(exercises):
    if not ex.get('initial_fen') or not ex.get('solution_moves'):
        continue
    status, issues = test_exercise(ex, idx)
    if status == 'OK':
        ok.append(idx)
    elif status == 'WARN':
        warn.append((idx, ex['name'], issues))
    else:
        broken.append((idx, ex['name'], issues))

print(f"=== RÉSULTATS ===")
print(f"OK      : {len(ok)}")
print(f"WARN    : {len(warn)}  (auto-play noir échoue, blanc OK)")
print(f"BROKEN  : {len(broken)}  (l'utilisateur est bloqué)")

print(f"\n=== BROKEN (utilisateur bloqué) ===")
for idx, name, issues in broken:
    print(f"\n[{idx}] {name}")
    for i in issues:
        print(f"  • {i}")

print(f"\n=== WARN (auto-play noir imparfait) ===")
for idx, name, issues in warn:
    print(f"[{idx}] {name}: {issues[0]}")
