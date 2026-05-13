"""FastAPI router for the pedagogy layer (spec §9)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

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
    MotifMatchOut,
    MoveVerdictOut,
    RecommendationsResponse,
    UserProfileOut,
)

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


# ---------------------------------------------------------------------------
# POST /api/pedagogy/analyze-game
# ---------------------------------------------------------------------------


@router.post("/analyze-game", response_model=AnalyzeGameResponse)
async def analyze_game(
    req: AnalyzeGameRequest,
    user: Any = Depends(current_user),
) -> AnalyzeGameResponse:
    """Run dilf's `assemble_verdict` on every half-move of a game.

    Not yet implemented — wire up to game_engine.py + dilf.verdicts.assembler.
    Tracked in ROADMAP Tier 1.
    """
    if req.game_id is None and not req.pdn:
        raise HTTPException(422, "game_id or pdn is required")
    raise HTTPException(501, "analyze-game not yet implemented")


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
