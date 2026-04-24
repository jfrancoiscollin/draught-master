from __future__ import annotations
import asyncio
import os
from typing import Optional
import anthropic
from game_engine import (
    GameState, Move, get_legal_moves, apply_move,
    WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING, EMPTY,
    board_to_fen, move_to_pdn,
)
from ai_engine import evaluate, get_best_move, rank_moves

PIECE_SYMBOLS = {
    EMPTY: '.',
    WHITE_MAN: 'b',
    WHITE_KING: 'B',
    BLACK_MAN: 'n',
    BLACK_KING: 'N',
}

SYSTEM_PROMPT = """Tu es un entraîneur expert en jeu de dames international (plateau 10x10, règles FMJD).

Règles fondamentales :
- La prise est obligatoire ; la prise maximale est obligatoire.
- Les dames se déplacent en diagonale sur toute la longueur du plateau.
- Les pièces capturées restent sur le plateau jusqu'à la fin de la séquence de prise.
- Promotion : pion blanc en cases 1-5, pion noir en cases 46-50.
- Notation PDN : "32-27" = coup simple, "32x21" = prise.

Principes d'analyse critique :
- Un sacrifice n'est justifié QUE s'il existe une combinaison forcée (suite de prises gagnante).
- Avant de recommander un sacrifice, montre EXPLICITEMENT la variante forcée qui le justifie.
- Si aucune combinaison ne justifie le sacrifice, dis clairement que le coup est une erreur.
- Ne justifie jamais mécaniquement un coup douteux : un bon joueur ne sacrifierait pas sans raison.
- Identifie les menaces réelles, les pièces en prise, les formations tactiques (triangulation, coup de barrage, etc.).

Notation de représentation : 'b'=pion blanc, 'B'=dame blanche, 'n'=pion noir, 'N'=dame noire, '.'=vide

IMPORTANT : N'utilise JAMAIS de markdown (pas de #, *, **, _, etc.).
Écris uniquement en texte brut avec des sauts de ligne simples."""


def format_board_for_claude(state: GameState) -> str:
    lines = ["Plateau (Blancs jouent vers le haut, cases 1-5 en haut) :"]
    for row in range(10):
        row_str = f"Rangée {row + 1:2d}: "
        pieces_in_row = []
        for col in range(10):
            if (row + col) % 2 != 0:
                sq_idx = row * 5 + col // 2 + 1
                p = state.board[sq_idx]
                if p != EMPTY:
                    pieces_in_row.append(f"{PIECE_SYMBOLS[p]}{sq_idx}")
        if pieces_in_row:
            row_str += " ".join(pieces_in_row)
        else:
            row_str += "(vide)"
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
    return anthropic.AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


def _piece_counts(state: GameState) -> tuple[int, int, int, int]:
    wm = wk = bm = bk = 0
    for sq in range(1, 51):
        p = state.board[sq]
        if p == WHITE_MAN: wm += 1
        elif p == WHITE_KING: wk += 1
        elif p == BLACK_MAN: bm += 1
        elif p == BLACK_KING: bk += 1
    return wm, wk, bm, bk


def _is_piece_capturable(state: GameState, sq: int) -> bool:
    """Check if the piece on sq can be captured by the opponent in the next move."""
    opponent_state = state.copy()
    opponent_state.turn = 'black' if state.turn == 'white' else 'white'
    for move in get_legal_moves(opponent_state):
        if sq in move.captures:
            return True
    return False


async def analyze_position(
    state: GameState,
    move_history: list[Move],
    user_question: Optional[str] = None,
    language: str = 'fr',
) -> dict:
    client = _get_client()

    # Run CPU-bound search in thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    ranked = await loop.run_in_executor(None, lambda: rank_moves(state, n=5, depth=5))
    top_moves_pdn = [move_to_pdn(m) for m, _ in ranked]
    top_scores = [score for _, score in ranked]

    best_move_pdn = top_moves_pdn[0] if top_moves_pdn else "aucun"
    best_score = top_scores[0] if top_scores else 0.0
    best_move_obj = ranked[0][0] if ranked else None

    current_score = evaluate(state)
    wm, wk, bm, bk = _piece_counts(state)
    turn_label = "Blancs" if state.turn == 'white' else "Noirs"
    lang_instruction = "Respond in English. No markdown." if language == 'en' \
        else "Réponds en français. Pas de markdown."

    # Detect if best move looks like a sacrifice
    sacrifice_warning = ""
    if best_move_obj and best_move_obj.captures == []:
        dest = best_move_obj.path[-1]
        after_state = apply_move(state, best_move_obj)
        if _is_piece_capturable(after_state, dest):
            score_diff = best_score - current_score
            sacrifice_warning = (
                f"\nATTENTION : Le coup {best_move_pdn} place une pièce en case {dest} "
                f"où elle peut être prise immédiatement par l'adversaire "
                f"(score moteur après coup : {best_score:+.0f} vs actuel : {current_score:+.0f}). "
                f"Vérifie s'il existe une combinaison forcée qui justifie ce sacrifice, "
                f"ou si c'est une erreur du moteur à courte profondeur."
            )

    # Build candidate list with scores
    candidates_str = ""
    for pdn, score in zip(top_moves_pdn, top_scores):
        sign = "+" if score >= 0 else ""
        candidates_str += f"  {pdn} (score moteur: {sign}{score:.0f})\n"

    board_repr = format_board_for_claude(state)
    history_repr = format_move_history(move_history)
    fen = board_to_fen(state)

    if current_score > 300:
        eval_desc = "nette avantage blanc"
    elif current_score < -300:
        eval_desc = "nette avantage noir"
    elif current_score > 80:
        eval_desc = "avantage blanc"
    elif current_score < -80:
        eval_desc = "avantage noir"
    elif current_score > 20:
        eval_desc = "légère avantage blanc"
    elif current_score < -20:
        eval_desc = "légère avantage noir"
    else:
        eval_desc = "position équilibrée"

    prompt = f"""Analyse cette position de jeu de dames international.

{board_repr}

FEN : {fen}
Trait : {turn_label}
Matériel — Blancs : {wm} pions, {wk} dames | Noirs : {bm} pions, {bk} dames
Évaluation actuelle (moteur) : {current_score:+.0f} ({eval_desc})
Nombre de coups légaux : {len(get_legal_moves(state))}
Historique : {history_repr}

Candidats classés par le moteur (profondeur 5) :
{candidates_str}{sacrifice_warning}
"""

    if user_question:
        prompt += f"\nQuestion du joueur : {user_question}\n"
    else:
        prompt += f"""
Analyse critique demandée :
1. Évalue la position générale (matériel, structure, menaces).
2. Pour le meilleur coup du moteur ({best_move_pdn}) : est-ce vraiment le bon coup ?
   - S'il s'agit d'un sacrifice, y a-t-il une combinaison forcée qui le justifie ? Montre la variante.
   - S'il n'y a pas de combinaison, indique que c'est probablement une erreur et propose le vrai meilleur coup.
3. Explique les idées stratégiques et tactiques réelles de la position.
"""

    prompt += f"\n{lang_instruction}"

    message = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    analysis_text = message.content[0].text

    return {
        "analysis": analysis_text,
        "best_moves": top_moves_pdn,
        "key_squares": [23, 24, 27, 28],
        "strategic_advice": _extract_advice(analysis_text),
    }


async def analyze_full_game(
    state: GameState,
    move_history: list[Move],
    language: str = 'fr',
) -> dict:
    client = _get_client()
    history_repr = format_move_history(move_history)
    board_repr = format_board_for_claude(state)
    wm, wk, bm, bk = _piece_counts(state)
    current_score = evaluate(state)
    lang_instruction = "Respond in English. No markdown." if language == 'en' \
        else "Réponds en français. Pas de markdown."

    if language == 'en':
        prompt = f"""Analyse this entire international draughts game from start to finish.

Full game ({len(move_history)} moves):
{history_repr}

Final position:
{board_repr}
Material — White: {wm} men, {wk} kings | Black: {bm} men, {bk} kings
Engine evaluation: {current_score:+.0f}

Provide a complete game analysis:
1. Opening phase: which moves were strong or weak? What strategy did each side adopt?
2. Middlegame: identify the key strong and weak moves. Were there important tactical or strategic errors?
3. Conclusion: what are the strengths and weaknesses of each side's strategy? Which side played better and why?

{lang_instruction}"""
    else:
        prompt = f"""Analyse l'ensemble de cette partie de jeu de dames international depuis le début.

Historique complet ({len(move_history)} coups) :
{history_repr}

Position finale :
{board_repr}
Matériel — Blancs : {wm} pions, {wk} dames | Noirs : {bm} pions, {bk} dames
Évaluation moteur : {current_score:+.0f}

Analyse complète de la partie :
1. Phase d'ouverture : quels coups ont été forts ou faibles ? Quelle stratégie chaque camp a-t-il adoptée ?
2. Milieu de jeu : identifie les coups forts et faibles des deux camps. Y a-t-il eu des erreurs importantes ?
3. Conclusion : quelles sont les forces et faiblesses de la stratégie des Blancs et des Noirs ? Quel camp a joué le mieux et pourquoi ?

{lang_instruction}"""

    message = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    analysis_text = message.content[0].text
    return {
        "analysis": analysis_text,
        "best_moves": [],
        "key_squares": [],
        "strategic_advice": _extract_advice(analysis_text),
    }


async def explain_best_move_concise(
    state: GameState,
    move_history: list[Move],
    language: str = 'fr',
) -> dict:
    client = _get_client()
    loop = asyncio.get_event_loop()
    ranked = await loop.run_in_executor(None, lambda: rank_moves(state, n=3, depth=5))

    if not ranked:
        return {"analysis": "Aucun coup légal.", "best_moves": [], "key_squares": [], "strategic_advice": ""}

    best_move_pdn = move_to_pdn(ranked[0][0])
    top_moves_pdn = [move_to_pdn(m) for m, _ in ranked]
    candidates_str = "\n".join(
        f"  {move_to_pdn(m)} (score: {'+' if s >= 0 else ''}{s:.0f})"
        for m, s in ranked
    )
    turn_label = "Whites" if state.turn == 'white' else "Blacks"
    if language != 'en':
        turn_label = "Blancs" if state.turn == 'white' else "Noirs"
    board_repr = format_board_for_claude(state)
    lang_instruction = "Respond in English. No markdown." if language == 'en' \
        else "Réponds en français. Pas de markdown."

    if language == 'en':
        prompt = f"""{turn_label} to play. Engine's best move: {best_move_pdn}
Candidates:
{candidates_str}

{board_repr}

In 2-3 sentences maximum, explain concisely WHY {best_move_pdn} is the best move. Focus only on the key tactical or strategic idea. No introduction, no general conclusion.

{lang_instruction}"""
    else:
        prompt = f"""{turn_label} au trait. Meilleur coup du moteur : {best_move_pdn}
Candidats :
{candidates_str}

{board_repr}

En 2-3 phrases maximum, explique de façon très synthétique POURQUOI {best_move_pdn} est le meilleur coup. Concentre-toi uniquement sur l'idée tactique ou stratégique essentielle. Pas d'introduction, pas de conclusion générale.

{lang_instruction}"""

    message = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    analysis_text = message.content[0].text
    return {
        "analysis": analysis_text,
        "best_moves": top_moves_pdn,
        "key_squares": [],
        "strategic_advice": analysis_text,
    }


def _extract_advice(text: str) -> str:
    for line in text.strip().split('\n'):
        if len(line) > 30:
            return line.strip()
    return text[:200].strip()


async def suggest_exercises(state: GameState) -> dict:
    client = _get_client()
    prompt = f"""Analyse cette position de jeu de dames et suggère des exercices d'entraînement :

{format_board_for_claude(state)}

FEN : {board_to_fen(state)}
Évaluation : {evaluate(state):+.0f}

Suggère 3 exercices pratiques. Pour chaque exercice : titre, objectif, difficulté (1-5), thèmes tactiques.
"""
    message = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"suggestions": message.content[0].text, "current_fen": board_to_fen(state)}
