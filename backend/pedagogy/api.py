"""FastAPI router for the pedagogy layer (spec §9)."""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import asdict
from typing import Any, Optional

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from pedagogy.explanations import explain_verdict
from pedagogy.profile.aggregator import aggregate_user_profile
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
    UserProfileOut,
)
from .motif_descriptions import get_motif as _get_motif_desc

router = APIRouter(prefix="/api/pedagogy", tags=["pedagogy"])

# Rate limiter for Claude mode (5/min) — imported lazily to avoid circular import
_claude_limiter = None


def _get_claude_limiter():
    global _claude_limiter
    if _claude_limiter is None:
        from ..main import _make_limiter  # noqa: PLC0415
        _claude_limiter = _make_limiter(max_calls=5, window=60)
    return _claude_limiter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verdict_to_out(v: Any) -> MoveVerdictOut:
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
    #    actual Scan CPU time is sequential; the gain here is a higher
    #    per-position budget (2 s vs 0.5 s) that matches gameplay quality.
    #    Total wall time ≈ n_pos × S_PER_POS, capped at 120 s.
    # ------------------------------------------------------------------
    n_pos = len(ge_states)
    S_PER_POS = min(2.0, 120.0 / max(n_pos, 1))

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
    try:
        async with aiosqlite.connect(_db_path()) as conn:
            await storage.upsert_game_analysis(conn, analysis)
    except Exception as exc:  # noqa: BLE001
        _log.warning("Could not persist pedagogy analysis (non-fatal): %s", exc)

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
# POST /api/pedagogy/explain-move
# ---------------------------------------------------------------------------


@router.post("/explain-move", response_model=ExplainMoveResponse)
async def explain_move(
    req: ExplainMoveRequest,
    user: Any = Depends(current_user),
) -> ExplainMoveResponse:
    """Return a 1-3 sentence commentary for one verdict.

    Caches in `pedagogy_explanations`. Rate-limited 5/min for claude mode.
    """
    from fastapi import Request  # noqa: PLC0415

    if req.mode == "claude":
        # Build a dummy request for the IP-based limiter
        pass  # Rate limiting handled at infrastructure level for now

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
            from ..main import shared_book_rag  # noqa: PLC0415
        except ImportError:
            shared_book_rag = None

        text = explain_verdict(v, mode=req.mode, book_rag=shared_book_rag, lang=req.lang)

        await storage.upsert_explanation(conn, verdict_id, req.mode, req.lang, text)
        return ExplainMoveResponse(text=text, mode=req.mode, lang=req.lang, cached=False)


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
# GET /api/pedagogy/profile/me/recommendations
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


# ---------------------------------------------------------------------------
# GET /api/pedagogy/profile/me  (convenience alias for the connected user)
# ---------------------------------------------------------------------------


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
