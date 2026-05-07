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
from scan_advisor import analyze_position, analyze_full_game, analyze_full_game_pdn, explain_best_move_concise
from database import (
    init_db, save_game, get_games, get_game,
    save_active_game, load_active_game, delete_active_game,
    get_exercises, get_exercise, record_progress,
    create_user, get_user_by_email, get_user_by_id,
    create_reset_token, get_reset_token, consume_reset_token,
    mark_exercise_solved, get_user_solved_exercise_ids,
    mark_lesson_read, get_user_read_lesson_chapters,
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


import json as _json_mod


def _serialize_entry(entry: dict) -> str:
    def ser_state(s: GameState) -> dict:
        return {
            "board": s.board,
            "turn": s.turn,
            "half_move_clock": s.half_move_clock,
            "move_history": [{"path": m.path, "captures": m.captures} for m in s.move_history],
        }
    return _json_mod.dumps({
        "date": entry["date"],
        "white_player": entry["white_player"],
        "black_player": entry["black_player"],
        "ai_depth": entry.get("ai_depth", 4),
        "fen_positions": entry["fen_positions"],
        "state": ser_state(entry["state"]),
        "state_history": [
            {"state": ser_state(s), "fen_len": fl}
            for s, fl in entry["state_history"]
        ],
    })


def _deserialize_entry(raw: str) -> dict:
    d = _json_mod.loads(raw)

    def deser_state(sd: dict) -> GameState:
        return GameState(
            board=sd["board"],
            turn=sd["turn"],
            half_move_clock=sd.get("half_move_clock", 0),
            move_history=[Move(path=m["path"], captures=m["captures"]) for m in sd.get("move_history", [])],
        )

    return {
        "date": d["date"],
        "white_player": d["white_player"],
        "black_player": d["black_player"],
        "ai_depth": d.get("ai_depth", 4),
        "fen_positions": d["fen_positions"],
        "state": deser_state(d["state"]),
        "state_history": [
            (deser_state(sh["state"]), sh["fen_len"])
            for sh in d.get("state_history", [])
        ],
    }


async def _get_game_entry(game_id: str) -> Optional[dict]:
    """Return game entry from RAM cache, restoring from DB if needed."""
    if game_id in game_store:
        return game_store[game_id]
    raw = await load_active_game(game_id)
    if raw is None:
        return None
    entry = _deserialize_entry(raw)
    game_store[game_id] = entry
    return entry


@app.post("/api/game/new", response_model=GameStateResponse)
async def new_game(req: NewGameRequest) -> GameStateResponse:
    game_id = str(uuid.uuid4())
    state = initial_state()
    entry = {
        "state": state,
        "white_player": req.white_player,
        "black_player": req.black_player,
        "ai_depth": req.ai_depth,
        "fen_positions": [board_to_fen(state)],
        "date": datetime.utcnow().isoformat(),
        "state_history": [],
    }
    game_store[game_id] = entry
    await save_active_game(game_id, _serialize_entry(entry))
    return _state_to_response(game_id, state)


@app.get("/api/game/{game_id}/legal-moves", response_model=LegalMovesResponse)
async def legal_moves(game_id: str, from_sq: Optional[int] = Query(None)) -> LegalMovesResponse:
    entry = await _get_game_entry(game_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    state: GameState = entry["state"]
    all_moves = get_legal_moves(state)
    if from_sq is not None:
        filtered = [m for m in all_moves if m.path[0] == from_sq]
    else:
        filtered = all_moves
    moves_data = [{"path": m.path, "captures": m.captures} for m in filtered]
    return LegalMovesResponse(game_id=game_id, from_square=from_sq, moves=moves_data)


@app.post("/api/game/{game_id}/move", response_model=MoveResponse)
async def make_move(game_id: str, req: MoveRequest) -> MoveResponse:
    entry = await _get_game_entry(game_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Partie introuvable")
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
        await delete_active_game(game_id)
    else:
        await save_active_game(game_id, _serialize_entry(entry))

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
    entry = await _get_game_entry(game_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Partie introuvable")
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
    await delete_active_game(game_id)
    return {"result": "black"}


@app.post("/api/game/{game_id}/undo", response_model=GameStateResponse)
async def undo_move(game_id: str) -> GameStateResponse:
    entry = await _get_game_entry(game_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    if not entry["state_history"]:
        raise HTTPException(status_code=400, detail="Aucun coup à annuler")
    state, fen_len = entry["state_history"].pop()
    entry["state"] = state
    entry["fen_positions"] = entry["fen_positions"][:fen_len]
    await save_active_game(game_id, _serialize_entry(entry))
    return _state_to_response(game_id, state)


@app.get("/api/game/{game_id}/ai-move")
async def get_ai_move_suggestion(
    game_id: str, depth: int = Query(4)
) -> Dict[str, Any]:
    entry = await _get_game_entry(game_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    state: GameState = entry["state"]
    move = get_best_move(state, depth=depth)
    if move is None:
        return {"move": None}
    return {"move": {"path": move.path, "captures": move.captures}}


@app.post("/api/game/{game_id}/analyze", response_model=AnalysisResponse)
async def analyze(game_id: str, req: AnalyzeRequest) -> AnalysisResponse:
    entry = await _get_game_entry(game_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    state: GameState = entry["state"]
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


@app.post("/api/position/legal-moves")
async def position_legal_moves(body: Dict[str, Any]) -> Dict[str, Any]:
    fen = body.get("fen", "")
    try:
        state = fen_to_board(fen)
    except Exception:
        raise HTTPException(status_code=400, detail="FEN invalide")
    moves = get_legal_moves(state)
    return {"moves": [{"path": m.path, "captures": m.captures} for m in moves]}


@app.post("/api/position/apply-move")
async def position_apply_move(body: Dict[str, Any]) -> Dict[str, Any]:
    fen = body.get("fen", "")
    path = body.get("path", [])
    try:
        state = fen_to_board(fen)
    except Exception:
        raise HTTPException(status_code=400, detail="FEN invalide")
    legal = get_legal_moves(state)
    move = next((m for m in legal if m.path == path), None)
    if move is None:
        raise HTTPException(status_code=400, detail="Coup illégal")
    new_state = apply_move(state, move)
    result = game_result(new_state)
    next_legal = get_legal_moves(new_state) if result is None else []
    return {
        "fen": board_to_fen(new_state),
        "moves": [{"path": m.path, "captures": m.captures} for m in next_legal],
    }


@app.get("/api/auth/me/lessons/read")
async def get_read_lessons(current_user: Dict[str, Any] = Depends(_require_auth)) -> Dict[str, Any]:
    chapters = await get_user_read_lesson_chapters(current_user["id"])
    return {"read_chapters": chapters}


@app.post("/api/auth/me/lessons/{chapter}/read")
async def mark_lesson_read_endpoint(
    chapter: int,
    current_user: Dict[str, Any] = Depends(_require_auth),
) -> Dict[str, Any]:
    await mark_lesson_read(current_user["id"], chapter)
    return {"ok": True}


@app.get("/api/lessons")
async def list_lessons() -> Dict[str, Any]:
    import json as _json_mod, os as _os
    lessons_path = _os.path.join(_os.path.dirname(__file__), "lessons.json")
    try:
        with open(lessons_path, encoding="utf-8") as f:
            lessons = _json_mod.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Lessons file not found")
    return {ch: {"title": v["title"], "category": v["category"]} for ch, v in lessons.items()}


@app.get("/api/lessons/{chapter}")
async def get_lesson(chapter: int) -> Dict[str, Any]:
    import json as _json_mod, os as _os
    lessons_path = _os.path.join(_os.path.dirname(__file__), "lessons.json")
    try:
        with open(lessons_path, encoding="utf-8") as f:
            lessons = _json_mod.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Lessons file not found")
    lesson = lessons.get(str(chapter))
    if not lesson:
        raise HTTPException(status_code=404, detail=f"No lesson for chapter {chapter}")
    return lesson


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


@app.post("/api/pdn/import")
async def import_pdn_game(body: Dict[str, Any]) -> Dict[str, Any]:
    import re as _re
    pdn_text = body.get("pdn", "").strip()
    if not pdn_text:
        raise HTTPException(status_code=400, detail="PDN vide")

    # Extract metadata from [Tag "value"] headers
    metadata: Dict[str, str] = {}
    for m in _re.finditer(r'\[(\w+)\s+"([^"]*)"\]', pdn_text):
        metadata[m.group(1).lower()] = m.group(2)

    # Strip headers, curly-brace comments, semicolon comments
    moves_text = _re.sub(r'\[.*?\]', '', pdn_text, flags=_re.DOTALL)
    moves_text = _re.sub(r'\{[^}]*\}', '', moves_text)
    moves_text = _re.sub(r';[^\n]*', '', moves_text)

    # Collect move tokens (skip "1." / "12..." numbering and result strings)
    result_tokens = {'1-0', '0-1', '1/2-1/2', '*', '2-0', '0-2', '1-1'}
    move_tokens: List[str] = []
    for tok in moves_text.split():
        if _re.match(r'^\d+\.+$', tok):
            continue
        if tok in result_tokens:
            continue
        if _re.match(r'^\d+[-x]\d', tok):
            move_tokens.append(tok)

    if not move_tokens:
        raise HTTPException(status_code=400, detail="Aucun coup trouvé dans le PDN")

    # Replay from initial position, collecting a FEN snapshot after each move
    state = initial_state()
    positions = [{"fen": board_to_fen(state), "notation": None, "move_number": 0, "color": None}]

    for i, pdn_move in enumerate(move_tokens):
        legal = get_legal_moves(state)
        move = _find_move_by_pdn(pdn_move, legal)
        if move is None:
            raise HTTPException(
                status_code=422,
                detail=f"Coup illisible ou illégal : '{pdn_move}' (coup n°{i + 1})"
            )
        state = apply_move(state, move)
        positions.append({
            "fen": board_to_fen(state),
            "notation": move_to_pdn(move),
            "move_number": i // 2 + 1,
            "color": "white" if i % 2 == 0 else "black",
        })

    return {"positions": positions, "metadata": metadata, "total_moves": len(move_tokens)}


@app.post("/api/pdn/annotate")
async def annotate_game_positions(body: Dict[str, Any]) -> Dict[str, Any]:
    """Batch position evaluation using the native Scan engine.
    Returns evaluations for every position or available=false if Scan is not installed."""
    from scan_engine import _get_engine, _build_pos
    import asyncio

    positions = body.get("positions", [])
    ms_per_move = min(max(int(body.get("ms_per_move", 200)), 50), 8000)

    engine = _get_engine()
    if engine is None:
        return {"evaluations": None, "available": False}

    movetime_s = ms_per_move / 1000.0

    def run_batch() -> tuple:
        from opening_eval_db import lookup as cached_lookup
        results = []
        cache_hits = 0
        for i, pos_data in enumerate(positions):
            fen = pos_data.get("fen", "")
            if not fen:
                results.append({"score": 0, "bestMove": None})
                continue
            # Check pre-computed cache first (populated by /api/opening-book/precompute)
            hit = cached_lookup(fen)
            if hit:
                results.append({"score": hit["score"], "bestMove": hit["bestMove"]})
                cache_hits += 1
                continue
            state = fen_to_board(fen)
            hub_pos = _build_pos(state)
            result = engine.evaluate_pos(hub_pos, movetime_s)
            ev = result or {"score": 0, "bestMove": None}
            results.append(ev)
        return results, cache_hits

    evaluations, cache_hits = await asyncio.get_event_loop().run_in_executor(None, run_batch)
    non_zero = sum(1 for e in evaluations if e["score"] != 0)
    logging.info("annotate done: %d positions, %d cache hits, %d non-zero scores",
                 len(evaluations), cache_hits, non_zero)
    return {"evaluations": evaluations, "available": True, "cache_hits": cache_hits}


@app.post("/api/opening-book/precompute")
async def precompute_positions(body: Dict[str, Any]) -> Dict[str, Any]:
    """Deep evaluation of a game's positions, stored in the opening eval cache.
    Uses more time per position than the live annotate endpoint so Scan reaches
    higher depth. Cached results are reused instantly on future annotation calls."""
    from scan_engine import _get_engine, _build_pos
    from opening_eval_db import lookup as cached_lookup, store as cache_store, size as cache_size
    import asyncio

    positions = body.get("positions", [])
    if not positions:
        return {"success": False, "error": "No positions provided"}

    engine = _get_engine()
    if engine is None:
        return {"success": False, "error": "Scan non disponible"}

    # Allocate up to 10 s/position, total budget 280 s so we stay under HTTP timeout
    ms_per_pos = min(10000, max(3000, 280000 // max(len(positions), 1)))
    movetime_s = ms_per_pos / 1000.0
    logging.info("precompute: %d positions, %.1f s each (total ~%.0f s)", len(positions), movetime_s, len(positions) * movetime_s)

    def run() -> list:
        new_entries: list[dict] = []
        all_results: list[dict] = []
        for i, pos_data in enumerate(positions):
            fen = pos_data.get("fen", "")
            if not fen:
                all_results.append({"score": 0, "bestMove": None})
                continue
            # Skip positions already in cache
            existing = cached_lookup(fen)
            if existing:
                logging.info("precompute pos %d/%d: already cached score=%d", i, len(positions)-1, existing["score"])
                all_results.append({"score": existing["score"], "bestMove": existing["bestMove"]})
                continue
            state = fen_to_board(fen)
            hub_pos = _build_pos(state)
            ev = engine.evaluate_pos(hub_pos, movetime_s) or {"score": 0, "bestMove": None}
            entry = {"fen": fen, "score": ev["score"], "bestMove": ev["bestMove"]}
            new_entries.append(entry)
            all_results.append({"score": ev["score"], "bestMove": ev["bestMove"]})
            logging.info("precompute pos %d/%d: score=%d best=%s", i, len(positions)-1, ev["score"], ev["bestMove"])
        if new_entries:
            cache_store(new_entries)
        return all_results

    evaluations = await asyncio.get_event_loop().run_in_executor(None, run)
    return {
        "success": True,
        "computed": len(evaluations),
        "cache_size": cache_size(),
        "evaluations": evaluations,
    }


@app.get("/api/opening-book/players")
async def find_players_by_rating(
    rating_min: int = Query(1600, ge=500, le=2800),
    rating_max: int = Query(2200, ge=500, le=2800),
    count: int = Query(10, ge=1, le=500),
    perf_type: str = Query("standard"),
) -> Dict[str, Any]:
    """Return randomly-sampled Lidraughts players within a rating range."""
    from lidraughts_fetcher import fetch_players_by_rating
    if rating_min >= rating_max:
        raise HTTPException(status_code=400, detail="rating_min doit être < rating_max")
    players = fetch_players_by_rating(rating_min, rating_max, count, perf_type)
    return {"players": players, "found": len(players)}


@app.post("/api/opening-book/build")
async def start_cache_build(body: Dict[str, Any]) -> Dict[str, Any]:
    """Start a background job that evaluates opening positions.
    Accepts either usernames (server fetches from Lidraughts) or
    pdn_texts (PDN already downloaded by the browser client).
    """
    import cache_builder
    usernames: List[str] = body.get("usernames", [])
    pdn_texts: List[str] = body.get("pdn_texts", [])
    if not usernames and not pdn_texts:
        raise HTTPException(status_code=400, detail="Fournir 'usernames' ou 'pdn_texts'")
    max_games = min(int(body.get("max_games_per_user", 100)), 500)
    max_moves = min(int(body.get("max_moves", 12)), 20)
    ms_per_pos = min(max(int(body.get("ms_per_position", 5000)), 1000), 15000)
    started = cache_builder.start(usernames, max_games, max_moves, ms_per_pos, pdn_texts or None)
    if not started:
        return {"started": False, "message": "Un calcul est déjà en cours"}
    src = f"{len(pdn_texts)} lots PDN" if pdn_texts else f"{len(usernames)} joueurs"
    logging.info("cache_builder started: %s max_moves=%d ms=%d", src, max_moves, ms_per_pos)
    return {"started": True, "message": f"Calcul lancé ({src})"}


@app.get("/api/opening-book/build/status")
async def get_cache_build_status() -> Dict[str, Any]:
    """Poll the status of the background opening cache build job."""
    import cache_builder
    from opening_eval_db import size as cache_size
    status = cache_builder.get_status()
    status["cache_size"] = cache_size()
    return status


@app.get("/api/opening-book/continuations")
async def get_opening_continuations(fen: str = Query(...)) -> Dict[str, Any]:
    """Return sorted continuation moves for a given FEN with frequency and eval."""
    from opening_eval_db import lookup
    entry = lookup(fen)
    if not entry:
        return {"fen": fen, "total_games": 0, "continuations": [],
                "engine_best": None, "engine_score": 0}

    raw_cont: dict = entry.get("cont", {})
    total_games = sum(raw_cont.values()) if raw_cont else 0

    if not raw_cont:
        return {"fen": fen, "total_games": 0, "continuations": [],
                "engine_best": entry.get("bestMove"), "engine_score": entry.get("score", 0)}

    try:
        state = fen_to_board(fen)
        legal = get_legal_moves(state)
    except Exception:
        return {"fen": fen, "total_games": 0, "continuations": [],
                "engine_best": entry.get("bestMove"), "engine_score": entry.get("score", 0)}

    continuations = []
    for move_pdn, freq in sorted(raw_cont.items(), key=lambda x: -x[1]):
        move_obj = _find_move_by_pdn(move_pdn, legal)
        score = None
        if move_obj:
            try:
                next_state = apply_move(state, move_obj)
                next_fen = board_to_fen(next_state)
                next_entry = lookup(next_fen)
                if next_entry and next_entry.get("score") is not None:
                    score = -next_entry["score"]  # negate: opponent's score → our score
            except Exception:
                pass
        continuations.append({
            "move": move_pdn,
            "frequency": freq,
            "pct": round(freq / total_games * 100) if total_games else 0,
            "score": score,
        })

    return {
        "fen": fen,
        "total_games": total_games,
        "continuations": continuations,
        "engine_best": entry.get("bestMove"),
        "engine_score": entry.get("score", 0),
    }


@app.post("/api/opening-book/ingest")
async def ingest_pdn(body: Dict[str, Any]) -> Dict[str, Any]:
    """Receive one player's raw PDN or NDJSON text, extract FENs into pending pool."""
    import cache_builder
    raw: str = body.get("raw", "")
    max_moves: int = min(int(body.get("max_moves", 12)), 20)
    try:
        result = cache_builder.ingest_raw(raw, max_moves)
        return result
    except Exception as exc:
        logging.exception("ingest_raw error (raw[:80]=%s)", raw[:80] if raw else "")
        return {"games": 0, "fens_added": 0, "format": "error", "error": str(exc)}


@app.post("/api/opening-book/start-eval")
async def start_eval(body: Dict[str, Any]) -> Dict[str, Any]:
    """Start Scan evaluation on all FENs collected via /ingest calls."""
    import cache_builder
    ms_per_pos: int = min(max(int(body.get("ms_per_position", 5000)), 1000), 15000)
    started = cache_builder.start_eval(ms_per_pos)
    if not started:
        s = cache_builder.get_status()
        if s.get("status") == "running":
            return {"started": False, "message": "Un calcul est déjà en cours"}
        return {"started": False, "message": "Aucune position en attente d'évaluation"}
    return {"started": True, "message": "Évaluation Scan démarrée en arrière-plan"}


async def position_analyze(body: Dict[str, Any]) -> AnalysisResponse:
    fen = body.get("fen", "")
    question = body.get("question") or None
    language = body.get("language", "fr")
    mode = body.get("mode", "position")
    pdn_history: List[str] = body.get("move_history") or []
    try:
        state = fen_to_board(fen)
    except Exception:
        raise HTTPException(status_code=400, detail="FEN invalide")
    if mode == "full_game":
        result = await analyze_full_game_pdn(state, pdn_history, language)
    else:
        if language == 'en':
            context_note = ("Note: this position comes from an imported PDN game. "
                            "The FEN is correct and valid. ")
        else:
            context_note = ("Note : cette position est extraite d'une partie importée au format PDN. "
                            "Le FEN est correct et la position est valide. ")
        effective_question = context_note + (question or "")
        result = await analyze_position(state, [], effective_question, language)
    return AnalysisResponse(**result)


@app.post("/api/position/best-move")
async def position_best_move(body: Dict[str, Any]) -> Dict[str, Any]:
    fen = body.get("fen", "")
    depth = int(body.get("depth", 6))
    try:
        state = fen_to_board(fen)
    except Exception:
        raise HTTPException(status_code=400, detail="FEN invalide")
    loop = asyncio.get_event_loop()
    move = await loop.run_in_executor(None, lambda: get_scan_move(state, depth))
    if move is None:
        return {"move": None}
    return {"move": move_to_pdn(move)}


_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(_STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(_STATIC_DIR, "assets")), name="assets")

    # Serve Scan WASM engine files with correct MIME types (iOS Safari is strict)
    _WASM_CACHE = "public, max-age=604800, immutable"

    @app.get("/scan_normal.wasm.js")
    async def serve_scan_js() -> FileResponse:
        return FileResponse(
            os.path.join(_STATIC_DIR, "scan_normal.wasm.js"),
            media_type="application/javascript",
            headers={"Cache-Control": _WASM_CACHE},
        )

    @app.get("/scan_normal.wasm")
    async def serve_scan_wasm() -> FileResponse:
        return FileResponse(
            os.path.join(_STATIC_DIR, "scan_normal.wasm"),
            media_type="application/wasm",
            headers={"Cache-Control": _WASM_CACHE},
        )

    @app.get("/scan_normal.data")
    async def serve_scan_data() -> FileResponse:
        return FileResponse(
            os.path.join(_STATIC_DIR, "scan_normal.data"),
            media_type="application/octet-stream",
            headers={"Cache-Control": _WASM_CACHE},
        )

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        return FileResponse(
            os.path.join(_STATIC_DIR, "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
