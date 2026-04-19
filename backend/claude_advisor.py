from __future__ import annotations
import os
from typing import Optional
import anthropic
from game_engine import (
    GameState, Move, get_legal_moves,
    sq_to_rc, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING, EMPTY,
    board_to_fen, move_to_pdn,
)
from ai_engine import evaluate, get_best_move

PIECE_SYMBOLS = {
    EMPTY: '.',
    WHITE_MAN: 'b',
    WHITE_KING: 'B',
    BLACK_MAN: 'n',
    BLACK_KING: 'N',
}

SYSTEM_PROMPT = """Tu es un entraîneur expert en jeu de dames international (100 cases, règles FMJD).
Tu analyses les positions de jeu de dames international (plateau 10x10) et fournis des conseils stratégiques détaillés.

Règles importantes du jeu de dames international :
- La prise est obligatoire
- La prise maximale est obligatoire (on doit prendre le maximum de pions possible)
- Les dames se déplacent en diagonale sur toute la longueur du plateau
- Les pièces capturées restent sur le plateau jusqu'à la fin de la séquence de prise
- Promotion : un pion blanc atteignant les cases 1-5, un pion noir atteignant les cases 46-50

Notation :
- 'b' = pion blanc, 'B' = dame blanche
- 'n' = pion noir, 'N' = dame noire
- '.' = case vide
- Les cases jouables sont les cases sombres numérotées de 1 à 50

Fournis des analyses précises, concises et pédagogiques en français."""


def format_board_for_claude(state: GameState) -> str:
    lines = []
    lines.append("Plateau (vue de dessus, les Blancs jouent vers le haut) :")
    lines.append("   1  2  3  4  5  6  7  8  9  10")
    for row in range(10):
        row_str = f"{row + 1:2d} "
        for col in range(10):
            if (row + col) % 2 == 0:
                row_str += "   "
            else:
                sq_idx = row * 5 + col // 2 + 1
                piece = state.board[sq_idx]
                sym = PIECE_SYMBOLS.get(piece, '?')
                row_str += f" {sym} "
        lines.append(row_str)
    return '\n'.join(lines)


def format_move_history(moves: list[Move]) -> str:
    if not moves:
        return "Aucun coup joué."
    parts = []
    for i, move in enumerate(moves):
        move_num = i // 2 + 1
        if i % 2 == 0:
            parts.append(f"{move_num}. {move_to_pdn(move)}")
        else:
            parts[-1] += f" {move_to_pdn(move)}"
    return ' '.join(parts)


def _get_client() -> anthropic.AsyncAnthropic:
    api_key = os.getenv('ANTHROPIC_API_KEY')
    return anthropic.AsyncAnthropic(api_key=api_key)


async def analyze_position(
    state: GameState,
    move_history: list[Move],
    user_question: Optional[str] = None,
) -> dict:
    client = _get_client()
    board_repr = format_board_for_claude(state)
    history_repr = format_move_history(move_history)
    fen = board_to_fen(state)
    score = evaluate(state)
    turn_fr = "Blancs" if state.turn == 'white' else "Noirs"

    legal_moves = get_legal_moves(state)
    best = get_best_move(state, depth=4)
    best_move_str = move_to_pdn(best) if best else "aucun"

    eval_desc = "position équilibrée"
    if score > 200:
        eval_desc = "avantage blanc"
    elif score < -200:
        eval_desc = "avantage noir"
    elif score > 50:
        eval_desc = "légère avantage blanc"
    elif score < -50:
        eval_desc = "légère avantage noir"

    prompt = f"""Analyse cette position de jeu de dames international :

{board_repr}

FEN : {fen}
Trait : {turn_fr}
Évaluation : {score:.0f} ({eval_desc})
Historique des coups : {history_repr}
Nombre de coups légaux : {len(legal_moves)}
Meilleur coup suggéré : {best_move_str}
"""

    if user_question:
        prompt += f"\nQuestion du joueur : {user_question}\n"
    else:
        prompt += "\nFournis une analyse complète de la position incluant les menaces, les idées stratégiques et le plan recommandé.\n"

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    analysis_text = message.content[0].text

    top_moves = [move_to_pdn(m) for m in legal_moves[:5]]

    return {
        "analysis": analysis_text,
        "best_moves": top_moves,
        "key_squares": list(CENTER_SQUARES_LIST),
        "strategic_advice": _extract_advice(analysis_text),
    }


CENTER_SQUARES_LIST = [23, 24, 27, 28]


def _extract_advice(text: str) -> str:
    lines = text.strip().split('\n')
    for line in lines:
        if len(line) > 30:
            return line.strip()
    return text[:200].strip()


async def suggest_exercises(state: GameState) -> dict:
    client = _get_client()
    board_repr = format_board_for_claude(state)
    fen = board_to_fen(state)
    score = evaluate(state)

    prompt = f"""Analyse cette position de jeu de dames et suggère des exercices d'entraînement adaptés :

{board_repr}

FEN : {fen}
Évaluation : {score:.0f}

Suggère 3 exercices pratiques pour améliorer les compétences du joueur basés sur cette position.
Pour chaque exercice, indique :
1. Le titre de l'exercice
2. L'objectif pédagogique
3. Le niveau de difficulté (1-5)
4. Les thèmes tactiques travaillés
"""

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "suggestions": message.content[0].text,
        "current_fen": fen,
    }
