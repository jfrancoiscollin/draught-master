"""Pydantic request/response models for the FastAPI application.

All public API endpoints in main.py use these models for automatic
request validation and OpenAPI schema generation.
"""
from __future__ import annotations
from typing import List, Optional, Any, Dict
from pydantic import BaseModel


class NewGameRequest(BaseModel):
    """POST /api/games — create a new game session."""
    white_player: str = "Joueur"
    black_player: str = "IA"
    ai_depth: int = 6


class MoveRequest(BaseModel):
    """POST /api/games/{id}/move — submit a player move."""
    path: List[int]
    captures: List[int] = []
    ai_depth: int = 6
    both_sides: bool = False  # if True, also request the AI reply in the same call


class AnalyzeRequest(BaseModel):
    """POST /api/analyze — request position/game/best-move analysis."""
    question: Optional[str] = None
    language: str = 'fr'
    mode: str = 'position'  # 'position' | 'full_game' | 'best_move'
    ai_depth: int = 6


class BoardPiece(BaseModel):
    """A single piece on the board (used in internal serialisation)."""
    square: int
    piece: int


class GameStateResponse(BaseModel):
    """Full game state returned after GET /api/games/{id}."""
    game_id: str
    board: List[int]
    turn: str
    half_move_clock: int
    move_count: int
    result: Optional[str] = None
    fen: str
    last_move: Optional[Dict[str, Any]] = None
    legal_moves: List[Dict[str, Any]] = []


class MoveResponse(BaseModel):
    """Response after POST /api/games/{id}/move — includes optional AI reply."""
    game_id: str
    player_move: Dict[str, Any]
    ai_move: Optional[Dict[str, Any]] = None
    board: List[int]
    turn: str
    half_move_clock: int
    move_count: int
    result: Optional[str] = None
    fen: str
    legal_moves: List[Dict[str, Any]] = []


class LegalMovesResponse(BaseModel):
    """Response for GET /api/games/{id}/moves?from={sq}."""
    game_id: str
    from_square: Optional[int]
    moves: List[Dict[str, Any]]


class ExerciseResponse(BaseModel):
    """Full exercise payload including initial FEN and solution moves."""
    id: int
    name: str
    description: Optional[str]
    initial_fen: str
    difficulty: int
    category: str
    hint: Optional[str]
    solution_moves: List[str]
    legal_moves: List[Dict[str, Any]] = []
    chapter: Optional[int] = None


class ExerciseCheckRequest(BaseModel):
    """POST /api/exercises/{id}/check — verify one move step of an exercise."""
    moves: List[str]
    step: int = 0  # 0-based index of the white move being checked


class ExerciseCheckResponse(BaseModel):
    """Result of an exercise move check, with optional auto-play opponent response."""
    correct: bool
    message: str
    solution: Optional[List[str]] = None
    in_progress: bool = False   # correct move but more user moves remain
    auto_move: Optional[str] = None  # opponent's forced response to auto-apply
    auto_move_path: Optional[List[int]] = None
    auto_move_captures: Optional[List[int]] = None
    next_legal_moves: List[Dict[str, Any]] = []  # legal moves for the next user step


class AnalysisResponse(BaseModel):
    """Response for POST /api/analyze — text analysis + optional move annotations."""
    analysis: str
    best_moves: List[str]
    key_squares: List[int]
    strategic_advice: str
    move_annotations: Optional[List[Dict[str, Any]]] = None


class HistoryItem(BaseModel):
    """Summary row for the game history list."""
    id: str
    date: str
    white_player: str
    black_player: str
    result: Optional[str]
    move_count: int
    has_scan_analysis: bool = False
    has_dilf_analysis: bool = False


class HistoryResponse(BaseModel):
    """Paginated game history list."""
    games: List[HistoryItem]
    total: int
    page: int
    page_size: int


class GameDetailResponse(BaseModel):
    """Full game record including PDN and per-move FEN positions."""
    id: str
    date: str
    white_player: str
    black_player: str
    result: Optional[str]
    pdn: str
    fen_positions: List[str]
    move_count: int


class RegisterRequest(BaseModel):
    """POST /api/auth/register — create a new account."""
    email: str
    password: str


class LoginRequest(BaseModel):
    """POST /api/auth/login — authenticate and obtain a JWT token."""
    email: str
    password: str


class UserResponse(BaseModel):
    """Authenticated user identity (included in TokenResponse)."""
    id: int
    email: str
    lidraughts_username: Optional[str] = None
    # Display username used by Live PvP. Auto-populated from the email
    # local part on first /me call after the column migration; user can
    # change it later via POST /api/auth/me/username.
    username: Optional[str] = None


class TokenResponse(BaseModel):
    """Successful authentication response — contains the JWT and user info."""
    token: str
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    """POST /api/auth/forgot-password — request a password-reset email."""
    email: str


class ResetPasswordRequest(BaseModel):
    """POST /api/auth/reset-password — submit a new password with the reset token."""
    token: str
    password: str
