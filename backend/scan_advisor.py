"""Deterministic game analysis powered by the Scan engine.

Replaces Claude API calls for the three standard analysis modes:
  - position   (Position button)
  - best_move  (Expliquer le coup button)
  - full_game  (Partie entière button)

No LLM required. Text is generated from Scan evaluations + board features
using rule-based templates, similar to Lichess / chess.com game reports.
"""
from __future__ import annotations

import asyncio
import logging
from game_engine import (
    GameState, get_legal_moves, apply_move, board_to_fen, move_to_pdn,
    WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING, EMPTY,
)

logger = logging.getLogger(__name__)

# ── Scan evaluation ───────────────────────────────────────────────────────────

def _scan_eval_sync(state: GameState, ms: float) -> dict:
    """Call Scan synchronously. Returns {score, bestMove, pv}."""
    try:
        from scan_engine import _get_engine, _build_pos
        engine = _get_engine()
        if engine is None:
            return {"score": 0, "bestMove": None, "pv": []}
        hub_pos = _build_pos(state)
        result = engine.evaluate_pos(hub_pos, ms) or {}
        return {
            "score": result.get("score", 0),
            "bestMove": result.get("bestMove"),
            "pv": result.get("pv", []),
        }
    except Exception as exc:
        logger.warning("_scan_eval_sync failed: %s", exc)
        return {"score": 0, "bestMove": None, "pv": []}


async def _scan_eval(state: GameState, ms: float = 2.0) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _scan_eval_sync, state, ms)


# ── Board feature extraction ──────────────────────────────────────────────────

def _piece_counts(state: GameState) -> dict:
    wm = wk = bm = bk = 0
    for sq in range(1, 51):
        p = state.board[sq]
        if p == WHITE_MAN:   wm += 1
        elif p == WHITE_KING: wk += 1
        elif p == BLACK_MAN:  bm += 1
        elif p == BLACK_KING: bk += 1
    return {"wm": wm, "wk": wk, "bm": bm, "bk": bk}


def _total_pieces(c: dict) -> int:
    return c["wm"] + c["wk"] + c["bm"] + c["bk"]


def _material_value(c: dict) -> dict:
    """Kings count as 3 men equivalent."""
    w = c["wm"] + c["wk"] * 3
    b = c["bm"] + c["bk"] * 3
    return {"white": w, "black": b, "diff": w - b}


def _phase(total: int) -> str:
    if total > 35: return "opening"
    if total > 18: return "middlegame"
    return "endgame"


def _score_from_white(score: int, turn: str) -> int:
    """Scan score is side-to-move positive; convert to white-positive."""
    return score if turn == "white" else -score


def _count_captures_in_pdn(pdn_list: list[str]) -> int:
    return sum(1 for m in pdn_list if "x" in m)


def _advancement(state: GameState) -> dict:
    """Average advancement of white/black pieces (0=own back row, 1=promotion row)."""
    w_scores, b_scores = [], []
    for sq in range(1, 51):
        p = state.board[sq]
        row = (sq - 1) // 5  # 0 (top) … 9 (bottom)
        if p in (WHITE_MAN, WHITE_KING):
            # White promotes at row 0 (squares 1-5)
            w_scores.append((9 - row) / 9)
        elif p in (BLACK_MAN, BLACK_KING):
            # Black promotes at row 9 (squares 46-50)
            b_scores.append(row / 9)
    wa = sum(w_scores) / len(w_scores) if w_scores else 0
    ba = sum(b_scores) / len(b_scores) if b_scores else 0
    return {"white": wa, "black": ba}


# ── Score interpretation ──────────────────────────────────────────────────────

def _score_label(score_white: int, lang: str) -> str:
    if lang == "fr":
        if score_white >  700: return "avantage décisif pour les Blancs"
        if score_white >  280: return "avantage clair pour les Blancs"
        if score_white >   80: return "légère avantage pour les Blancs"
        if score_white >  -80: return "position équilibrée"
        if score_white > -280: return "légère avantage pour les Noirs"
        if score_white > -700: return "avantage clair pour les Noirs"
        return "avantage décisif pour les Noirs"
    else:
        if score_white >  700: return "decisive advantage for White"
        if score_white >  280: return "clear advantage for White"
        if score_white >   80: return "slight advantage for White"
        if score_white >  -80: return "equal position"
        if score_white > -280: return "slight advantage for Black"
        if score_white > -700: return "clear advantage for Black"
        return "decisive advantage for Black"


_PHASE_FR = {"opening": "Ouverture", "middlegame": "Milieu de jeu", "endgame": "Fin de partie"}
_PHASE_EN = {"opening": "Opening", "middlegame": "Middlegame", "endgame": "Endgame"}


# ── Move description ──────────────────────────────────────────────────────────

def _move_desc(move_pdn: str, state: GameState, lang: str) -> str:
    is_capture = "x" in move_pdn
    sep = "x" if is_capture else "-"
    parts = move_pdn.split(sep)
    try:
        frm = int(parts[0])
        to  = int(parts[-1])
    except (ValueError, IndexError):
        return move_pdn

    piece = state.board[frm] if 1 <= frm <= 50 else EMPTY
    is_king = piece in (WHITE_KING, BLACK_KING)
    n_cap = move_pdn.count("x")

    # Promotion check
    promotes = (
        (state.turn == "white" and to <= 5  and piece == WHITE_MAN) or
        (state.turn == "black" and to >= 46 and piece == BLACK_MAN)
    )

    # Center squares (22-29 in 10x10 board)
    center = set(range(22, 30))
    to_center = to in center

    if lang == "fr":
        if promotes:
            if is_capture:
                return f"{move_pdn} — prise avec promotion en dame !"
            return f"{move_pdn} — promotion en dame !"
        if is_capture:
            if n_cap >= 3:
                return f"{move_pdn} — rafle de {n_cap} pièces."
            if n_cap == 2:
                return f"{move_pdn} — double prise."
            return f"{move_pdn} — prise."
        if is_king:
            return f"{move_pdn} — coup de dame vers {to}."
        if to_center:
            return f"{move_pdn} — développement vers le centre."
        return f"{move_pdn} — coup de développement."
    else:
        if promotes:
            if is_capture:
                return f"{move_pdn} — capture with promotion to king!"
            return f"{move_pdn} — promotion to king!"
        if is_capture:
            if n_cap >= 3:
                return f"{move_pdn} — {n_cap}-piece multiple capture."
            if n_cap == 2:
                return f"{move_pdn} — double capture."
            return f"{move_pdn} — capture."
        if is_king:
            return f"{move_pdn} — king move to {to}."
        if to_center:
            return f"{move_pdn} — central development."
        return f"{move_pdn} — development move."


# ── Strategic advice ──────────────────────────────────────────────────────────

def _advice(phase: str, score_white: int, counts: dict, lang: str) -> str:
    has_kings = counts["wk"] > 0 or counts["bk"] > 0
    if lang == "fr":
        if phase == "opening":
            return "Développez vos pions vers le centre et maintenez une structure solide."
        if phase == "endgame":
            if has_kings:
                return "En finale avec dames, contrôlez les grandes diagonales."
            if score_white > 100:
                return "Les Blancs doivent convertir leur avantage matériel prudemment."
            if score_white < -100:
                return "Les Noirs doivent convertir leur avantage matériel prudemment."
            return "Finale très serrée — chaque coup est décisif."
        # middlegame
        if score_white > 300:
            return "Les Blancs ont l'avantage. Maintenez la pression et évitez les échanges défavorables."
        if score_white < -300:
            return "Les Noirs ont l'avantage. Maintenez la pression et évitez les échanges défavorables."
        return "Position équilibrée. Cherchez des combinaisons tactiques et contrôlez le centre."
    else:
        if phase == "opening":
            return "Develop your pieces toward the center and maintain solid structure."
        if phase == "endgame":
            if has_kings:
                return "In a king endgame, dominate the long diagonals."
            if score_white > 100:
                return "White should convert the material advantage carefully."
            if score_white < -100:
                return "Black should convert the material advantage carefully."
            return "Very tight endgame — every move is critical."
        if score_white > 300:
            return "White has the advantage. Keep the pressure and avoid unfavorable trades."
        if score_white < -300:
            return "Black has the advantage. Keep the pressure and avoid unfavorable trades."
        return "Equal position. Look for tactical combinations and control the center."


# ── Key squares helper ────────────────────────────────────────────────────────

def _key_squares(best_move: str | None) -> list[int]:
    if not best_move:
        return []
    sqs = []
    for tok in best_move.replace("x", "-").split("-"):
        try:
            sq = int(tok)
            if 1 <= sq <= 50:
                sqs.append(sq)
        except ValueError:
            pass
    return sqs[:4]


# ── PDN history formatter ─────────────────────────────────────────────────────

def _fmt_pdn(moves: list[str]) -> str:
    if not moves:
        return "Aucun coup joué." if True else "No moves."
    parts: list[str] = []
    for i, m in enumerate(moves):
        if i % 2 == 0:
            parts.append(f"{i // 2 + 1}. {m}")
        else:
            parts[-1] += f" {m}"
    return " ".join(parts)


# ── Public API — matches signatures used in main.py ──────────────────────────

async def analyze_position(
    state: GameState,
    move_history,          # list[Move] — not used here but kept for compat
    user_question: str | None = None,
    language: str = "fr",
) -> dict:
    """Deterministic position analysis (replaces claude_advisor.analyze_position)."""
    ev = await _scan_eval(state, ms=2.0)
    score      = ev["score"]
    best_move  = ev["bestMove"]
    score_w    = _score_from_white(score, state.turn)

    counts     = _piece_counts(state)
    total      = _total_pieces(counts)
    phase      = _phase(total)
    mat        = _material_value(counts)
    legal_cnt  = len(get_legal_moves(state))
    adv        = _advancement(state)

    fr = language == "fr"

    lines: list[str] = []

    if fr:
        turn_str = "Blancs" if state.turn == "white" else "Noirs"
        lines.append(f"{_PHASE_FR[phase]}. {_score_label(score_w, 'fr').capitalize()}.")
        lines.append(f"Au trait : {turn_str}. Coups légaux : {legal_cnt}.")

        # Material
        if mat["diff"] > 0:
            lines.append(f"Matériel : avantage Blancs (+{mat['diff']} en équivalent pions).")
        elif mat["diff"] < 0:
            lines.append(f"Matériel : avantage Noirs (+{-mat['diff']} en équivalent pions).")
        else:
            lines.append("Matériel équilibré.")

        # Kings
        king_parts = []
        if counts["wk"]: king_parts.append(f"{counts['wk']} dame(s) blanche(s)")
        if counts["bk"]: king_parts.append(f"{counts['bk']} dame(s) noire(s)")
        if king_parts:
            lines.append("Dames présentes : " + ", ".join(king_parts) + ".")

        # Advancement
        if phase == "middlegame":
            if adv["white"] > adv["black"] + 0.10:
                lines.append("Les Blancs sont mieux avancés vers le camp adverse.")
            elif adv["black"] > adv["white"] + 0.10:
                lines.append("Les Noirs sont mieux avancés vers le camp adverse.")

        # Best move
        if best_move:
            lines.append("")
            lines.append("Meilleur coup : " + _move_desc(best_move, state, "fr"))

        # Advice
        adv_text = _advice(phase, score_w, counts, "fr")
        lines.append("")
        lines.append("Conseil stratégique : " + adv_text)

    else:
        turn_str = "White" if state.turn == "white" else "Black"
        lines.append(f"{_PHASE_EN[phase]}. {_score_label(score_w, 'en').capitalize()}.")
        lines.append(f"To play: {turn_str}. Legal moves: {legal_cnt}.")

        if mat["diff"] > 0:
            lines.append(f"Material: White ahead (+{mat['diff']} piece-equivalent).")
        elif mat["diff"] < 0:
            lines.append(f"Material: Black ahead (+{-mat['diff']} piece-equivalent).")
        else:
            lines.append("Material is balanced.")

        king_parts = []
        if counts["wk"]: king_parts.append(f"{counts['wk']} white king(s)")
        if counts["bk"]: king_parts.append(f"{counts['bk']} black king(s)")
        if king_parts:
            lines.append("Kings on board: " + ", ".join(king_parts) + ".")

        if phase == "middlegame":
            if adv["white"] > adv["black"] + 0.10:
                lines.append("White pieces are more advanced into enemy territory.")
            elif adv["black"] > adv["white"] + 0.10:
                lines.append("Black pieces are more advanced into enemy territory.")

        if best_move:
            lines.append("")
            lines.append("Best move: " + _move_desc(best_move, state, "en"))

        adv_text = _advice(phase, score_w, counts, "en")
        lines.append("")
        lines.append("Strategic advice: " + adv_text)

    return {
        "analysis": "\n".join(lines),
        "best_moves": [best_move] if best_move else [],
        "key_squares": _key_squares(best_move),
        "strategic_advice": adv_text,
    }


async def explain_best_move_concise(
    state: GameState,
    move_history,          # kept for compat
    language: str = "fr",
    ai_depth: int = 6,     # kept for compat
) -> dict:
    """Deterministic best-move explanation (replaces claude_advisor.explain_best_move_concise)."""
    ev = await _scan_eval(state, ms=2.5)
    best_move = ev["bestMove"]
    score_w   = _score_from_white(ev["score"], state.turn)

    if not best_move:
        msg = "Aucun coup légal." if language == "fr" else "No legal moves."
        return {"analysis": msg, "best_moves": [], "key_squares": [], "strategic_advice": ""}

    counts = _piece_counts(state)
    phase  = _phase(_total_pieces(counts))
    fr     = language == "fr"

    desc    = _move_desc(best_move, state, language)
    score_s = _score_label(score_w, language)

    if fr:
        turn_s   = "Blancs" if state.turn == "white" else "Noirs"
        phase_s  = _PHASE_FR[phase]
        lines = [
            f"{turn_s} au trait. {phase_s}.",
            f"Meilleur coup du moteur : {desc}",
            f"Évaluation après ce coup : {score_s}.",
        ]
    else:
        turn_s  = "White" if state.turn == "white" else "Black"
        phase_s = _PHASE_EN[phase]
        lines = [
            f"{turn_s} to play. {phase_s}.",
            f"Engine's best move: {desc}",
            f"Evaluation after this move: {score_s}.",
        ]

    adv_text = _advice(phase, score_w, counts, language)
    analysis = "\n".join(lines)

    return {
        "analysis": analysis,
        "best_moves": [best_move],
        "key_squares": _key_squares(best_move),
        "strategic_advice": adv_text,
    }


async def analyze_full_game(
    state: GameState,
    move_history,          # list[Move]
    language: str = "fr",
) -> dict:
    """Deterministic full-game summary (replaces claude_advisor.analyze_full_game)."""
    pdn_list = [move_to_pdn(m) if not isinstance(m, str) else m for m in move_history]
    return await _full_game_common(state, pdn_list, language)


async def analyze_full_game_pdn(
    state: GameState,
    pdn_history: list[str],
    language: str = "fr",
) -> dict:
    """Deterministic full-game summary (replaces claude_advisor.analyze_full_game_pdn)."""
    return await _full_game_common(state, pdn_history, language)


async def _full_game_common(
    state: GameState,
    pdn_list: list[str],
    language: str,
) -> dict:
    ev        = await _scan_eval(state, ms=1.5)
    score_w   = _score_from_white(ev["score"], state.turn)
    counts    = _piece_counts(state)
    total     = _total_pieces(counts)
    phase     = _phase(total)
    n_moves   = len(pdn_list)
    n_cap     = _count_captures_in_pdn(pdn_list)
    mat       = _material_value(counts)
    fr        = language == "fr"

    # Opening summary: first 10 moves
    opening_pdns = pdn_list[:10]
    opening_str  = _fmt_pdn(opening_pdns)

    score_s  = _score_label(score_w, language)
    adv_text = _advice(phase, score_w, counts, language)

    if fr:
        phase_final = _PHASE_FR[phase]
        lines = [
            f"Partie en {n_moves} coups ({n_cap} prise{'s' if n_cap != 1 else ''} au total).",
            "",
            f"Ouverture (10 premiers coups) : {opening_str}",
            "",
            "Position finale :",
            f"  Évaluation moteur : {score_s}. {phase_final}.",
        ]

        if mat["diff"] > 0:
            lines.append(f"  Matériel : avantage Blancs (+{mat['diff']}).")
        elif mat["diff"] < 0:
            lines.append(f"  Matériel : avantage Noirs (+{-mat['diff']}).")
        else:
            lines.append("  Matériel équilibré.")

        king_parts = []
        if counts["wk"]: king_parts.append(f"{counts['wk']} dame(s) blanche(s)")
        if counts["bk"]: king_parts.append(f"{counts['bk']} dame(s) noire(s)")
        if king_parts:
            lines.append("  Dames : " + ", ".join(king_parts) + ".")

        lines.append("")
        if score_w > 300:
            lines.append("Les Blancs ont mené la partie et maintenu leur avantage.")
        elif score_w < -300:
            lines.append("Les Noirs ont mené la partie et maintenu leur avantage.")
        elif score_w > 80:
            lines.append("Légère domination des Blancs en fin de partie.")
        elif score_w < -80:
            lines.append("Légère domination des Noirs en fin de partie.")
        else:
            lines.append("Partie très équilibrée des deux côtés.")

        if n_cap > n_moves * 0.6:
            lines.append("Partie très tactique avec de nombreux échanges.")
        elif n_cap < n_moves * 0.2:
            lines.append("Partie positionnelle avec peu d'échanges.")

        lines.append("")
        lines.append("Conseil : " + adv_text)

    else:
        phase_final = _PHASE_EN[phase]
        lines = [
            f"Game lasted {n_moves} moves ({n_cap} capture{'s' if n_cap != 1 else ''} total).",
            "",
            f"Opening ({min(10, n_moves)} moves): {opening_str}",
            "",
            "Final position:",
            f"  Engine evaluation: {score_s}. {phase_final}.",
        ]

        if mat["diff"] > 0:
            lines.append(f"  Material: White ahead (+{mat['diff']}).")
        elif mat["diff"] < 0:
            lines.append(f"  Material: Black ahead (+{-mat['diff']}).")
        else:
            lines.append("  Material balanced.")

        king_parts = []
        if counts["wk"]: king_parts.append(f"{counts['wk']} white king(s)")
        if counts["bk"]: king_parts.append(f"{counts['bk']} black king(s)")
        if king_parts:
            lines.append("  Kings: " + ", ".join(king_parts) + ".")

        lines.append("")
        if score_w > 300:
            lines.append("White dominated the game and maintained their advantage.")
        elif score_w < -300:
            lines.append("Black dominated the game and maintained their advantage.")
        else:
            lines.append("A well-balanced game on both sides.")

        if n_cap > n_moves * 0.6:
            lines.append("Very tactical game with many exchanges.")
        elif n_cap < n_moves * 0.2:
            lines.append("Positional game with few exchanges.")

        lines.append("")
        lines.append("Advice: " + adv_text)

    return {
        "analysis": "\n".join(lines),
        "best_moves": [],
        "key_squares": [],
        "strategic_advice": adv_text,
    }
