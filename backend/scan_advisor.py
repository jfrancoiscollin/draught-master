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
import json
import logging
import math
import os
from game_engine import (
    GameState, get_legal_moves, apply_move, board_to_fen, move_to_pdn,
    WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING, EMPTY,
    initial_state as _initial_state,
)

logger = logging.getLogger(__name__)

# ── Knowledge base ────────────────────────────────────────────────────────────

_KB: list[dict] | None = None

def _load_kb() -> list[dict]:
    """Lazy-load knowledge_base.json. Returns an empty list if the file is missing."""
    global _KB
    if _KB is None:
        kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
        try:
            with open(kb_path, encoding="utf-8") as f:
                _KB = json.load(f)["tips"]
        except Exception as exc:
            logger.warning("knowledge_base.json not loaded: %s", exc)
            _KB = []
    return _KB


def _board_features(state: GameState, counts: dict, phase: str,
                    pdn_list: list[str], best_move: str | None,
                    legal_cnt: int = 0) -> set[str]:
    """Extract boolean features from the position for knowledge-base matching."""
    b = state.board
    feats: set[str] = set()

    # ── Square presences ──────────────────────────────────────────────────────
    W = (WHITE_MAN, WHITE_KING)
    BL = (BLACK_MAN, BLACK_KING)

    # White squares
    for sq, tag in [(23, "white_on_23"), (25, "white_on_25"), (27, "white_on_27"),
                    (28, "white_on_28"), (29, "white_on_29"), (35, "white_on_35"),
                    (36, "white_on_36"), (45, "white_on_45"), (46, "white_on_46"),
                    (47, "white_on_47")]:
        if b[sq] in W: feats.add(tag)

    # Black squares
    for sq, tag in [(6, "black_on_6"), (15, "black_on_15"), (16, "black_on_16"),
                    (21, "black_on_21"), (22, "black_on_22"), (23, "black_on_23"),
                    (24, "black_on_24"), (26, "black_on_26")]:
        if b[sq] in BL: feats.add(tag)

    # ── Formations ────────────────────────────────────────────────────────────
    # Marchand de bois core (27-32-38)
    if b[27] in W and b[32] in W and b[38] in W:
        feats.add("white_on_32")
        feats.add("white_on_38")

    # Formation 45-40
    if b[45] in W and b[40] in W:
        feats.add("formation_45_40")

    # Flèche 33-38-42
    if b[33] in W and b[38] in W:
        feats.add("formation_33_38")

    # Formation 34-39-43
    if b[34] in W and b[39] in W:
        feats.add("formation_34_39")

    # Piquet canadien: black on 23 without white support nearby
    if b[23] in BL and b[28] not in W:
        feats.add("piquet_canadien")

    # ── Tactical richness ─────────────────────────────────────────────────────
    n_moves = len(pdn_list)
    n_cap = _count_captures_in_pdn(pdn_list)
    if n_moves > 4 and n_cap / max(n_moves, 1) > 0.25:
        feats.add("many_captures")
    if best_move and ("x" in best_move or "×" in best_move):
        feats.add("capture_possible")

    # Promotion possible for active side
    if best_move:
        try:
            dest = int(best_move.split("x")[-1].split("-")[-1])
            if state.turn == "white" and dest <= 5:
                feats.add("promotion_possible")
            elif state.turn == "black" and dest >= 46:
                feats.add("promotion_possible")
        except Exception:
            pass

    # ── Piece advancement ─────────────────────────────────────────────────────
    # White pawns close to promotion (rows 2-3, squares 6-15)
    if any(b[sq] == WHITE_MAN for sq in range(6, 16)):
        feats.add("pion_avance_blanc")
    # Black pawns close to promotion (rows 7-8, squares 36-45)
    if any(b[sq] == BLACK_MAN for sq in range(36, 46)):
        feats.add("pion_avance_noir")

    # ── Wing imbalance ────────────────────────────────────────────────────────
    left_w  = sum(1 for sq in [31, 32, 36, 37, 41, 42, 46, 47] if b[sq] in W)
    right_w = sum(1 for sq in [33, 34, 38, 39, 43, 44, 48, 49] if b[sq] in W)
    if abs(left_w - right_w) >= 3:
        feats.add("wing_imbalance")

    # ── Tempo advantage (opening/middlegame) ──────────────────────────────────
    if phase in ("opening", "middlegame"):
        w_adv = sum(1 for sq in range(1, 51) if b[sq] in W
                    for _ in [1] if (10 - (sq - 1) // 5) >= 7)
        b_adv = sum(1 for sq in range(1, 51) if b[sq] in BL
                    for _ in [1] if ((sq - 1) // 5 + 1) >= 7)
        if w_adv > b_adv + 2 or b_adv > w_adv + 2:
            feats.add("tempo_advantage")

    # ── Restricted side ───────────────────────────────────────────────────────
    if legal_cnt <= 3 and legal_cnt > 0:
        feats.add("restricted_side")

    # ── Endgame patterns ──────────────────────────────────────────────────────
    total = _total_pieces(counts)
    if phase == "endgame":
        feats.add("few_pieces")
        if counts["wk"] > 0 or counts["bk"] > 0:
            feats.add("kings_present")

        # King vs pawns
        if counts["wk"] >= 1 and counts["bk"] == 0 and counts["bm"] <= 3:
            feats.add("king_vs_pawns")
        if counts["bk"] >= 1 and counts["wk"] == 0 and counts["wm"] <= 3:
            feats.add("king_vs_pawns")

        # 1 king vs 2 pawns
        if ((counts["wk"] == 1 and counts["wm"] == 0 and counts["bm"] == 2 and counts["bk"] == 0) or
                (counts["bk"] == 1 and counts["bm"] == 0 and counts["wm"] == 2 and counts["wk"] == 0)):
            feats.add("dame_vs_two_pawns")

        # King+pawn vs 2 pawns
        if ((counts["wk"] == 1 and counts["wm"] == 1 and counts["bm"] == 2 and counts["bk"] == 0) or
                (counts["bk"] == 1 and counts["bm"] == 1 and counts["wm"] == 2 and counts["wk"] == 0)):
            feats.add("dame_pion_vs_deux")

        # King+pawn vs 3 pawns
        if ((counts["wk"] == 1 and counts["wm"] >= 1 and counts["bm"] == 3 and counts["bk"] == 0) or
                (counts["bk"] == 1 and counts["bm"] >= 1 and counts["wm"] == 3 and counts["wk"] == 0)):
            feats.add("dame_pion_vs_trois")

        # Pure pawn endgame
        if counts["wk"] == 0 and counts["bk"] == 0 and counts["wm"] > 0 and counts["bm"] > 0:
            feats.add("pions_vs_pions")

        # Corner pieces
        corner_sqs = {1, 5, 46, 50}
        if any(b[sq] != EMPTY for sq in corner_sqs):
            feats.add("piece_in_corner")

        # Equal endgame
        mat = _material_value(counts)
        if abs(mat["diff"]) <= 1 and total <= 8:
            feats.add("equal_endgame")

    # ── Middlegame features ───────────────────────────────────────────────────
    if phase == "middlegame":
        mat = _material_value(counts)
        if abs(mat["diff"]) <= 1:
            feats.add("balanced_material")
        contacts = sum(1 for sq in range(16, 36) if b[sq] != EMPTY)
        if contacts >= 10:
            feats.add("many_contacts")

    # Opening general
    if phase == "opening":
        feats.add("opening_general")

    return feats


def _select_book_tip(state: GameState, counts: dict, phase: str,
                     pdn_list: list[str], best_move: str | None,
                     lang: str, legal_cnt: int = 0) -> dict | None:
    """Return the best matching knowledge-base tip for the current position."""
    tips = _load_kb()
    feats = _board_features(state, counts, phase, pdn_list, best_move, legal_cnt)

    for tip in tips:
        # Phase filter
        if phase not in tip.get("phase", []):
            continue
        # Condition matching
        conds = tip.get("conditions", [])
        require_all = tip.get("require_all", False)
        if require_all:
            if not all(c in feats for c in conds):
                continue
        else:
            if not any(c in feats for c in conds):
                continue
        # Return localised version
        loc = tip.get(lang) or tip.get("fr") or {}
        return loc

    return None

# ── Scan evaluation ───────────────────────────────────────────────────────────

def _scan_eval_sync(state: GameState, ms: float) -> dict:
    """Call Scan synchronously. Returns {score, bestMove, pv}."""
    try:
        from scan_engine import _get_engine, _build_pos
        engine = _get_engine(use_book=False)
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
    """Return {wm, wk, bm, bk} piece counts for the current position."""
    wm = wk = bm = bk = 0
    for sq in range(1, 51):
        p = state.board[sq]
        if p == WHITE_MAN:   wm += 1
        elif p == WHITE_KING: wk += 1
        elif p == BLACK_MAN:  bm += 1
        elif p == BLACK_KING: bk += 1
    return {"wm": wm, "wk": wk, "bm": bm, "bk": bk}


def _total_pieces(c: dict) -> int:
    """Sum all pieces on the board from a counts dict."""
    return c["wm"] + c["wk"] + c["bm"] + c["bk"]


def _material_value(c: dict) -> dict:
    """Kings count as 3 men equivalent."""
    w = c["wm"] + c["wk"] * 3
    b = c["bm"] + c["bk"] * 3
    return {"white": w, "black": b, "diff": w - b}


def _phase(total: int) -> str:
    """Classify game phase from total piece count: opening > 35, endgame ≤ 18."""
    if total > 35: return "opening"
    if total > 18: return "middlegame"
    return "endgame"


def _score_from_white(score: float, turn: str) -> float:
    """Scan score is side-to-move positive; convert to white-positive."""
    return score if turn == "white" else -score


def _count_captures_in_pdn(pdn_list: list[str]) -> int:
    """Count how many PDN move strings contain a capture (contain 'x')."""
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

def _score_label(score_white: float, lang: str) -> str:
    """Convert a white-perspective score (in centipawns) to a human-readable label."""
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
    """Build a natural-language description of a PDN move (e.g. 'double capture', 'promotion')."""
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

def _advice(phase: str, score_white: float, counts: dict, lang: str) -> str:
    """Return a one-sentence strategic tip tailored to phase, score, and material balance."""
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
    """Extract up to 4 square numbers from a PDN move string for board highlighting."""
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
    """Format a flat move list as '1. 32-28 17-21 2. ...' for display."""
    if not moves:
        return "Aucun coup joué." if True else "No moves."
    parts: list[str] = []
    for i, m in enumerate(moves):
        if i % 2 == 0:
            parts.append(f"{i // 2 + 1}. {m}")
        else:
            parts[-1] += f" {m}"
    return " ".join(parts)


# ── Move-by-move annotation ───────────────────────────────────────────────────

def _win_chance(cp: float) -> float:
    """Sigmoid mapping from Scan score (side-to-move, in piece units) to win probability shift.
    k=2.0 calibrated for Scan's piece-unit scale where 1.0 ≈ one-piece advantage."""
    return 2 / (1 + math.exp(-2.0 * cp)) - 1


def _annotate_game_moves_sync(
    move_history: list,   # list[Move]
    language: str,
    ms_per_move: float = 300,
) -> list[dict]:
    """Replay game move-by-move and annotate each with Scan evaluation.

    Returns a list of annotation dicts, one per move. Only blunders / mistakes /
    inaccuracies receive a knowledge-base tip; other moves have book_tip=None.
    """
    try:
        from scan_engine import _get_engine, _build_pos
        from opening_book_db import lookup as _cached_lookup
    except ImportError:
        return []

    engine = _get_engine(use_book=False)
    if engine is None:
        return []

    n = len(move_history)
    if n == 0:
        return []

    # Adaptive timing: keep total ≤ 20 s regardless of game length
    budget_ms = 20_000.0
    ms_each = min(ms_per_move, budget_ms / max(n + 1, 1))

    def _eval_pos(st: GameState) -> dict:
        fen = board_to_fen(st)
        hit = _cached_lookup(fen)
        if hit:
            return {"score": hit["score"], "bestMove": hit["bestMove"]}
        try:
            hub = _build_pos(st)
            res = engine.evaluate_pos(hub, ms_each / 1000.0) or {}
            return {"score": res.get("score", 0), "bestMove": res.get("bestMove")}
        except Exception:
            return {"score": 0, "bestMove": None}

    state = _initial_state()
    ev_before = _eval_pos(state)
    score_before = ev_before["score"]
    best_move_before = ev_before["bestMove"]

    annotations: list[dict] = []

    for i, move in enumerate(move_history):
        if isinstance(move, str):
            break  # can't replay PDN-only history

        move_pdn_str = move_to_pdn(move)
        try:
            state_after = apply_move(state, move)
        except Exception:
            break

        ev_after = _eval_pos(state_after)
        score_after = ev_after["score"]

        # rawLoss: both scores from side-to-move perspective in piece units;
        # positive sum means the mover lost ground. Convert ×100 for cp display.
        raw_loss = score_before + score_after
        loss_cp = min(1000, max(0, round(raw_loss * 100)))

        dwc = _win_chance(score_before) + _win_chance(score_after)
        delta = max(0.0, dwc)

        if delta >= 0.30:
            verdict = "blunder"
        elif delta >= 0.15:
            verdict = "mistake"
        elif delta >= 0.075:
            verdict = "inaccuracy"
        else:
            verdict = None

        color = "white" if i % 2 == 0 else "black"
        move_number = i // 2 + 1

        book_tip = None
        if verdict in ("blunder", "mistake"):
            counts_b = _piece_counts(state)
            phase_b  = _phase(_total_pieces(counts_b))
            legal_cnt = len(get_legal_moves(state_after))
            tip = _select_book_tip(state, counts_b, phase_b, [], best_move_before, language, legal_cnt)
            if tip:
                book_tip = {"concept": tip.get("concept", ""), "source": tip.get("source", "")}

        annotations.append({
            "move_number": move_number,
            "color": color,
            "move_pdn": move_pdn_str,
            "verdict": verdict,
            "score_before": score_before,
            "score_after": score_after,
            "loss_cp": loss_cp,
            "best_move": best_move_before,
            "book_tip": book_tip,
        })

        state = state_after
        score_before = score_after
        best_move_before = ev_after["bestMove"]

    return annotations


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

    # ── Book tip ──────────────────────────────────────────────────────────────
    pdn_list = [move_to_pdn(m) if not isinstance(m, str) else m
                for m in (move_history or [])]
    tip = _select_book_tip(state, counts, phase, pdn_list, best_move, language, legal_cnt)
    if tip:
        sep = "\n\n─────────────────────"
        fr = language == "fr"
        label = "📚 À approfondir" if fr else "📚 Further reading"
        lines.append(sep)
        lines.append(f"{label} — {tip['concept']}")
        lines.append(tip["text"])
        lines.append(f"→ {tip['source']}")

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

    tip = _select_book_tip(state, counts, phase, [], best_move, language)
    if tip:
        fr = language == "fr"
        label = "📚 À approfondir" if fr else "📚 Further reading"
        lines.append("")
        lines.append("─────────────────────")
        lines.append(f"{label} — {tip['concept']}")
        lines.append(tip["text"])
        lines.append(f"→ {tip['source']}")

    return {
        "analysis": "\n".join(lines),
        "best_moves": [best_move],
        "key_squares": _key_squares(best_move),
        "strategic_advice": adv_text,
    }


async def analyze_full_game(
    state: GameState,
    move_history,          # list[Move]
    language: str = "fr",
) -> dict:
    """Deterministic full-game summary with move-by-move annotations."""
    pdn_list = [move_to_pdn(m) if not isinstance(m, str) else m for m in move_history]
    result = await _full_game_common(state, pdn_list, language)

    # Move-by-move annotation — run in thread executor to avoid blocking
    if move_history and not isinstance(move_history[0], str):
        loop = asyncio.get_event_loop()
        n = len(move_history)
        ms_each = 200.0 if n > 40 else 300.0
        move_annotations = await loop.run_in_executor(
            None, _annotate_game_moves_sync, list(move_history), language, ms_each
        )
        result["move_annotations"] = move_annotations

    return result


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

    # ── Book tip ──────────────────────────────────────────────────────────────
    tip = _select_book_tip(state, counts, phase, pdn_list, None, language)
    if tip:
        fr = language == "fr"
        label = "📚 À approfondir" if fr else "📚 Further reading"
        lines.append("")
        lines.append("─────────────────────")
        lines.append(f"{label} — {tip['concept']}")
        lines.append(tip["text"])
        lines.append(f"→ {tip['source']}")

    return {
        "analysis": "\n".join(lines),
        "best_moves": [],
        "key_squares": [],
        "strategic_advice": adv_text,
    }
