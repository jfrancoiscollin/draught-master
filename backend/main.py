from __future__ import annotations
import asyncio
import logging
import os
import secrets
import smtplib
import ssl
import uuid
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO)

import hmac
import hashlib
import base64
import json as _json
from passlib.context import CryptContext
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from game_engine import (
    GameState, Move, initial_state, get_legal_moves, apply_move,
    game_result, board_to_fen, fen_to_board, move_to_pdn,
)
from ai_engine import get_best_move
from scan_engine import get_scan_move
from claude_advisor import analyze_position, suggest_exercises, analyze_full_game, explain_best_move_concise
from database import (
    init_db, save_game, get_games, get_game,
    get_exercises, get_exercise, record_progress,
    create_user, get_user_by_email, get_user_by_id,
    create_reset_token, get_reset_token, consume_reset_token,
    mark_exercise_solved, get_user_solved_exercise_ids,
)
from models import (
    NewGameRequest, MoveRequest, AnalyzeRequest,
    GameStateResponse, MoveResponse, LegalMovesResponse,
    ExerciseResponse, ExerciseCheckRequest, ExerciseCheckResponse,
    AnalysisResponse, HistoryResponse, HistoryItem, GameDetailResponse,
    RegisterRequest, LoginRequest, TokenResponse, UserResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
)

load_dotenv()

_SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_DAYS = 30
_pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _create_token(user_id: int, email: str) -> str:
    header = _b64url(_json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    exp = int((datetime.utcnow() + timedelta(days=_TOKEN_EXPIRE_DAYS)).timestamp())
    payload = _b64url(_json.dumps({"sub": str(user_id), "email": email, "exp": exp}).encode())
    sig = _b64url(
        hmac.new(_SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{sig}"


def _decode_token(token: str) -> Dict[str, Any]:
    try:
        header, payload, sig = token.split(".")
        expected = _b64url(
            hmac.new(_SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        data = _json.loads(base64.urlsafe_b64decode(payload + "=="))
        if data.get("exp", 0) < int(datetime.utcnow().timestamp()):
            raise ValueError("expired")
        return data
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token invalide") from exc


async def _require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=401, detail="Non authentifié")
    data = _decode_token(credentials.credentials)
    return {"id": int(data["sub"]), "email": data["email"]}

app = FastAPI(title="AI-Draught API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

game_store: Dict[str, Dict[str, Any]] = {}


@app.on_event("startup")
async def startup_event() -> None:
    await init_db()


def _state_to_response(game_id: str, state: GameState, last_move: Optional[Move] = None) -> GameStateResponse:
    result = game_result(state)
    legal = get_legal_moves(state) if result is None else []
    return GameStateResponse(
        game_id=game_id,
        board=state.board,
        turn=state.turn,
        half_move_clock=state.half_move_clock,
        move_count=len(state.move_history),
        result=result,
        fen=board_to_fen(state),
        last_move={"path": last_move.path, "captures": last_move.captures} if last_move else None,
        legal_moves=[{"path": m.path, "captures": m.captures} for m in legal],
    )


def _build_pdn(history: List[Move]) -> str:
    if not history:
        return ""
    parts = []
    for i, move in enumerate(history):
        if i % 2 == 0:
            parts.append(f"{i // 2 + 1}. {move_to_pdn(move)}")
        else:
            parts[-1] += f" {move_to_pdn(move)}"
    return " ".join(parts)


@app.post("/api/game/new", response_model=GameStateResponse)
async def new_game(req: NewGameRequest) -> GameStateResponse:
    game_id = str(uuid.uuid4())
    state = initial_state()
    game_store[game_id] = {
        "state": state,
        "white_player": req.white_player,
        "black_player": req.black_player,
        "ai_depth": req.ai_depth,
        "fen_positions": [board_to_fen(state)],
        "date": datetime.utcnow().isoformat(),
        "state_history": [],   # list of (GameState, fen_positions_len) for undo
    }
    return _state_to_response(game_id, state)


@app.get("/api/game/{game_id}/legal-moves", response_model=LegalMovesResponse)
async def legal_moves(game_id: str, from_sq: Optional[int] = Query(None)) -> LegalMovesResponse:
    if game_id not in game_store:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    state: GameState = game_store[game_id]["state"]
    all_moves = get_legal_moves(state)
    if from_sq is not None:
        filtered = [m for m in all_moves if m.path[0] == from_sq]
    else:
        filtered = all_moves
    moves_data = [{"path": m.path, "captures": m.captures} for m in filtered]
    return LegalMovesResponse(game_id=game_id, from_square=from_sq, moves=moves_data)


@app.post("/api/game/{game_id}/move", response_model=MoveResponse)
async def make_move(game_id: str, req: MoveRequest) -> MoveResponse:
    if game_id not in game_store:
        raise HTTPException(status_code=404, detail="Partie introuvable")

    entry = game_store[game_id]
    state: GameState = entry["state"]

    if game_result(state) is not None:
        raise HTTPException(status_code=400, detail="La partie est terminée")

    player_move = Move(path=req.path, captures=req.captures)
    legal = get_legal_moves(state)
    legal_set = {(tuple(m.path), frozenset(m.captures)) for m in legal}
    move_key = (tuple(player_move.path), frozenset(player_move.captures))
    if move_key not in legal_set:
        raise HTTPException(status_code=400, detail="Coup illégal")

    # Save snapshot before applying player move so undo can restore it
    entry["state_history"].append((state, len(entry["fen_positions"])))

    state = apply_move(state, player_move)
    entry["state"] = state
    entry["fen_positions"].append(board_to_fen(state))

    result = game_result(state)
    ai_move_data = None

    if not req.both_sides and result is None and state.turn == "black":
        depth = req.ai_depth
        loop = asyncio.get_event_loop()

        def _pick_move(s: GameState, d: int) -> Optional[Move]:
            legal = get_legal_moves(s)
            if not legal:
                return None
            if len(legal) == 1:
                return legal[0]
            move = get_scan_move(s, d)
            if move is None:
                move = get_best_move(s, depth=d)
            return move

        ai_move = await loop.run_in_executor(None, _pick_move, state, depth)
        if ai_move:
            # Save snapshot before AI move so undo can remove it independently
            entry["state_history"].append((state, len(entry["fen_positions"])))
            state = apply_move(state, ai_move)
            entry["state"] = state
            entry["fen_positions"].append(board_to_fen(state))
            ai_move_data = {"path": ai_move.path, "captures": ai_move.captures}
            result = game_result(state)

    if result is not None:
        pdn = _build_pdn(state.move_history)
        await save_game(
            game_id=game_id,
            date=entry["date"],
            white_player=entry["white_player"],
            black_player=entry["black_player"],
            result=result,
            pdn=pdn,
            fen_positions=entry["fen_positions"],
            move_count=len(state.move_history),
        )

    final_legal = get_legal_moves(state) if result is None else []
    return MoveResponse(
        game_id=game_id,
        player_move={"path": player_move.path, "captures": player_move.captures},
        ai_move=ai_move_data,
        board=state.board,
        turn=state.turn,
        half_move_clock=state.half_move_clock,
        move_count=len(state.move_history),
        result=result,
        fen=board_to_fen(state),
        legal_moves=[{"path": m.path, "captures": m.captures} for m in final_legal],
    )


@app.post("/api/game/{game_id}/resign")
async def resign_game(game_id: str) -> Dict[str, Any]:
    if game_id not in game_store:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    entry = game_store[game_id]
    state: GameState = entry["state"]
    if game_result(state) is not None:
        raise HTTPException(status_code=400, detail="La partie est déjà terminée")
    pdn = _build_pdn(state.move_history)
    await save_game(
        game_id=game_id,
        date=entry["date"],
        white_player=entry["white_player"],
        black_player=entry["black_player"],
        result="black",
        pdn=pdn,
        fen_positions=entry["fen_positions"],
        move_count=len(state.move_history),
    )
    return {"result": "black"}


@app.post("/api/game/{game_id}/undo", response_model=GameStateResponse)
async def undo_move(game_id: str) -> GameStateResponse:
    if game_id not in game_store:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    entry = game_store[game_id]
    if not entry["state_history"]:
        raise HTTPException(status_code=400, detail="Aucun coup à annuler")
    state, fen_len = entry["state_history"].pop()
    entry["state"] = state
    entry["fen_positions"] = entry["fen_positions"][:fen_len]
    return _state_to_response(game_id, state)


@app.get("/api/game/{game_id}/ai-move")
async def get_ai_move_suggestion(
    game_id: str, depth: int = Query(4)
) -> Dict[str, Any]:
    if game_id not in game_store:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    state: GameState = game_store[game_id]["state"]
    move = get_best_move(state, depth=depth)
    if move is None:
        return {"move": None}
    return {"move": {"path": move.path, "captures": move.captures}}


@app.post("/api/game/{game_id}/analyze", response_model=AnalysisResponse)
async def analyze(game_id: str, req: AnalyzeRequest) -> AnalysisResponse:
    if game_id not in game_store:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    state: GameState = game_store[game_id]["state"]
    try:
        if req.mode == 'full_game':
            result = await analyze_full_game(state, state.move_history, req.language)
        elif req.mode == 'best_move':
            result = await explain_best_move_concise(state, state.move_history, req.language, req.ai_depth)
        else:
            result = await analyze_position(state, state.move_history, req.question, req.language)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur analyse: {type(e).__name__}: {e}")
    return AnalysisResponse(**result)


@app.get("/api/exercises", response_model=List[ExerciseResponse])
async def list_exercises(
    category: Optional[str] = Query(None),
    difficulty: Optional[int] = Query(None),
) -> List[ExerciseResponse]:
    exercises = await get_exercises(category=category, difficulty=difficulty)
    result = []
    for ex in exercises:
        try:
            result.append(ExerciseResponse(**ex))
        except Exception as e:
            logging.error(f"Exercise {ex.get('id')} skipped: {e}")
    return result


@app.get("/api/exercises-categories")
async def list_exercise_categories() -> List[str]:
    exercises = await get_exercises()
    seen: dict = {}
    for ex in exercises:
        cat = ex["category"]
        if cat not in seen:
            seen[cat] = True
    return list(seen.keys())


@app.get("/api/exercises/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise_detail(exercise_id: int) -> ExerciseResponse:
    ex = await get_exercise(exercise_id)
    if ex is None:
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    state = fen_to_board(ex["initial_fen"])
    legal = get_legal_moves(state)
    return ExerciseResponse(
        **ex,
        legal_moves=[{"path": m.path, "captures": m.captures} for m in legal],
    )


@app.get("/api/exercises/{exercise_id}/legal-moves")
async def exercise_legal_moves_endpoint(
    exercise_id: int,
    step: int = Query(0),
) -> Dict[str, Any]:
    ex = await get_exercise(exercise_id)
    if ex is None:
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    solution: List[Optional[str]] = ex["solution_moves"]
    # Reconstruct state after `step` user moves (each user move is followed by an opponent move)
    state = _reconstruct_state(ex["initial_fen"], solution, step * 2)
    if state is None:
        # Reconstruction failed (e.g. abbreviated solution PDN): return empty so
        # the frontend activates free-move mode rather than showing wrong moves.
        if step > 0:
            return {"moves": []}
        state = fen_to_board(ex["initial_fen"])
    legal = get_legal_moves(state)
    return {"moves": [{"path": m.path, "captures": m.captures} for m in legal]}


def _find_move_by_pdn(pdn: str, legal_moves: List[Move]) -> Optional[Move]:
    """Match a PDN string (full or short form start x end) to a legal move."""
    pdn_norm = pdn.strip()
    for move in legal_moves:
        if move_to_pdn(move) == pdn_norm:
            return move
    try:
        if 'x' in pdn_norm:
            parts = [int(p) for p in pdn_norm.split('x') if p]
        elif '-' in pdn_norm:
            parts = [int(p) for p in pdn_norm.split('-') if p]
        else:
            return None
        start, end = parts[0], parts[-1]
    except (ValueError, IndexError):
        return None
    for move in legal_moves:
        if move.path[0] == start and move.path[-1] == end:
            return move
    return None


def _reconstruct_state(initial_fen: str, solution: List[Optional[str]], move_count: int) -> Optional[GameState]:
    """Apply move_count moves from solution to reconstruct board state."""
    state = fen_to_board(initial_fen)
    for i in range(move_count):
        if i >= len(solution) or solution[i] is None:
            break
        legal = get_legal_moves(state)
        move = _find_move_by_pdn(solution[i], legal)
        if move is None:
            return None
        state = apply_move(state, move)
    return state


async def _optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[Dict[str, Any]]:
    if not credentials:
        return None
    try:
        data = _decode_token(credentials.credentials)
        return {"id": int(data["sub"]), "email": data["email"]}
    except Exception:
        return None


@app.post("/api/exercises/{exercise_id}/check", response_model=ExerciseCheckResponse)
async def check_exercise(
    exercise_id: int,
    req: ExerciseCheckRequest,
    current_user: Optional[Dict[str, Any]] = Depends(_optional_auth),
) -> ExerciseCheckResponse:
    ex = await get_exercise(exercise_id)
    if ex is None:
        raise HTTPException(status_code=404, detail="Exercice introuvable")

    solution: List[Optional[str]] = ex["solution_moves"]  # may contain None for ad-lib moves
    step = req.step
    submitted = req.moves

    def _parse_endpoints(pdn: str):
        s = pdn.strip().lstrip('K')
        try:
            if 'x' in s:
                parts = [int(p) for p in s.split('x') if p]
            elif '-' in s:
                parts = [int(p) for p in s.split('-') if p]
            else:
                return None, None
            return parts[0], parts[-1]
        except (ValueError, IndexError):
            return None, None

    def _moves_match(submitted: str, expected: str) -> bool:
        s = submitted.strip().lstrip('K')
        e = expected.strip().lstrip('K')
        if s == e:
            return True
        s_start, s_end = _parse_endpoints(s)
        e_start, e_end = _parse_endpoints(e)
        return s_start is not None and s_start == e_start and s_end == e_end

    user_move_idx = step * 2
    if user_move_idx >= len(solution) or solution[user_move_idx] is None:
        return ExerciseCheckResponse(correct=True, message="Exercice terminé.")

    expected = solution[user_move_idx]
    correct = len(submitted) >= 1 and _moves_match(submitted[0], expected)

    if correct:
        next_opponent_idx = user_move_idx + 1
        next_user_idx = user_move_idx + 2

        auto_move: Optional[str] = None
        auto_move_path: Optional[List[int]] = None
        auto_move_captures: Optional[List[int]] = None

        if next_opponent_idx < len(solution) and solution[next_opponent_idx] is not None:
            auto_move = solution[next_opponent_idx]
            # Reconstruct board after user's move and find full auto_move data
            state_after_user = _reconstruct_state(ex["initial_fen"], solution, user_move_idx + 1)
            if state_after_user:
                opponent_legal = get_legal_moves(state_after_user)
                auto_move_obj = _find_move_by_pdn(auto_move, opponent_legal)
                if auto_move_obj:
                    auto_move_path = auto_move_obj.path
                    auto_move_captures = auto_move_obj.captures
                elif 'x' in auto_move:
                    # PDN is a capture but no exact/endpoint match found (abbreviated notation).
                    # Fall back to first legal capture from the same starting square for display.
                    try:
                        start_sq = int(auto_move.split('x')[0])
                        fallback_obj = next(
                            (m for m in opponent_legal if m.path[0] == start_sq and m.captures),
                            None,
                        )
                        if fallback_obj:
                            auto_move_path = fallback_obj.path
                            auto_move_captures = fallback_obj.captures
                    except (ValueError, IndexError):
                        pass

        has_more = next_user_idx < len(solution) and any(
            m is not None for m in solution[next_user_idx:]
        )

        if has_more:
            # Compute legal moves for the next user step (after auto_move applied)
            next_legal_moves: List[Dict] = []
            state_after_auto = _reconstruct_state(ex["initial_fen"], solution, user_move_idx + 2)
            if state_after_auto:
                next_legal = get_legal_moves(state_after_auto)
                next_legal_moves = [{"path": m.path, "captures": m.captures} for m in next_legal]

            return ExerciseCheckResponse(
                correct=True,
                in_progress=True,
                message="Bon coup ! Continuez.",
                auto_move=auto_move,
                auto_move_path=auto_move_path,
                auto_move_captures=auto_move_captures,
                next_legal_moves=next_legal_moves,
            )
        else:
            await record_progress(exercise_id, True)
            if current_user:
                await mark_exercise_solved(current_user["id"], exercise_id)
            return ExerciseCheckResponse(
                correct=True,
                in_progress=False,
                message="Bravo ! Vous avez trouvé la solution.",
                auto_move=auto_move,
                auto_move_path=auto_move_path,
                auto_move_captures=auto_move_captures,
            )
    else:
        if step == 0:
            await record_progress(exercise_id, False)
        first_move = next((m for m in solution if m is not None), None)
        msg = f"Ce n'est pas le bon coup. Le premier coup attendu était : {first_move}"
        visible = [m for m in solution if m is not None]
        return ExerciseCheckResponse(
            correct=False,
            message=msg,
            solution=visible,
        )


@app.get("/api/history", response_model=HistoryResponse)
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
) -> HistoryResponse:
    offset = (page - 1) * page_size
    games = await get_games(limit=page_size, offset=offset)
    items = [
        HistoryItem(
            id=g["id"],
            date=g["date"],
            white_player=g["white_player"],
            black_player=g["black_player"],
            result=g.get("result"),
            move_count=g.get("move_count", 0),
        )
        for g in games
    ]
    return HistoryResponse(games=items, total=len(items), page=page, page_size=page_size)


@app.get("/api/history/{game_id}", response_model=GameDetailResponse)
async def get_game_detail(game_id: str) -> GameDetailResponse:
    game = await get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    return GameDetailResponse(**game)


def _send_reset_email(to_email: str, reset_link: str) -> bool:
    """Returns True if email was sent successfully."""
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    from_addr = os.getenv("SMTP_FROM", user)

    if not host or not user or not password:
        logging.warning(f"SMTP not configured — reset link: {reset_link}")
        return False

    body = (
        "Bonjour,\n\n"
        "Vous avez demandé la réinitialisation de votre mot de passe sur AI-Draught.\n\n"
        f"Cliquez sur ce lien (valable 1 heure) :\n{reset_link}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.\n\n"
        "L'équipe AI-Draught"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Réinitialisation de mot de passe — AI-Draught"
    msg["From"] = from_addr
    msg["To"] = to_email
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=ctx)
            server.login(user, password)
            server.sendmail(from_addr, to_email, msg.as_string())
        logging.info(f"Reset email sent to {to_email}")
        return True
    except Exception as e:
        logging.error(f"SMTP error sending reset email to {to_email}: {type(e).__name__}: {e}")
        return False


@app.post("/api/auth/forgot-password")
async def auth_forgot_password(req: ForgotPasswordRequest) -> Dict[str, Any]:
    email = req.email.lower().strip()
    user = await get_user_by_email(email)
    if not user:
        return {
            "message": "Aucun compte trouvé avec cet email. Veuillez vous inscrire.",
            "not_found": True,
        }

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    await create_reset_token(email, token, expires_at)
    app_url = os.getenv("APP_URL", "").rstrip("/")
    reset_link = f"{app_url}/?reset_token={token}"
    sent = _send_reset_email(email, reset_link)

    if sent:
        return {"message": "Un lien de réinitialisation a été envoyé à votre adresse email."}
    else:
        # SMTP not configured or failed: return the link directly so the admin can share it
        return {
            "message": "L'envoi email a échoué. Utilisez le lien ci-dessous pour réinitialiser votre mot de passe :",
            "reset_url": reset_link,
        }


@app.post("/api/auth/reset-password")
async def auth_reset_password(req: ResetPasswordRequest) -> Dict[str, str]:
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caractères")
    row = await get_reset_token(req.token)
    if not row:
        raise HTTPException(status_code=400, detail="Lien invalide ou expiré")
    expires_at = datetime.fromisoformat(row["expires_at"])
    if datetime.utcnow() > expires_at:
        raise HTTPException(status_code=400, detail="Lien expiré")
    new_hash = _pwd_context.hash(req.password)
    ok = await consume_reset_token(req.token, new_hash)
    if not ok:
        raise HTTPException(status_code=400, detail="Lien invalide ou déjà utilisé")
    return {"message": "Mot de passe mis à jour avec succès"}


@app.post("/api/auth/register", response_model=TokenResponse)
async def auth_register(req: RegisterRequest) -> TokenResponse:
    email = req.email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Email invalide")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caractères")
    if await get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")
    password_hash = _pwd_context.hash(req.password)
    user_id = await create_user(email, password_hash)
    return TokenResponse(
        token=_create_token(user_id, email),
        user=UserResponse(id=user_id, email=email),
    )


@app.post("/api/auth/login", response_model=TokenResponse)
async def auth_login(req: LoginRequest) -> TokenResponse:
    email = req.email.lower().strip()
    user = await get_user_by_email(email)
    if not user or not _pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    return TokenResponse(
        token=_create_token(user["id"], user["email"]),
        user=UserResponse(id=user["id"], email=user["email"]),
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def auth_me(current_user: Dict[str, Any] = Depends(_require_auth)) -> UserResponse:
    return UserResponse(id=current_user["id"], email=current_user["email"])


@app.get("/api/auth/me/progress")
async def auth_me_progress(current_user: Dict[str, Any] = Depends(_require_auth)) -> Dict[str, Any]:
    solved_ids = await get_user_solved_exercise_ids(current_user["id"])
    return {"solved_exercise_ids": solved_ids}


@app.get("/api/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/debug/db-stats")
async def debug_db_stats() -> Dict[str, Any]:
    import aiosqlite
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT category, COUNT(*) as cnt FROM exercises GROUP BY category ORDER BY category"
        )
        rows = await cursor.fetchall()
        cats = {row[0]: row[1] for row in rows}
        cursor2 = await db.execute("SELECT COUNT(*) FROM exercises")
        total = (await cursor2.fetchone())[0]
    return {"total": total, "by_category": cats}


_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(_STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(_STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        return FileResponse(
            os.path.join(_STATIC_DIR, "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
