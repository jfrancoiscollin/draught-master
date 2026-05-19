"""FastAPI router for the live PvP module.

J1 surface: challenges only (queue + accept/decline). The WebSocket
endpoint and the in-flight game state machine land on later days and
will live alongside this router.
"""

from __future__ import annotations

from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

try:
    from auth import current_user  # absolute when backend/ is on sys.path
except ImportError:
    from ..auth import current_user  # type: ignore[assignment]

from . import storage
from .models import (
    ChallengeCreateRequest,
    ChallengeOut,
    ChallengeRespondRequest,
    PendingChallengesResponse,
)

router = APIRouter(prefix="/api/live", tags=["live"])


def _db_path() -> str:
    """Same lookup as pedagogy/api.py — keeps the live module
    decoupled from the rest of the import graph."""
    try:
        from db.config import DB_PATH  # absolute (backend/ on sys.path)
        return DB_PATH
    except ImportError:
        from ..db.config import DB_PATH  # type: ignore[assignment]
        return DB_PATH


def _row_to_out(row: dict[str, Any]) -> ChallengeOut:
    return ChallengeOut(**row)


# ---------------------------------------------------------------------------
# POST /api/live/challenge
# ---------------------------------------------------------------------------


@router.post("/challenge", response_model=ChallengeOut)
async def create_challenge(
    req: ChallengeCreateRequest,
    user: Any = Depends(current_user),
) -> ChallengeOut:
    """Issue a challenge to ``opponent_username``.

    Rejects:
      - opponent doesn't exist (404)
      - opponent is the caller themself (422)
      - caller already has a pending challenge to the same opponent (409)
    """
    challenger_id = int(user["id"])

    async with aiosqlite.connect(_db_path()) as conn:
        opp = await storage.find_user_by_username(conn, req.opponent_username)
        if opp is None:
            raise HTTPException(404, f"Aucun joueur ne s'appelle {req.opponent_username!r}")
        if opp["id"] == challenger_id:
            raise HTTPException(422, "On ne peut pas se défier soi-même")

        # Prevent duplicate-pending: spamming "Défier" would otherwise
        # let one user clutter another's inbox.
        dup_cur = await conn.execute(
            """
            SELECT id FROM live_challenges
             WHERE challenger_id = ? AND opponent_id = ? AND status = 'pending'
             LIMIT 1
            """,
            (challenger_id, opp["id"]),
        )
        if await dup_cur.fetchone() is not None:
            raise HTTPException(409, "Tu as déjà un défi en attente vers ce joueur")

        cid = await storage.insert_challenge(
            conn,
            challenger_id=challenger_id,
            opponent_id=opp["id"],
            preferred_color=req.preferred_color,
        )
        row = await storage.fetch_challenge(conn, cid)
        assert row is not None
    return _row_to_out(row)


# ---------------------------------------------------------------------------
# GET /api/live/challenges/pending
# ---------------------------------------------------------------------------


@router.get("/challenges/pending", response_model=PendingChallengesResponse)
async def list_pending_challenges(
    user: Any = Depends(current_user),
) -> PendingChallengesResponse:
    """Bootstrap query for the live lobby UI: pending challenges I
    received + pending challenges I sent. Pruned to status='pending';
    accepted / declined / expired ones drop off the list automatically."""
    async with aiosqlite.connect(_db_path()) as conn:
        received, sent = await storage.fetch_pending_for_user(conn, int(user["id"]))
    return PendingChallengesResponse(
        received=[_row_to_out(r) for r in received],
        sent=[_row_to_out(r) for r in sent],
    )


# ---------------------------------------------------------------------------
# POST /api/live/challenge/{id}/respond
# ---------------------------------------------------------------------------


@router.post("/challenge/{challenge_id}/respond", response_model=ChallengeOut)
async def respond_challenge(
    challenge_id: str,
    req: ChallengeRespondRequest,
    user: Any = Depends(current_user),
) -> ChallengeOut:
    """Accept or decline a pending challenge.

    Only the opponent can respond. Acceptance transitions the challenge
    to 'accepted' and (in a later day) spawns a live game; for now we
    just stamp the status — the game-creation handshake comes with the
    WebSocket layer on J3. The `game_id` field of the response stays
    null until then.
    """
    user_id = int(user["id"])

    async with aiosqlite.connect(_db_path()) as conn:
        row = await storage.fetch_challenge(conn, challenge_id)
        if row is None:
            raise HTTPException(404, "Défi introuvable")
        if row["opponent_id"] != user_id:
            # Don't leak whether the challenge exists at all — same
            # response shape as a missing one. (Soft policy: 403 is
            # also fine, but 404 hides the existence.)
            raise HTTPException(404, "Défi introuvable")
        if row["status"] != "pending":
            raise HTTPException(409, f"Ce défi a déjà été {row['status']}")

        new_status = "accepted" if req.accept else "declined"
        await storage.update_status(conn, challenge_id, new_status)
        refreshed = await storage.fetch_challenge(conn, challenge_id)
        assert refreshed is not None
    return _row_to_out(refreshed)


# ---------------------------------------------------------------------------
# POST /api/live/challenge/{id}/cancel
# ---------------------------------------------------------------------------


@router.post("/challenge/{challenge_id}/cancel", response_model=ChallengeOut)
async def cancel_challenge(
    challenge_id: str,
    user: Any = Depends(current_user),
) -> ChallengeOut:
    """Challenger withdraws a still-pending challenge. Mirror of
    /respond but reserved to the challenger; the opponent must use
    /respond with accept=false to decline."""
    user_id = int(user["id"])

    async with aiosqlite.connect(_db_path()) as conn:
        row = await storage.fetch_challenge(conn, challenge_id)
        if row is None:
            raise HTTPException(404, "Défi introuvable")
        if row["challenger_id"] != user_id:
            raise HTTPException(404, "Défi introuvable")
        if row["status"] != "pending":
            raise HTTPException(409, f"Ce défi a déjà été {row['status']}")
        await storage.update_status(conn, challenge_id, "cancelled")
        refreshed = await storage.fetch_challenge(conn, challenge_id)
        assert refreshed is not None
    return _row_to_out(refreshed)
