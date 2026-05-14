"""Pydantic models for the /api/pedagogy/* routes (PR 8)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class AnalyzeGameRequest(BaseModel):
    """One of game_id / pdn is required."""

    game_id: Optional[str] = None
    pdn: Optional[str] = None
    user_side: Optional[str] = Field(default=None, pattern="^(white|black)$")
    lang: str = Field(default="fr", pattern="^(fr|en)$")


class ExplainMoveRequest(BaseModel):
    game_id: str
    move_number: int
    mode: str = Field(default="template", pattern="^(template|template\\+book|claude)$")
    lang: str = Field(default="fr", pattern="^(fr|en)$")


class ImportLidraughtsRequest(BaseModel):
    """Trigger an import of the authenticated user's lidraughts history.

    The user is identified by their lidraughts username (free-form, the
    Lidraughts profile URL last segment). ``max_games`` is capped at 50 in
    the route handler to keep an individual import bounded; larger
    backfills should be queued by the caller in batches.
    """

    lidraughts_username: str = Field(min_length=1, max_length=64)
    max_games: int = Field(default=10, ge=1, le=50)
    user_side: Optional[str] = Field(
        default=None,
        pattern="^(white|black|auto)$",
        description=(
            "'auto' (default) reads the [White]/[Black] PDN tag and matches "
            "against lidraughts_username case-insensitively. Override with "
            "'white' or 'black' if the username heuristic is unreliable."
        ),
    )


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class MotifMatchOut(BaseModel):
    motif: str
    role: str
    squares: list[int]
    pv: list[str]
    severity: float
    metadata: dict[str, Any] = {}


class MoveVerdictOut(BaseModel):
    move_number: int
    side: str
    move_notation: str
    fen_before: str
    fen_after: str
    score_before: float
    score_after: float
    delta_winchance: float
    verdict: str
    is_forced: bool
    phase: str
    motifs: list[MotifMatchOut] = []


class AnalyzeGameResponse(BaseModel):
    game_id: str
    verdicts: list[MoveVerdictOut]
    summary: dict[str, Any] = {}


class ExplainMoveResponse(BaseModel):
    text: str
    mode: str
    lang: str
    cached: bool


class UserProfileOut(BaseModel):
    user_id: int
    games_count: int
    average_accuracy: float
    strengths: list[dict[str, Any]]
    weaknesses: list[dict[str, Any]]
    weakest_phase: str
    recommended_exercise_tags: list[str]


class RecommendationsResponse(BaseModel):
    exercises: list[dict[str, Any]]


class ImportLidraughtsReportEntry(BaseModel):
    """Per-game outcome of a lidraughts import."""

    game_id: str
    status: str = Field(pattern="^(analyzed|skipped_dedup|failed)$")
    half_moves: int = 0
    error: Optional[str] = None


class ImportLidraughtsResponse(BaseModel):
    """Summary returned by POST /api/pedagogy/import-lidraughts."""

    lidraughts_username: str
    fetched: int
    analyzed: int
    skipped_dedup: int
    failed: int
    games: list[ImportLidraughtsReportEntry] = []
    profile_url: str = "/api/pedagogy/profile/me"


class MotifExerciseOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    initial_fen: str
    solution_moves: list[str]
    difficulty: int
    category: str
    hint: Optional[str]


class MotifInfoOut(BaseModel):
    slug: str
    name_fr: str
    name_en: str
    description_fr: str
    description_en: str
    exercises: list[MotifExerciseOut] = []
