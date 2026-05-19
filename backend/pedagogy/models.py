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
    # Structural weaknesses (also from features_after) — the position
    # diagnostic panel highlights one set at a time on the board.
    isolated_pawns_white: list[int] = []
    isolated_pawns_black: list[int] = []
    backward_pawns_white: list[int] = []
    backward_pawns_black: list[int] = []
    holes_white: list[int] = []
    holes_black: list[int] = []
    outposts_white: list[int] = []
    outposts_black: list[int] = []
    # Named formations detected on the position (e.g. "roozenburg_blancs").
    # Phase is already on MoveVerdict.phase above — no duplicate needed.
    formations: list[str] = []
    # Captures the opponent would play next turn — for the board arrow
    # overlay. Each entry mirrors the dilf ThreatenedCapture dataclass:
    # {"path": [from, to, ...], "captures": [sq, ...]}.
    threatened_captures_white: list[dict[str, list[int]]] = []
    threatened_captures_black: list[dict[str, list[int]]] = []


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


class SquareWeaknessCounts(BaseModel):
    isolated: int = 0
    backward: int = 0
    holes: int = 0
    outposts: int = 0


class HeatmapNarrativeOut(BaseModel):
    """Top squares (verbatim) + one pedagogical sentence for one metric."""

    top_line: str
    hint: str


# ---------------------------------------------------------------------------
# Per-game narrative (dilf.profile.narrate_game) — J4 wire shape
# ---------------------------------------------------------------------------


class PhaseSummaryOut(BaseModel):
    phase: str                      # "opening" | "middlegame" | "endgame"
    n_half_moves: int
    acpl_user: int
    acpl_opponent: int
    summary: str


class TurningPointOut(BaseModel):
    move_number: int
    side: str                       # "white" | "black"
    notation: str
    delta_cp: int
    score_before: float
    score_after: float
    verdict: str
    reason: str


class PersistentWeaknessOut(BaseModel):
    family: str                     # "isolated" | "backward" | "holes" | "outposts"
    square: int
    side: str
    duration_half_moves: int
    first_seen: int
    summary: str


class GameNarrativeOut(BaseModel):
    """Wire shape of :func:`pedagogy.profile.narrate_game`'s output —
    consumed by the frontend's <GameNarrativeSummary>."""

    headline: str
    phase_summary: list[PhaseSummaryOut]
    turning_points: list[TurningPointOut]
    persistent_weaknesses: list[PersistentWeaknessOut]
    motifs_played: dict[str, int]
    motifs_missed: dict[str, int]
    strengths: list[str]
    recommended_drills: list[str]


class NarrateHeatmapRequest(BaseModel):
    # Same shape as WeaknessHeatmapOut.by_square. Keys are FMJD square
    # indices 1..50 sent as ints by the wire; Pydantic accepts the
    # canonical JSON form (numeric keys become str on the JSON side and
    # are coerced back here).
    by_square: dict[int, SquareWeaknessCounts]


class NarrateHeatmapResponse(BaseModel):
    narratives: dict[str, Optional[HeatmapNarrativeOut]]


class WeaknessHeatmapOut(BaseModel):
    # Square index (1..50, FMJD numbering) -> per-metric occurrence count
    # across the lookback window. Only the user's own side is counted, so
    # users see *their* recurring weaknesses, not the opponent's.
    by_square: dict[int, SquareWeaknessCounts]
    games_analyzed: int
    half_moves_analyzed: int
    lookback: int
    # Pre-computed narratives, one per metric (incl. "all"). Null when
    # the metric has no signal — frontend just hides the narrative box.
    # Pre-computing all 5 avoids a round-trip per toggle.
    narratives: dict[str, Optional[HeatmapNarrativeOut]] = {}
