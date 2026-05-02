from __future__ import annotations
from typing import List, Optional, Any, Dict
from pydantic import BaseModel


class NewGameRequest(BaseModel):
    white_player: str = "Joueur"
    black_player: str = "IA"
    ai_depth: int = 6


class MoveRequest(BaseModel):
    path: List[int]
    captures: List[int] = []
    ai_depth: int = 6
    both_sides: bool = False


class AnalyzeRequest(BaseModel):
    question: Optional[str] = None
    language: str = 'fr'
    mode: str = 'position'  # 'position' | 'full_game' | 'best_move'
    ai_depth: int = 6


class BoardPiece(BaseModel):
    square: int
    piece: int


class GameStateResponse(BaseModel):
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
    game_id: str
    from_square: Optional[int]
    moves: List[Dict[str, Any]]


class ExerciseResponse(BaseModel):
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
    moves: List[str]
    step: int = 0  # 0-based index of the white move being checked


class ExerciseCheckResponse(BaseModel):
    correct: bool
    message: str
    solution: Optional[List[str]] = None
    in_progress: bool = False   # correct move but more user moves remain
    auto_move: Optional[str] = None  # opponent's forced response to auto-apply
    auto_move_path: Optional[List[int]] = None
    auto_move_captures: Optional[List[int]] = None
    next_legal_moves: List[Dict[str, Any]] = []  # legal moves for the next user step


class AnalysisResponse(BaseModel):
    analysis: str
    best_moves: List[str]
    key_squares: List[int]
    strategic_advice: str


class HistoryItem(BaseModel):
    id: str
    date: str
    white_player: str
    black_player: str
    result: Optional[str]
    move_count: int


class HistoryResponse(BaseModel):
    games: List[HistoryItem]
    total: int
    page: int
    page_size: int


class GameDetailResponse(BaseModel):
    id: str
    date: str
    white_player: str
    black_player: str
    result: Optional[str]
    pdn: str
    fen_positions: List[str]
    move_count: int


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str


class TokenResponse(BaseModel):
    token: str
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
