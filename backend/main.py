from __future__ import annotations
import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI, HTTPException, Query
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
from database import init_db, save_game, get_games, get_game, get_exercises, get_exercise, record_progress
from models import (
    NewGameRequest, MoveRequest, AnalyzeRequest,
    GameStateResponse, MoveResponse, LegalMovesResponse,
    ExerciseResponse, ExerciseCheckRequest, ExerciseCheckResponse,
    AnalysisResponse, HistoryResponse, HistoryItem, GameDetailResponse,
)

load_dotenv()

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
    return [ExerciseResponse(**ex) for ex in exercises]


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
async def exercise_legal_moves_endpoint(exercise_id: int) -> Dict[str, Any]:
    ex = await get_exercise(exercise_id)
    if ex is None:
        raise HTTPException(status_code=404, detail="Exercice introuvable")
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
async def check_exercise(exercise_id: int, req: ExerciseCheckRequest) -> ExerciseCheckResponse:
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
