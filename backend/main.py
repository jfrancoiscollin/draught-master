from __future__ import annotations
import asyncio
import logging
import os
import secrets
import smtplib
import ssl
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO)

import hmac
import hashlib
import base64
import json as _json
from passlib.context import CryptContext
from fastapi import FastAPI, HTTPException, Query, Depends, Request
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
    init_db, save_game, save_imported_game, save_game_annotations, get_user_stats,
    count_user_games_by_source,
    get_games, get_game,
    save_active_game, load_active_game, delete_active_game,
    get_exercises, get_exercise, record_progress,
    create_user, get_user_by_email, get_user_by_id, set_lidraughts_username,
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

_SENTRY_DSN = os.getenv("SENTRY_DSN")
if _SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
    logging.getLogger(__name__).info("Sentry initialized")

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


app = FastAPI(title="AI-Draught API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pedagogy.api import router as pedagogy_router  # noqa: E402
app.include_router(pedagogy_router)

from live import router as live_router  # noqa: E402
app.include_router(live_router)

# Shared BookRAG singleton — populated at startup if corpus is present.
# `explain_verdict` degrades gracefully to template mode when None.
shared_book_rag = None

game_store: Dict[str, Dict[str, Any]] = {}


@app.on_event("startup")
async def startup_event() -> None:
    await init_db()
    global shared_book_rag
    try:
        from pathlib import Path
        from pedagogy.explanations.book_rag import BookRAG
        corpus = Path(__file__).parent.parent / "docs" / "corpus"
        if corpus.exists():
            shared_book_rag = BookRAG.from_directory(str(corpus))
    except Exception:
        pass  # corpus not present or scikit-learn not installed

    # Auto-tag exercises with dilf motif detectors (idempotent, non-blocking).
    async def _auto_tag_exercises() -> None:
        try:
            from pedagogy.scripts.tag_existing_exercises import _run as _tag_run
            await _tag_run(only_ids=None, dry_run=False)
            logging.info("startup: exercise tags refreshed")
        except Exception:
            logging.exception("startup: exercise auto-tagging failed (non-fatal)")

    asyncio.create_task(_auto_tag_exercises())


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


def _make_limiter(max_calls: int, window: int):
    """Return a FastAPI dependency that enforces a sliding-window rate limit per IP.

    Using a factory (plain function) rather than a callable class avoids a
    Pydantic forward-reference resolution bug that occurs with
    `from __future__ import annotations`: Pydantic resolves annotations of a
    class `__call__` in the class namespace rather than the module globals,
    causing `NameError: name 'Request' is not defined` at startup.
    """
    calls: defaultdict = defaultdict(deque)
    lock = asyncio.Lock()

    async def _check(request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        async with lock:
            q = calls[key]
            while q and q[0] < now - window:
                q.popleft()
            if len(q) >= max_calls:
                raise HTTPException(
                    status_code=429,
                    detail="Trop de requêtes. Réessayez dans quelques secondes.",
                )
            q.append(now)

    return _check


# 5 Claude analyses / minute / IP
_analysis_limiter = _make_limiter(max_calls=5, window=60)
# 20 Scan move requests / minute / IP
_scan_limiter = _make_limiter(max_calls=20, window=60)
# 3 heavy batch operations / minute / IP
_batch_limiter = _make_limiter(max_calls=3, window=60)


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
        "user_id": entry.get("user_id"),
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
        "user_id": d.get("user_id"),
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
async def new_game(
    req: NewGameRequest,
    current_user: Optional[Dict[str, Any]] = Depends(_optional_auth),
) -> GameStateResponse:
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
        "user_id": current_user["id"] if current_user else None,
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
    _cur_fen = board_to_fen(state)
    entry["fen_positions"].append(_cur_fen)

    if entry["fen_positions"].count(_cur_fen) >= 3:
        result = "draw"
    else:
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
            _ai_fen = board_to_fen(state)
            entry["fen_positions"].append(_ai_fen)
            ai_move_data = {"path": ai_move.path, "captures": ai_move.captures}
            if entry["fen_positions"].count(_ai_fen) >= 3:
                result = "draw"
            else:
                result = game_result(state)

    if result is not None:
        pdn = _build_pdn(state.move_history)
        try:
            await save_game(
                game_id=game_id,
                date=entry["date"],
                white_player=entry["white_player"],
                black_player=entry["black_player"],
                result=result,
                pdn=pdn,
                fen_positions=entry["fen_positions"],
                move_count=len(state.move_history),
                user_id=entry.get("user_id"),
            )
            await delete_active_game(game_id)
        except Exception:
            logging.exception("save_game failed for game %s (result=%s)", game_id, result)
    else:
        try:
            await save_active_game(game_id, _serialize_entry(entry))
        except Exception:
            logging.exception("save_active_game failed for game %s", game_id)

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
async def resign_game(
    game_id: str,
    req: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entry = await _get_game_entry(game_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    state: GameState = entry["state"]

    # If game already finished (e.g. race condition), return current result gracefully
    existing_result = game_result(state)
    if existing_result is not None:
        return {"result": existing_result}

    # Determine who resigned to compute winner correctly
    user_side = (req or {}).get("user_side", "white")
    result = "black" if user_side == "white" else "white"

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
        user_id=entry.get("user_id"),
    )
    await delete_active_game(game_id)
    return {"result": result}


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
    game_id: str, depth: int = Query(4),
    _rl: None = Depends(_scan_limiter),
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
async def analyze(
    game_id: str, req: AnalyzeRequest,
    _rl: None = Depends(_analysis_limiter),
) -> AnalysisResponse:
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
    book_id: Optional[str] = Query(None),
) -> List[ExerciseResponse]:
    exercises = await get_exercises(category=category, difficulty=difficulty, book_id=book_id)
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
    current_user: Optional[Dict[str, Any]] = Depends(_optional_auth),
) -> HistoryResponse:
    offset = (page - 1) * page_size
    user_id = current_user["id"] if current_user else None
    games = await get_games(limit=page_size, offset=offset, user_id=user_id)
    items = [
        HistoryItem(
            id=g["id"],
            date=g["date"],
            white_player=g["white_player"],
            black_player=g["black_player"],
            result=g.get("result"),
            move_count=g.get("move_count", 0),
            has_scan_analysis=bool(g.get("has_scan_analysis", 0)),
            has_dilf_analysis=bool(g.get("has_dilf_analysis", 0)),
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
    user = await get_user_by_id(current_user["id"])
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        lidraughts_username=(user or {}).get("lidraughts_username"),
    )


@app.get("/api/auth/me/progress")
async def auth_me_progress(current_user: Dict[str, Any] = Depends(_require_auth)) -> Dict[str, Any]:
    solved_ids = await get_user_solved_exercise_ids(current_user["id"])
    return {"solved_exercise_ids": solved_ids}


@app.get("/api/auth/me/stats")
async def auth_me_stats(current_user: Dict[str, Any] = Depends(_require_auth)) -> Dict[str, Any]:
    stats = await get_user_stats(current_user["id"])
    return stats


@app.post("/api/auth/me/lidraughts/import")
async def auth_me_lidraughts_import(
    body: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(_require_auth),
) -> Dict[str, Any]:
    """Download the user's last N games from Lidraughts and store them
    in the database. Default N=50, capped at 100.
    """
    import re as _re
    import uuid as _uuid
    from datetime import datetime as _dt
    from lidraughts_fetcher import fetch_user_games_pdn, split_pdn_games

    raw_username = (body.get("username") or "").strip()
    try:
        count = int(body.get("count", 50))
    except (TypeError, ValueError):
        count = 50
    count = max(1, min(count, 100))

    db_user = await get_user_by_id(current_user["id"])
    if not raw_username:
        raw_username = ((db_user or {}).get("lidraughts_username") or "").strip()
    if not raw_username:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur Lidraughts manquant")
    if not _re.match(r"^[A-Za-z0-9_-]{2,30}$", raw_username):
        raise HTTPException(status_code=400, detail="Nom d'utilisateur Lidraughts invalide")

    # Persist the username so the user doesn't have to retype it next time.
    if (db_user or {}).get("lidraughts_username") != raw_username:
        await set_lidraughts_username(current_user["id"], raw_username)

    pdn_text = await asyncio.to_thread(fetch_user_games_pdn, raw_username, count)
    if not pdn_text:
        raise HTTPException(
            status_code=502,
            detail="Impossible de récupérer les parties depuis Lidraughts",
        )

    games_pdn = split_pdn_games(pdn_text)[:count]
    user_login = raw_username.lower()

    # Auto-cleanup of ghost rows left by the pre-PR #20 split_pdn_games
    # bug (one row per PDN tag fragment, white_player='?'). Without this
    # purge, those ghosts share the same source_id as real games and
    # cause dedup to silently swallow every fresh import. Scoped to the
    # current user. Idempotent : no-op once the DB is clean.
    try:
        import aiosqlite as _aiosqlite
        from db.config import DB_PATH as _DB_PATH
        async with _aiosqlite.connect(_DB_PATH) as _db:
            _cur = await _db.execute(
                "DELETE FROM games WHERE user_id = ? AND source = 'lidraughts' "
                "AND (white_player = '?' OR black_player = '?')",
                (current_user["id"],),
            )
            _purged = _cur.rowcount
            await _db.commit()
        if _purged > 0:
            logging.info(
                "lidraughts import: purged %d ghost row(s) for user %s",
                _purged, current_user["id"],
            )
    except Exception as exc:
        logging.warning("lidraughts import: ghost cleanup skipped: %s", exc)

    imported = 0
    skipped = 0
    for pdn in games_pdn:
        tags: Dict[str, str] = {}
        for m in _re.finditer(r'\[(\w+)\s+"([^"]*)"\]', pdn):
            tags[m.group(1).lower()] = m.group(2)
        site = tags.get("site", "")
        m_site = _re.search(r"lidraughts\.org/(\w+)", site)
        source_id = m_site.group(1) if m_site else (tags.get("gameid") or None)
        white_player = tags.get("white", "?")
        black_player = tags.get("black", "?")
        date_tag = tags.get("utcdate") or tags.get("date") or _dt.utcnow().date().isoformat()
        result_tag = tags.get("result", "")
        if result_tag in ("1-0", "2-0"):
            result = "white"
        elif result_tag in ("0-1", "0-2"):
            result = "black"
        elif result_tag in ("1/2-1/2", "1-1"):
            result = "draw"
        else:
            result = None
        if white_player.lower() == user_login:
            user_side = "white"
        elif black_player.lower() == user_login:
            user_side = "black"
        else:
            user_side = None
        # Scan only the moves section (after the last tag) and strip the
        # trailing result token so it isn't counted as a phantom move.
        # Without this, `1-0` / `2-0` / inner `2-1` in `1/2-1/2` would
        # inflate move_count by 1 (cf smoke_test_lidraughts_import.py).
        _move_section_match = _re.search(r"\][^\[]*$", pdn, _re.DOTALL)
        _move_section = _move_section_match.group(0) if _move_section_match else pdn
        _move_section = _re.sub(
            r"(1-0|0-1|2-0|0-2|1-1|2-1|1-2|1/2-1/2|\*)\s*$",
            "",
            _move_section.strip(),
        )
        move_tokens = _re.findall(r"\b\d+[-x]\d+(?:[-x]\d+)*\b", _move_section)
        game_id = source_id or _uuid.uuid4().hex
        try:
            inserted = await save_imported_game(
                game_id=game_id,
                user_id=current_user["id"],
                date=date_tag,
                white_player=white_player,
                black_player=black_player,
                result=result,
                pdn=pdn,
                move_count=len(move_tokens),
                source="lidraughts",
                source_id=source_id,
                user_side=user_side,
            )
            if inserted:
                imported += 1
            else:
                skipped += 1
        except Exception as exc:
            logging.warning("lidraughts import: failed to save game %s: %s", source_id, exc)
            skipped += 1

    total = await count_user_games_by_source(current_user["id"], "lidraughts")
    return {
        "requested": count,
        "fetched": len(games_pdn),
        "imported": imported,
        "skipped": skipped,
        "total_lidraughts_games": total,
        "username": raw_username,
    }


@app.post("/api/auth/me/analyses/reset")
async def auth_me_analyses_reset(
    current_user: Dict[str, Any] = Depends(_require_auth),
) -> Dict[str, Any]:
    """Wipe every persisted analysis for the current user's games :

    - clears `games.annotations_json` (legacy Scan per-move verdicts)
    - deletes every `move_verdicts` row tied to a game the user owns
      (the dilf pedagogy verdicts + motifs)

    The `games` rows themselves are kept — only the analysis layer is
    wiped, so the user can re-run "Analyser avec dilf" cleanly without
    losing their imported library.
    """
    import aiosqlite as _aiosqlite
    from db.config import DB_PATH as _DB_PATH

    async with _aiosqlite.connect(_DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM move_verdicts "
            "WHERE game_id IN (SELECT id FROM games WHERE user_id = ?)",
            (current_user["id"],),
        )
        verdicts_deleted = cur.rowcount
        cur = await db.execute(
            "UPDATE games SET annotations_json = NULL WHERE user_id = ?",
            (current_user["id"],),
        )
        games_cleared = cur.rowcount
        await db.commit()

    return {
        "verdicts_deleted": verdicts_deleted,
        "games_cleared": games_cleared,
    }


@app.post("/api/history/{game_id}/annotations")
async def save_annotations(
    game_id: str,
    body: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(_require_auth),
) -> Dict[str, Any]:
    annotations = body.get("annotations")
    if not isinstance(annotations, list):
        raise HTTPException(status_code=400, detail="annotations doit être une liste")
    await save_game_annotations(game_id, current_user["id"], annotations)
    return {"ok": True}


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
async def list_lessons(book: Optional[str] = Query(None)) -> Dict[str, Any]:
    # The Dubois static lessons were retired (see PR #7). The manuel
    # Débutant prose (`docs/manuels/debutant/manuel_debutant.md`) is now
    # the source. `book` is accepted for compat with the existing client
    # but only `manuel_debutant` has prose for now ; an empty mapping is
    # returned for any other value.
    from manuels.prose_loader import load_debutant_chapters
    if book not in (None, "manuel_debutant"):
        return {}
    chapters = load_debutant_chapters()
    return {ch: {"title": v["title"], "category": v["category"]} for ch, v in chapters.items()}


@app.get("/api/lessons/{chapter}")
async def get_lesson(chapter: int) -> Dict[str, Any]:
    from manuels.prose_loader import load_debutant_chapters
    chapters = load_debutant_chapters()
    lesson = chapters.get(str(chapter))
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
async def annotate_game_positions(
    body: Dict[str, Any],
    _rl: None = Depends(_batch_limiter),
) -> Dict[str, Any]:
    """Batch position evaluation using the native Scan engine.
    Returns evaluations for every position or available=false if Scan is not installed."""
    from scan_engine import _get_engine, _build_pos
    import asyncio

    positions = body.get("positions", [])
    ms_per_move = min(max(int(body.get("ms_per_move", 200)), 50), 8000)

    engine = _get_engine(use_book=False)  # no opening book so positions get real scores
    if engine is None:
        return {"evaluations": None, "available": False}

    movetime_s = ms_per_move / 1000.0

    def run_batch() -> tuple:
        try:
            from opening_book_db import lookup as cached_lookup, store as book_store
        except Exception as exc:
            logging.warning("opening_book_db unavailable: %s", exc)
            cached_lookup = lambda _fen: None  # noqa: E731
            book_store = lambda _entries: None  # noqa: E731

        results = []
        cache_hits = 0
        to_save: list[dict] = []

        for i, pos_data in enumerate(positions):
            fen = pos_data.get("fen", "")
            if not fen:
                results.append({"score": 0, "bestMove": None})
                continue
            # Check cache first — only trust non-zero scores (zero could be a
            # stale value from an older buggy analysis run).
            try:
                hit = cached_lookup(fen)
            except Exception:
                hit = None
            if hit is not None and hit.get("score") != 0:
                results.append({"score": hit["score"], "bestMove": hit.get("bestMove")})
                cache_hits += 1
                continue
            state = fen_to_board(fen)
            hub_pos = _build_pos(state)
            result = engine.evaluate_pos(hub_pos, movetime_s)
            ev = result or {"score": 0, "bestMove": None}
            logging.info("annotate pos %d/%d fen=%s score=%.3f best=%s",
                         i+1, len(positions), fen[:40], ev["score"], ev.get("bestMove"))
            results.append(ev)
            # Only cache non-zero scores — zero could be a genuine balance or
            # an engine miss; we don't want to freeze it in the DB indefinitely.
            if ev.get("score") != 0:
                to_save.append({"fen": fen, "score": ev["score"], "bestMove": ev.get("bestMove")})

        # Forced-move propagation (negamax): when a position had only one legal
        # move (forced capture), Scan returns score=0 without evaluating.
        # Derive its score from the resulting position: score(P) ≈ -score(P_next).
        for i in range(len(results) - 1):
            r = results[i]
            if r.get("forced") and r.get("score", 0) == 0:
                next_score = results[i + 1].get("score", 0)
                if next_score != 0:
                    results[i] = {"score": -next_score, "bestMove": r.get("bestMove")}
                    logging.info("annotate pos %d: forced-move score derived as %.3f", i + 1, -next_score)

        if to_save:
            try:
                book_store(to_save)
                logging.info("annotate: saved %d new positions to opening book cache", len(to_save))
            except Exception as exc:
                logging.warning("annotate: could not save to cache: %s", exc)

        return results, cache_hits

    evaluations, cache_hits = await asyncio.get_event_loop().run_in_executor(None, run_batch)
    non_zero = sum(1 for e in evaluations if e["score"] != 0)
    logging.info("annotate done: %d positions, %d cache hits, %d non-zero scores",
                 len(evaluations), cache_hits, non_zero)
    return {"evaluations": evaluations, "available": True, "cache_hits": cache_hits,
            "debug": {"non_zero_scores": non_zero, "total": len(evaluations)}}


@app.post("/api/opening-book/precompute")
async def precompute_positions(
    body: Dict[str, Any],
    _rl: None = Depends(_batch_limiter),
) -> Dict[str, Any]:
    """Deep evaluation of a game's positions, stored in the opening eval cache.
    Uses more time per position than the live annotate endpoint so Scan reaches
    higher depth. Cached results are reused instantly on future annotation calls."""
    from scan_engine import _get_engine, _build_pos
    from opening_book_db import lookup as cached_lookup, store as cache_store, size as cache_size
    import asyncio

    positions = body.get("positions", [])
    if not positions:
        return {"success": False, "error": "No positions provided"}

    engine = _get_engine(use_book=False)
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
    players, pool_size = fetch_players_by_rating(rating_min, rating_max, count, perf_type)
    return {"players": players, "found": len(players), "pool_size": pool_size}


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
    from opening_book_db import size as cache_size
    status = cache_builder.get_status()
    status["cache_size"] = cache_size()
    return status


# ── Exercise verification ─────────────────────────────────────────────────────

@app.post("/api/admin/verify-exercises")
async def start_exercise_verification(body: Dict[str, Any] = {}) -> Dict[str, Any]:
    """Start background exercise verification.
    Optionally uses Scan (use_scan=true) to compare best move vs stored solution."""
    import exercise_verifier
    use_scan = bool(body.get("use_scan", False))
    movetime = float(body.get("movetime", 0.3))
    started = exercise_verifier.start(use_scan=use_scan, movetime=movetime)
    return {"started": started, "message": "Vérification lancée" if started else "Déjà en cours"}


@app.get("/api/admin/verify-exercises/status")
async def get_exercise_verification_status() -> Dict[str, Any]:
    """Poll the status of the background exercise verification job."""
    import exercise_verifier
    return exercise_verifier.get_status()


@app.get("/api/opening-book/continuations")
async def get_opening_continuations(fen: str = Query(...)) -> Dict[str, Any]:
    """Return sorted continuation moves for a given FEN with frequency and eval."""
    from opening_book_db import lookup
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


@app.post("/api/opening-book/reeval")
async def reeval_unevaluated(body: Dict[str, Any] = {}) -> Dict[str, Any]:
    """Re-evaluate positions in the book that have no Scan score yet (best_move IS NULL).

    Useful after a server restart interrupted a build run. Picks up exactly where
    the previous job left off without re-downloading any games.

    Parameters (all optional):
      ms_per_position  int  default 5000  — thinking time in ms per position
      limit            int  default 0     — max positions to evaluate (0 = all)
    """
    import cache_builder
    from opening_book_db import get_unevaluated_fens
    ms_per_pos: int = min(max(int(body.get("ms_per_position", 5000)), 1000), 15000)
    limit: int = max(0, int(body.get("limit", 0)))

    pending = len(get_unevaluated_fens(limit=1))  # cheap check
    if pending == 0:
        return {"started": False, "message": "Toutes les positions sont déjà évaluées", "pending": 0}

    started = cache_builder.start_reeval(ms_per_pos, limit=limit)
    if not started:
        s = cache_builder.get_status()
        if s.get("status") == "running":
            return {"started": False, "message": "Un calcul est déjà en cours"}
        return {"started": False, "message": "Aucune position non-évaluée trouvée"}

    # Count how many we're about to evaluate so the UI can show a meaningful message
    from opening_book_db import get_unevaluated_fens as _guf
    total_pending = len(_guf(limit=limit)) if limit == 0 else limit
    return {"started": True, "message": f"Réévaluation de {total_pending} positions lancée en arrière-plan", "pending": total_pending}


@app.post("/api/opening-book/cleanup")
async def opening_book_cleanup(body: Dict[str, Any] = {}) -> Dict[str, Any]:
    """Remove low-quality positions from the opening book.

    Parameters (all optional):
      min_games       int   default 3   — drop positions seen in fewer games
      max_depth       int   default 40  — drop positions deeper than N half-moves
      min_cont_pct    float default 0.03 — drop moves with < 3% frequency
      min_cont_count  int   default 2   — drop moves seen fewer than N times
    """
    from opening_book_db import cleanup
    result = cleanup(
        min_games=int(body.get("min_games", 3)),
        max_depth=int(body.get("max_depth", 40)),
        min_cont_pct=float(body.get("min_cont_pct", 0.03)),
        min_cont_count=int(body.get("min_cont_count", 2)),
    )
    return result


@app.get("/api/opening-book/stats")
async def opening_book_stats() -> Dict[str, Any]:
    """Return summary statistics about the opening book."""
    from opening_book_db import stats
    return stats()


@app.get("/api/opening-book/db-info")
async def opening_book_db_info() -> Dict[str, Any]:
    """Return the DB path, file size, and row counts so you can verify
    that the Railway volume is correctly mounted and populated."""
    import os as _os
    from opening_book_db import _DB_PATH, stats as db_stats
    abs_path = _os.path.abspath(_DB_PATH)
    try:
        file_size = _os.path.getsize(abs_path)
    except FileNotFoundError:
        file_size = None
    try:
        book_stats = db_stats()
    except Exception as exc:
        book_stats = {"error": str(exc)}
    return {
        "db_path": abs_path,
        "env_override": _os.environ.get("OPENING_BOOK_DB") is not None,
        "file_exists": file_size is not None,
        "file_size_bytes": file_size,
        **book_stats,
    }


@app.post("/api/opening-book/migrate-json")
async def opening_book_migrate_json() -> Dict[str, Any]:
    """One-time migration from the old opening_eval_cache.json file."""
    from opening_book_db import migrate_from_json
    import os as _os
    json_path = _os.path.join(_os.path.dirname(__file__), "opening_eval_cache.json")
    return migrate_from_json(json_path)


@app.post("/api/opening-book/migrate-local-db")
async def opening_book_migrate_local_db() -> Dict[str, Any]:
    """One-time migration from the old local opening_book.db (ephemeral FS)
    to the current DB path (Railway volume). Safe to call if already migrated."""
    import os as _os
    import sqlite3 as _sqlite3
    from opening_book_db import _DB_PATH, store, store_continuations

    local_path = _os.path.join(_os.path.dirname(__file__), "opening_book.db")
    abs_local = _os.path.abspath(local_path)
    abs_target = _os.path.abspath(_DB_PATH)

    if abs_local == abs_target:
        return {"status": "same_path", "message": "Source and target are the same DB — nothing to migrate."}

    if not _os.path.exists(abs_local):
        return {"status": "no_source", "message": f"Local DB not found at {abs_local}"}

    try:
        src = _sqlite3.connect(abs_local)
        src.row_factory = _sqlite3.Row
        rows = src.execute(
            "SELECT fen, score, best_move, games_seen, depth FROM opening_book"
        ).fetchall()
        cont_rows = src.execute(
            "SELECT fen, move, count FROM opening_continuations"
        ).fetchall()
        src.close()
    except Exception as exc:
        return {"status": "error", "message": f"Could not read source DB: {exc}"}

    entries = [
        {"fen": r["fen"], "score": r["score"], "bestMove": r["best_move"], "depth": r["depth"]}
        for r in rows
    ]
    added = store(entries)

    # Rebuild cont_map from source continuations
    cont_map: Dict[str, Dict[str, int]] = {}
    fen_depths: Dict[str, int] = {r["fen"]: r["depth"] for r in rows}
    for r in cont_rows:
        cont_map.setdefault(r["fen"], {})[r["move"]] = r["count"]
    if cont_map:
        store_continuations(cont_map, fen_depths)

    return {
        "status": "ok",
        "source": abs_local,
        "target": abs_target,
        "source_positions": len(entries),
        "new_positions_added": added,
        "continuations_merged": len(cont_rows),
    }


@app.get("/api/opening-book/export-fens")
async def export_fens():
    """Export all known positions as a plain-text file, one FEN per line.

    Sources (deduplicated):
      1. opening_book table (positions from downloaded Lidraughts games)
      2. exercises table (exercise starting positions)
    """
    import os as _os
    from opening_book_db import _get_conn, _lock
    from fastapi.responses import PlainTextResponse

    lines: list[str] = ["# draught-master positions export", ""]

    # 1. Opening book FENs
    try:
        with _lock:
            conn = _get_conn()
            rows = conn.execute("SELECT fen FROM opening_book ORDER BY games_seen DESC").fetchall()
        book_fens = [r["fen"] for r in rows]
    except Exception:
        book_fens = []

    if book_fens:
        lines.append(f"# opening book ({len(book_fens)} positions)")
        lines.extend(book_fens)
        lines.append("")

    # 2. Exercise FENs
    try:
        ex_rows = await db.fetch_all("SELECT DISTINCT initial_fen FROM exercises WHERE initial_fen IS NOT NULL AND initial_fen != ''")
        ex_fens = [r["initial_fen"] for r in ex_rows]
    except Exception:
        ex_fens = []

    if ex_fens:
        lines.append(f"# exercises ({len(ex_fens)} positions)")
        lines.extend(ex_fens)
        lines.append("")

    total = len(book_fens) + len(ex_fens)
    lines.append(f"# total: {total} positions")

    return PlainTextResponse(
        content="\n".join(lines),
        headers={"Content-Disposition": 'attachment; filename="positions.fen"'},
    )


# ---------------------------------------------------------------------------
# Expert games corpus (NNUE training)
# ---------------------------------------------------------------------------

@app.post("/api/expert-games/ingest")
async def ingest_expert_games(body: Dict[str, Any]) -> Dict[str, Any]:
    """Receive raw Lidraughts NDJSON and store full games into expert_games.

    Body: { "ndjson": "<raw NDJSON string>" }
    Returns: { "inserted": N, "skipped": N, "errors": N }
    """
    from db.expert_games import ingest_ndjson
    ndjson: str = body.get("ndjson", "")
    if not ndjson or len(ndjson) < 10:
        return {"inserted": 0, "skipped": 0, "errors": 0}
    return await ingest_ndjson(ndjson)


@app.get("/api/expert-games/stats")
async def expert_games_stats() -> Dict[str, Any]:
    """Return aggregate statistics for the expert_games corpus."""
    from db.expert_games import get_stats
    return await get_stats()


def _scrape_lidraughts_seeds(nb_seeds: int = 30) -> list[str]:
    """Scrape lidraughts.org/player to extract top player usernames."""
    import re
    import requests as _req
    try:
        resp = _req.get("https://lidraughts.org/player", timeout=15,
                        headers={"Accept": "text/html"})
        if not resp.ok:
            return []
        # Lidraughts URLs use /@/username pattern
        names = re.findall(r'/@/([A-Za-z0-9_-]{2,30})', resp.text)
        seen: set[str] = set()
        result: list[str] = []
        for n in names:
            if n not in seen:
                seen.add(n)
                result.append(n)
        return result[:nb_seeds]
    except Exception:
        return []


@app.get("/api/lidraughts/top-players")
async def lidraughts_top_players(
    seeds: str = "",
    min_rating: int = 1800,
    nb: int = 200,
    max_games_per_seed: int = 30,
) -> Dict[str, Any]:
    """Discover strong players by fetching games from seed players in parallel."""
    import asyncio
    import json as _json
    import random
    import requests as _req

    # Auto-discover seeds from leaderboard if none provided
    seed_list = [s.strip() for s in seeds.split(",") if s.strip()]
    if not seed_list:
        seed_list = await asyncio.to_thread(_scrape_lidraughts_seeds, 60)
    # Shuffle so repeated clicks explore different subsets of the seed pool
    random.shuffle(seed_list)
    seed_list = seed_list[:25]  # up to 25 seeds per call, run in parallel
    if not seed_list:
        return {"players": [], "total": 0, "error": "Impossible de récupérer les seeds depuis lidraughts.org/player"}

    found: dict[str, int] = {}  # username → max rating seen

    def _fetch_games(username: str) -> str:
        url = (
            f"https://lidraughts.org/api/games/user/{username}"
            f"?max={max_games_per_seed}&rated=true"
        )
        try:
            r = _req.get(url, headers={"Accept": "application/x-ndjson"}, timeout=12)
            return r.text if r.ok else ""
        except Exception:
            return ""

    def _extract_opponents(text: str) -> None:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = _json.loads(line)
                for side in ("white", "black"):
                    p = obj.get("players", {}).get(side, {})
                    name = (p.get("user") or {}).get("name") or p.get("name") or ""
                    rating = p.get("rating") or (p.get("user") or {}).get("rating") or 0
                    if name and int(rating) >= min_rating:
                        found[name] = max(found.get(name, 0), int(rating))
            except Exception:
                pass

    # Hop 1 — fetch games of seed players in parallel
    texts = await asyncio.gather(*[asyncio.to_thread(_fetch_games, s) for s in seed_list])
    for text in texts:
        _extract_opponents(text)

    # Hop 2 — pick a random sample of newly discovered players as new seeds
    # to reach the wider player graph (players who never met the original seeds)
    hop2_candidates = [u for u in found if u not in set(seed_list)]
    if hop2_candidates:
        hop2_seeds = random.sample(hop2_candidates, min(15, len(hop2_candidates)))
        texts2 = await asyncio.gather(*[asyncio.to_thread(_fetch_games, s) for s in hop2_seeds])
        for text in texts2:
            _extract_opponents(text)

    sorted_players = sorted(found.items(), key=lambda x: -x[1])[:nb]
    players = [{"username": name, "rating": rating, "game_count": 0} for name, rating in sorted_players]

    # Batch-fetch rated game counts via POST /api/users
    def _fetch_counts(usernames: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for i in range(0, len(usernames), 100):
            batch = usernames[i:i + 100]
            try:
                r = _req.post(
                    "https://lidraughts.org/api/users",
                    data="\n".join(batch),
                    headers={"Content-Type": "text/plain", "Accept": "application/json"},
                    timeout=15,
                )
                if r.ok:
                    for u in r.json():
                        uname = (u.get("username") or u.get("id") or "").lower()
                        c = u.get("count") or {}
                        counts[uname] = int(c.get("rated") or c.get("all") or 0)
            except Exception:
                pass
        return counts

    if players:
        counts = await asyncio.to_thread(_fetch_counts, [p["username"] for p in players])
        for p in players:
            p["game_count"] = counts.get(p["username"].lower(), 0)
    return {"players": players, "total": len(players), "seeds_used": seed_list}


@app.post("/api/position/analyze", response_model=AnalysisResponse)
async def position_analyze(
    body: Dict[str, Any],
    _rl: None = Depends(_analysis_limiter),
) -> AnalysisResponse:
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
async def position_best_move(
    body: Dict[str, Any],
    _rl: None = Depends(_scan_limiter),
) -> Dict[str, Any]:
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
