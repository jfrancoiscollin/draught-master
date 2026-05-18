"""FastAPI router for the pedagogy layer (spec §9)."""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import asdict
from typing import Any, Optional

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Request

from pedagogy.explanations import explain_verdict
from pedagogy.profile.aggregator import aggregate_user_profile, _MOTIF_THRESHOLD
from pedagogy.profile.recommender import recommend_exercises

try:
    from auth import current_user  # absolute when backend/ is on sys.path
except ImportError:
    from ..auth import current_user  # type: ignore[assignment]
from . import storage
from .models import (
    AnalyzeGameRequest,
    AnalyzeGameResponse,
    ExplainMoveRequest,
    ExplainMoveResponse,
    MotifExerciseOut,
    MotifInfoOut,
    MotifMatchOut,
    MoveVerdictOut,
    RecommendationsResponse,
    SquareWeaknessCounts,
    UserProfileOut,
    WeaknessHeatmapOut,
)
from .motif_descriptions import get_motif as _get_motif_desc

router = APIRouter(prefix="/api/pedagogy", tags=["pedagogy"])

# Rate limiters for /explain-move. claude burns API tokens so it gets 5/min;
# template is free but capped at 60/min per IP for courtesy (spec §14.6).
# Built lazily because importing _make_limiter at module load creates a
# circular import via main.py -> pedagogy.api -> main.
_claude_limiter = None
_template_limiter = None


def _ensure_explain_limiters() -> None:
    global _claude_limiter, _template_limiter
    if _claude_limiter is not None:
        return
    try:
        from main import _make_limiter  # noqa: PLC0415
    except ImportError:
        from ..main import _make_limiter  # type: ignore[assignment]  # noqa: PLC0415
    _claude_limiter = _make_limiter(max_calls=5, window=60)
    _template_limiter = _make_limiter(max_calls=60, window=60)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _threats_to_payload(items: Any) -> list[dict[str, list[int]]]:
    """Coerce ``items`` (list of ThreatenedCapture or dicts) to JSONable."""
    out: list[dict[str, list[int]]] = []
    for it in items or []:
        path = getattr(it, "path", None)
        captures = getattr(it, "captures", None)
        if path is None and isinstance(it, dict):
            path = it.get("path")
            captures = it.get("captures")
        out.append({
            "path": [int(x) for x in (path or ())],
            "captures": [int(x) for x in (captures or ())],
        })
    return out


def _verdict_to_out(v: Any) -> MoveVerdictOut:
    feats_after = getattr(v, "features_after", None)
    return MoveVerdictOut(
        move_number=v.move_number,
        side=v.side,
        move_notation=v.move_notation,
        fen_before=v.fen_before,
        fen_after=v.fen_after,
        score_before=v.score_before,
        score_after=v.score_after,
        delta_winchance=v.delta_winchance,
        verdict=v.verdict.value if hasattr(v.verdict, "value") else v.verdict,
        is_forced=v.is_forced,
        phase=v.phase.value if hasattr(v.phase, "value") else v.phase,
        motifs=[MotifMatchOut(**asdict(m)) for m in v.motifs],
        material_balance=getattr(feats_after, "material_balance", None),
        hanging_pieces_white=list(getattr(feats_after, "hanging_pieces_white", []) or []),
        hanging_pieces_black=list(getattr(feats_after, "hanging_pieces_black", []) or []),
        isolated_pawns_white=list(getattr(feats_after, "isolated_pawns_white", []) or []),
        isolated_pawns_black=list(getattr(feats_after, "isolated_pawns_black", []) or []),
        backward_pawns_white=list(getattr(feats_after, "backward_pawns_white", []) or []),
        backward_pawns_black=list(getattr(feats_after, "backward_pawns_black", []) or []),
        holes_white=list(getattr(feats_after, "holes_white", []) or []),
        holes_black=list(getattr(feats_after, "holes_black", []) or []),
        outposts_white=list(getattr(feats_after, "outposts_white", []) or []),
        outposts_black=list(getattr(feats_after, "outposts_black", []) or []),
        formations=list(getattr(feats_after, "formations", []) or []),
        threatened_captures_white=_threats_to_payload(
            getattr(feats_after, "threatened_captures_white", [])
        ),
        threatened_captures_black=_threats_to_payload(
            getattr(feats_after, "threatened_captures_black", [])
        ),
    )


def _db_path() -> str:
    try:
        from db.config import DB_PATH  # absolute (backend/ on sys.path)
        return DB_PATH
    except ImportError:
        from ..db.config import DB_PATH  # type: ignore[assignment]
        return DB_PATH


def _parse_pdn_moves(pdn: str) -> list[str]:
    """Extract the ordered list of move tokens from a PDN string.

    Strips headers ([...]), move numbers (1. 2. ...) and result tokens,
    then returns the remaining '-' / 'x' notation tokens.
    """
    # Remove header tags
    pdn = re.sub(r'\[[^\]]*\]', '', pdn)
    # Remove move numbers like "1." "12."
    pdn = re.sub(r'\b\d+\.', '', pdn)
    tokens = pdn.split()
    moves: list[str] = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        # Skip result markers and bare numbers
        if t in ('1-0', '0-1', '1/2-1/2', '*'):
            continue
        if re.fullmatch(r'\d+', t):
            continue
        # Valid move token contains '-' or 'x'
        if '-' in t or 'x' in t:
            # Strip optional leading king prefix 'K' used in some PDN dialects
            moves.append(t.lstrip('K'))
    return moves


# ---------------------------------------------------------------------------
# POST /api/pedagogy/analyze-game
# ---------------------------------------------------------------------------


@router.post("/analyze-game", response_model=AnalyzeGameResponse)
async def analyze_game(
    req: AnalyzeGameRequest,
    user: Any = Depends(current_user),
) -> AnalyzeGameResponse:
    """Run dilf's assemble_verdict on every half-move of a game.

    Accepts either a game_id (looked up from the games table) or a raw PDN
    string. Evaluates every position with the Scan engine (200 ms/pos),
    assembles a MoveVerdict per half-move, persists the analysis, and
    returns the full verdict list plus a summary.
    """
    from game_engine import (
        apply_move as ge_apply,
        get_legal_moves as ge_legal,
        initial_state as ge_initial,
    )
    from pedagogy.types import GameAnalysis
    from pedagogy.verdicts.assembler import assemble_verdict
    from scan_advisor import _scan_eval_sync

    from .engine_adapter import GameEngineAdapter, ge_move_to_dilf, ge_state_to_dilf

    # ------------------------------------------------------------------
    # 1. Retrieve PDN text
    # ------------------------------------------------------------------
    if req.game_id is None and not req.pdn:
        raise HTTPException(422, "game_id or pdn is required")

    if req.game_id:
        async with aiosqlite.connect(_db_path()) as conn:
            cur = await conn.execute(
                "SELECT pdn FROM games WHERE id = ?", (req.game_id,)
            )
            row = await cur.fetchone()
        if row is None:
            raise HTTPException(404, f"Game {req.game_id!r} not found")
        pdn_str = row[0] or ""
    else:
        pdn_str = req.pdn or ""

    if not pdn_str.strip():
        raise HTTPException(422, "PDN content is empty")

    # ------------------------------------------------------------------
    # 2. Parse move tokens
    # ------------------------------------------------------------------
    move_tokens = _parse_pdn_moves(pdn_str)
    if not move_tokens:
        raise HTTPException(422, "No moves found in PDN")

    # ------------------------------------------------------------------
    # 3. Replay moves through game_engine
    # ------------------------------------------------------------------
    try:
        from main import _find_move_by_pdn  # noqa: PLC0415
    except ImportError:
        from ..main import _find_move_by_pdn  # type: ignore[assignment]  # noqa: PLC0415

    ge_state = ge_initial()
    ge_states = [ge_state]
    ge_moves_played = []

    for token in move_tokens:
        legal = ge_legal(ge_state)
        move = _find_move_by_pdn(token, legal)
        if move is None:
            break  # stop at first unrecognised token (e.g. result in PDN body)
        ge_state = ge_apply(ge_state, move)
        ge_moves_played.append(move)
        ge_states.append(ge_state)

    n_moves = len(ge_moves_played)
    if n_moves == 0:
        raise HTTPException(422, "Could not replay any moves from PDN")

    # ------------------------------------------------------------------
    # 4. Evaluate all positions — each in its own thread so the event
    #    loop stays responsive between evals.  The Scan engine singleton
    #    serialises concurrent calls internally via its own lock, so the
    #    actual Scan CPU time is sequential; the gain here is just I/O
    #    interleaving.
    #
    #    Wall budget is capped at ~25 s to stay under Railway's ~30 s
    #    HTTP proxy timeout — any longer and the platform 502s the
    #    request, the dilf verdicts are computed but never reach the
    #    client, and `pedagogy.storage.upsert_game_analysis` is never
    #    called. That's the root cause of the silent bulk-analyse
    #    failures reported by the user (30 games analysed yet only 1
    #    had verdicts persisted, the one done via the per-game button
    #    which was short enough to fit).
    #
    #    Same logic as `frontend/src/lib/gameAnnotations.ts` for the
    #    legacy Scan annotations (max 200 ms/pos, total ≤ 25 s).
    # ------------------------------------------------------------------
    n_pos = len(ge_states)
    S_PER_POS = max(0.2, min(2.0, 25.0 / max(n_pos, 1)))

    evals: list[dict] = list(await asyncio.gather(*[
        asyncio.to_thread(_scan_eval_sync, s, S_PER_POS)
        for s in ge_states
    ]))

    # ------------------------------------------------------------------
    # 5. Assemble verdicts via dilf
    # ------------------------------------------------------------------
    adapter = GameEngineAdapter()
    verdicts = []

    for i, ge_move in enumerate(ge_moves_played):
        state_before = ge_states[i]
        state_after = ge_states[i + 1]
        ev_before = evals[i]
        ev_after = evals[i + 1]

        dilf_before = ge_state_to_dilf(state_before)
        dilf_after = ge_state_to_dilf(state_after)
        dilf_move = ge_move_to_dilf(ge_move, state_before.board)

        # Best move from engine for the position before this half-move
        best_dilf: Optional[Any] = None
        if ev_before.get("bestMove"):
            bm_ge = _find_move_by_pdn(ev_before["bestMove"], ge_legal(state_before))
            if bm_ge is not None:
                best_dilf = ge_move_to_dilf(bm_ge, state_before.board)

        # Scan reports scores from side-to-move perspective; dilf expects white's perspective.
        raw_before = float(ev_before.get("score", 0.0))
        raw_after = float(ev_after.get("score", 0.0))
        score_before_white = raw_before if state_before.turn == "white" else -raw_before
        score_after_white = raw_after if state_after.turn == "white" else -raw_after

        verdict = assemble_verdict(
            dilf_before,
            dilf_move,
            dilf_after,
            score_before=score_before_white,
            score_after=score_after_white,
            best_move=best_dilf,
            best_pv=ev_before.get("pv") or [],
            half_move_number=i + 1,
            is_book=bool(ev_before.get("forced") and ev_before.get("score", 0) == 0),
            engine=adapter,
        )
        verdicts.append(verdict)

    # ------------------------------------------------------------------
    # 6. Persist analysis
    # ------------------------------------------------------------------
    game_id_str = req.game_id or (
        "pdn-" + hashlib.sha1(pdn_str.encode()).hexdigest()[:16]
    )

    analysis = GameAnalysis(
        game_id=game_id_str,  # type: ignore[arg-type]
        user_id=user["id"],
        user_side=req.user_side or "white",
        opening_name="",
        verdicts=verdicts,
        summary={},
    )
    import logging as _logging  # noqa: PLC0415
    _log = _logging.getLogger(__name__)
    # Diagnostic: surface motif-detection counts per game so Railway logs
    # explain a "0 motifs across N games" complaint without DB access.
    _motif_total = sum(len(v.motifs) for v in verdicts)
    _verdicts_with_motifs = sum(1 for v in verdicts if v.motifs)
    _per_motif: dict[str, int] = {}
    for v in verdicts:
        for m in v.motifs:
            _per_motif[m.motif] = _per_motif.get(m.motif, 0) + 1
    _log.info(
        "analyze-game motifs: game_id=%s user_id=%s verdicts=%d "
        "verdicts_with_motifs=%d motifs_total=%d by_motif=%s",
        game_id_str, user["id"], len(verdicts),
        _verdicts_with_motifs, _motif_total, _per_motif,
    )
    try:
        async with aiosqlite.connect(_db_path()) as conn:
            await storage.upsert_game_analysis(conn, analysis)
        _log.info(
            "analyze-game persisted: game_id=%s verdicts=%d motifs_total=%d",
            game_id_str, len(verdicts), _motif_total,
        )
    except Exception:  # noqa: BLE001
        # DEBUG: full traceback + structural info to diagnose the silent
        # persist failure observed in prod. Remove once root cause found.
        _log.exception(
            "DEBUG persist failure | game_id=%s user_id=%s verdicts=%d "
            "first_verdict_motifs=%s",
            analysis.game_id,
            analysis.user_id,
            len(analysis.verdicts),
            [m.motif for m in analysis.verdicts[0].motifs] if analysis.verdicts else [],
        )

    # ------------------------------------------------------------------
    # 6b. Cascade : also persist legacy Scan annotations into
    #     games.annotations_json. The Scan scores are already computed
    #     above, so this is a free side-effect that flips the
    #     `has_scan_analysis` badge ✓ alongside `has_dilf_analysis` ✓.
    #     Same shape as the frontend `MoveAnnotation` so AnalysisPanel
    #     renders the legacy view unchanged.
    # ------------------------------------------------------------------
    if req.game_id:  # only persist annotations on real DB-backed games
        import math as _math  # noqa: PLC0415
        annotations_payload: list[dict[str, Any]] = []
        for i in range(len(ge_moves_played)):
            ev_before = evals[i]
            ev_after = evals[i + 1]
            score_before = float(ev_before.get("score", 0.0))
            score_after = float(ev_after.get("score", 0.0))
            raw_loss = score_before + score_after
            loss_cp = int(min(1000, max(0, round(raw_loss * 100))))
            # winChance(cp) = 2 / (1 + exp(-2 cp)) - 1, see gameAnnotations.ts
            dwc = (
                (2 / (1 + _math.exp(-2.0 * score_before)) - 1)
                + (2 / (1 + _math.exp(-2.0 * score_after)) - 1)
            )
            delta_winchance = max(0.0, dwc)
            if delta_winchance >= 0.30:
                ann_verdict: Optional[str] = "blunder"
            elif delta_winchance >= 0.15:
                ann_verdict = "mistake"
            elif delta_winchance >= 0.075:
                ann_verdict = "inaccuracy"
            else:
                ann_verdict = None
            annotations_payload.append({
                "posIdx": i + 1,
                "color": ge_states[i].turn,
                "scoreBefore": score_before,
                "scoreAfter": score_after,
                "lossCp": loss_cp,
                "deltaWinChance": delta_winchance,
                "verdict": ann_verdict,
                "bestMove": ev_before.get("bestMove"),
            })
        try:
            from db.games import save_game_annotations  # noqa: PLC0415
            await save_game_annotations(req.game_id, user["id"], annotations_payload)
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "Could not persist legacy annotations cascade (non-fatal): %s", exc,
            )

    # ------------------------------------------------------------------
    # 7. Build summary
    # ------------------------------------------------------------------
    side = req.user_side or "white"
    blunders = sum(1 for v in verdicts if v.verdict.value == "blunder")
    mistakes = sum(1 for v in verdicts if v.verdict.value == "mistake")
    user_verdicts = [v for v in verdicts if v.side == side]
    if user_verdicts:
        avg_accuracy = round(
            1.0 - sum(max(v.delta_winchance, 0.0) for v in user_verdicts) / len(user_verdicts),
            3,
        )
    else:
        avg_accuracy = 1.0

    summary: dict[str, Any] = {
        "total_half_moves": n_moves,
        "blunders": blunders,
        "mistakes": mistakes,
        "average_accuracy": avg_accuracy,
        "user_side": side,
    }

    return AnalyzeGameResponse(
        game_id=game_id_str,
        verdicts=[_verdict_to_out(v) for v in verdicts],
        summary=summary,
    )


# ---------------------------------------------------------------------------
# GET /api/pedagogy/move-verdict/{game_id}/{move_number}
# ---------------------------------------------------------------------------


@router.get(
    "/move-verdict/{game_id}/{move_number}",
    response_model=MoveVerdictOut,
)
async def get_move_verdict(
    game_id: str,
    move_number: int,
    user: Any = Depends(current_user),
) -> MoveVerdictOut:
    async with aiosqlite.connect(_db_path()) as conn:
        v = await storage.get_move_verdict(conn, game_id, move_number)
    if v is None:
        raise HTTPException(404, "Verdict not yet computed for this move")
    return _verdict_to_out(v)


# ---------------------------------------------------------------------------
# GET /api/pedagogy/game/{game_id}/analysis
# ---------------------------------------------------------------------------


@router.get(
    "/game/{game_id}/analysis",
    response_model=AnalyzeGameResponse,
)
async def get_game_analysis(
    game_id: str,
    user: Any = Depends(current_user),
) -> AnalyzeGameResponse:
    """Return the persisted pedagogy verdicts for an already-analysed game.

    Same response shape as POST `/analyze-game`, but does **no** Scan
    work — purely reads what's in `move_verdicts`. 404 if the game has
    never been analysed.
    """
    async with aiosqlite.connect(_db_path()) as conn:
        verdicts = await storage._fetch_verdicts_for_game(conn, game_id)
    if not verdicts:
        raise HTTPException(404, f"No persisted analysis for game {game_id!r}")
    blunders = sum(1 for v in verdicts if v.verdict.value == "blunder")
    mistakes = sum(1 for v in verdicts if v.verdict.value == "mistake")
    inaccuracies = sum(1 for v in verdicts if v.verdict.value == "inaccuracy")
    summary: dict[str, Any] = {
        "blunders": blunders,
        "mistakes": mistakes,
        "inaccuracies": inaccuracies,
        "total_moves": len(verdicts),
    }
    return AnalyzeGameResponse(
        game_id=game_id,
        verdicts=[_verdict_to_out(v) for v in verdicts],
        summary=summary,
    )


# ---------------------------------------------------------------------------
# POST /api/pedagogy/explain-move
# ---------------------------------------------------------------------------


@router.post("/explain-move", response_model=ExplainMoveResponse)
async def explain_move(
    req: ExplainMoveRequest,
    request: Request,
    user: Any = Depends(current_user),
) -> ExplainMoveResponse:
    """Return a 1-3 sentence commentary for one verdict.

    Caches in `pedagogy_explanations`. Rate-limited per IP — 5/min for
    `mode=claude`, 60/min for everything else (spec §14.6).
    """
    _ensure_explain_limiters()
    limiter = _claude_limiter if req.mode == "claude" else _template_limiter
    assert limiter is not None
    await limiter(request)

    async with aiosqlite.connect(_db_path()) as conn:
        v = await storage.get_move_verdict(conn, req.game_id, req.move_number)
        if v is None:
            raise HTTPException(404, "Verdict not yet computed for this move")
        cur = await conn.execute(
            "SELECT id FROM move_verdicts WHERE game_id = ? AND move_number = ?",
            (req.game_id, req.move_number),
        )
        row = await cur.fetchone()
        assert row is not None
        verdict_id = int(row[0])

        cached_text = await storage.get_explanation(conn, verdict_id, req.mode, req.lang)
        if cached_text is not None:
            return ExplainMoveResponse(
                text=cached_text, mode=req.mode, lang=req.lang, cached=True
            )

        # Retrieve the shared BookRAG singleton (may be None if corpus not loaded)
        try:
            from main import shared_book_rag  # noqa: PLC0415
        except ImportError:
            try:
                from ..main import shared_book_rag  # noqa: PLC0415
            except ImportError:
                shared_book_rag = None

        text = await explain_verdict(
            v, mode=req.mode, book_rag=shared_book_rag, lang=req.lang
        )

        await storage.upsert_explanation(conn, verdict_id, req.mode, req.lang, text)
        return ExplainMoveResponse(text=text, mode=req.mode, lang=req.lang, cached=False)


# ---------------------------------------------------------------------------
# GET /api/pedagogy/profile/me*  — declared BEFORE `/profile/{user_id}` so
# the literal "me" doesn't get sucked into the int-typed wildcard route
# and produce a 422 "Input should be a valid integer @ path.user_id"
# (FastAPI matches routes in declaration order).
# ---------------------------------------------------------------------------


@router.get(
    "/profile/me/recommendations",
    response_model=RecommendationsResponse,
)
async def get_recommendations(
    n: int = 10,
    user: Any = Depends(current_user),
) -> RecommendationsResponse:
    async with aiosqlite.connect(_db_path()) as conn:
        games = await storage.fetch_user_games_with_verdicts(conn, user["id"], lookback=30)
        profile = aggregate_user_profile(user["id"], games)
        excluded = await storage.fetch_already_solved_exercise_ids(conn, user["id"])
        pool = await storage.fetch_exercises_by_tags(
            conn,
            profile.recommended_exercise_tags,
            exclude_ids=excluded,
            limit=100,
        )
    chosen = recommend_exercises(profile, pool, exclude_ids=set(excluded), n=n)
    return RecommendationsResponse(exercises=chosen)


@router.get("/profile/me", response_model=UserProfileOut)
async def get_my_profile(
    user: Any = Depends(current_user),
) -> UserProfileOut:
    async with aiosqlite.connect(_db_path()) as conn:
        games = await storage.fetch_user_games_with_verdicts(conn, user["id"], lookback=30)
    profile = aggregate_user_profile(user["id"], games)
    return UserProfileOut(
        user_id=profile.user_id,
        games_count=profile.games_count,
        average_accuracy=profile.average_accuracy,
        strengths=profile.strengths,
        weaknesses=profile.weaknesses,
        weakest_phase=(
            profile.weakest_phase.value
            if hasattr(profile.weakest_phase, "value")
            else profile.weakest_phase
        ),
        recommended_exercise_tags=profile.recommended_exercise_tags,
    )


# ---------------------------------------------------------------------------
# GET /api/pedagogy/profile/me/weakness-heatmap
# ---------------------------------------------------------------------------


@router.get(
    "/profile/me/weakness-heatmap",
    response_model=WeaknessHeatmapOut,
)
async def get_my_weakness_heatmap(
    lookback: int = 30,
    user: Any = Depends(current_user),
) -> WeaknessHeatmapOut:
    """Per-square occurrence counts of isolated / backward / holes / outposts
    across the user's last ``lookback`` games.

    Filters to the user's own side: white games contribute *_white lists,
    black games contribute *_black. The frontend renders this as a 10×10
    heatmap so the user sees *where* their structural weaknesses (and
    outposts) cluster across their recent play.

    Iterates over features_after_json blobs in Python rather than pushing
    the JSON traversal into SQLite — keeps the SQL simple and the
    lookback budget (~30 games × ~50 half-moves = ~1500 rows) cheap
    enough to do in-process.
    """
    import json as _json  # noqa: PLC0415

    by_square: dict[int, dict[str, int]] = {}
    games_analyzed = 0
    half_moves_analyzed = 0
    async with aiosqlite.connect(_db_path()) as conn:
        cur = await conn.execute(
            """
            SELECT id, user_side FROM games
             WHERE user_id = ?
               AND (status = 'finished' OR status IS NULL)
             ORDER BY date DESC
             LIMIT ?
            """,
            (user["id"], lookback),
        )
        games = await cur.fetchall()
        for game_row in games:
            game_id = str(game_row[0])
            side = (game_row[1] or "white").lower()
            suffix = "white" if side == "white" else "black"
            vcur = await conn.execute(
                "SELECT features_after_json FROM move_verdicts "
                "WHERE game_id = ? AND features_after_json IS NOT NULL",
                (game_id,),
            )
            v_rows = await vcur.fetchall()
            if not v_rows:
                continue
            games_analyzed += 1
            for (blob,) in v_rows:
                try:
                    feats = _json.loads(blob)
                except (TypeError, ValueError):
                    continue
                half_moves_analyzed += 1
                for metric, key in (
                    ("isolated", f"isolated_pawns_{suffix}"),
                    ("backward", f"backward_pawns_{suffix}"),
                    ("holes",    f"holes_{suffix}"),
                    ("outposts", f"outposts_{suffix}"),
                ):
                    for sq in feats.get(key, []) or []:
                        bucket = by_square.setdefault(int(sq), {
                            "isolated": 0, "backward": 0, "holes": 0, "outposts": 0,
                        })
                        bucket[metric] += 1
    return WeaknessHeatmapOut(
        by_square={
            sq: SquareWeaknessCounts(**counts) for sq, counts in by_square.items()
        },
        games_analyzed=games_analyzed,
        half_moves_analyzed=half_moves_analyzed,
        lookback=lookback,
    )


# ---------------------------------------------------------------------------
# GET /api/pedagogy/profile/{user_id}
# ---------------------------------------------------------------------------


@router.get("/profile/{user_id}", response_model=UserProfileOut)
async def get_user_profile(
    user_id: int,
    user: Any = Depends(current_user),
) -> UserProfileOut:
    if user["id"] != user_id and not user.get("is_admin", False):
        raise HTTPException(403, "Forbidden")
    async with aiosqlite.connect(_db_path()) as conn:
        games = await storage.fetch_user_games_with_verdicts(conn, user_id, lookback=30)
    profile = aggregate_user_profile(user_id, games)
    return UserProfileOut(
        user_id=profile.user_id,
        games_count=profile.games_count,
        average_accuracy=profile.average_accuracy,
        strengths=profile.strengths,
        weaknesses=profile.weaknesses,
        weakest_phase=profile.weakest_phase.value if hasattr(profile.weakest_phase, "value") else profile.weakest_phase,
        recommended_exercise_tags=profile.recommended_exercise_tags,
    )


# ---------------------------------------------------------------------------
# GET /api/pedagogy/profile/me/motif-debug  — diagnostic
# ---------------------------------------------------------------------------


@router.get("/profile/me/motif-debug")
async def get_motif_debug(
    user: Any = Depends(current_user),
) -> dict[str, Any]:
    """Diagnostic : count motif hits per (motif, role) across the user's
    last 30 games. Helps explain why the Points faibles panel is empty
    even with many analysed games.

    Returns a JSON dict :
      {
        "games_count": int,
        "games_with_verdicts": int,
        "verdicts_total": int,
        "verdicts_with_motifs": int,
        "by_motif_role": {"<motif>/<role>": count, ...},
        "by_motif": {"<motif>": count, ...},
        "missed_threshold": _MOTIF_THRESHOLD,
        "weakness_score": {"<motif>": missed+suffered, ...},
        "would_be_weakness": [<motif> where score >= threshold]
      }
    """
    async with aiosqlite.connect(_db_path()) as conn:
        games = await storage.fetch_user_games_with_verdicts(conn, user["id"], lookback=30)

    by_motif_role: dict[str, int] = {}
    by_motif: dict[str, int] = {}
    weakness_score: dict[str, int] = {}
    verdicts_total = 0
    verdicts_with_motifs = 0
    games_with_verdicts = 0

    for g in games:
        if g.verdicts:
            games_with_verdicts += 1
        for v in g.verdicts:
            verdicts_total += 1
            if v.motifs:
                verdicts_with_motifs += 1
            for m in v.motifs:
                # User-perspective role: own moves keep their role,
                # opponent's `played` motifs become `suffered` for user.
                if v.side == g.user_side:
                    role = m.role
                else:
                    role = "suffered" if m.role == "played" else m.role
                key = f"{m.motif}/{role}"
                by_motif_role[key] = by_motif_role.get(key, 0) + 1
                by_motif[m.motif] = by_motif.get(m.motif, 0) + 1
                if role in ("missed", "suffered"):
                    weakness_score[m.motif] = weakness_score.get(m.motif, 0) + 1

    would_be = [m for m, s in weakness_score.items() if s >= _MOTIF_THRESHOLD]

    return {
        "games_count": len(games),
        "games_with_verdicts": games_with_verdicts,
        "verdicts_total": verdicts_total,
        "verdicts_with_motifs": verdicts_with_motifs,
        "by_motif_role": dict(sorted(by_motif_role.items(), key=lambda kv: -kv[1])),
        "by_motif": dict(sorted(by_motif.items(), key=lambda kv: -kv[1])),
        "missed_threshold": _MOTIF_THRESHOLD,
        "weakness_score": weakness_score,
        "would_be_weakness": would_be,
    }


# ---------------------------------------------------------------------------
# GET /api/pedagogy/motifs/{slug}
# ---------------------------------------------------------------------------


@router.get("/motifs/{slug}", response_model=MotifInfoOut)
async def get_motif_info(
    slug: str,
    _user: Any = Depends(current_user),
) -> MotifInfoOut:
    desc = _get_motif_desc(slug)
    if desc is None:
        raise HTTPException(404, f"Unknown motif: {slug!r}")
    async with aiosqlite.connect(_db_path()) as conn:
        raw_exercises = await storage.fetch_exercises_for_motif(conn, slug, limit=20)
    exercises = [MotifExerciseOut(**ex) for ex in raw_exercises]
    return MotifInfoOut(
        slug=desc["slug"],
        name_fr=desc["name_fr"],
        name_en=desc["name_en"],
        description_fr=desc["description_fr"],
        description_en=desc["description_en"],
        exercises=exercises,
    )
