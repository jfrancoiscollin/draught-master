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
    # Slim slice of features_after — what the frontend needs to render
    # the position AFTER this move. material_balance feeds the timeline;
    # hanging_pieces_{white,black} feed the board overlay.
    material_balance: Optional[int] = None
    hanging_pieces_white: list[int] = []
    hanging_pieces_black: list[int] = []


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
