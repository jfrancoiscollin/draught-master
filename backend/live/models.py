"""Pydantic models for the /api/live/* routes."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------

PreferredColor = Literal["white", "black", "random"]
ChallengeStatus = Literal["pending", "accepted", "declined", "expired", "cancelled"]


class ChallengeCreateRequest(BaseModel):
    """Body of POST /api/live/challenge.

    The opponent is identified by username (case-insensitive lookup
    server-side) — the frontend doesn't get to know other users' ids.
    """

    opponent_username: str = Field(min_length=1, max_length=64)
    preferred_color: PreferredColor = "random"


class ChallengeRespondRequest(BaseModel):
    """Body of POST /api/live/challenge/{id}/respond."""

    accept: bool


class ChallengeOut(BaseModel):
    """One row of the challenge queue, viewable by either party."""

    id: str
    challenger_id: int
    challenger_username: str
    opponent_id: int
    opponent_username: str
    preferred_color: PreferredColor
    status: ChallengeStatus
    created_at: str
    resolved_at: Optional[str] = None
    # Set when accepted — the live game spawned from this challenge.
    game_id: Optional[str] = None


class PendingChallengesResponse(BaseModel):
    """Bundles the two queues a logged-in user cares about."""

    received: list[ChallengeOut]   # challenges where I am opponent + status='pending'
    sent: list[ChallengeOut]       # challenges I issued + status='pending'


# ---------------------------------------------------------------------------
# Online users
# ---------------------------------------------------------------------------


class OnlineUserOut(BaseModel):
    """One row of the live lobby's "Joueurs connectés" list."""

    user_id: int
    username: str
    # True when this user is already in an in-progress live game.
    # The frontend renders the Défier button disabled in that case.
    in_game: bool


class OnlineUsersResponse(BaseModel):
    users: list[OnlineUserOut]


# ---------------------------------------------------------------------------
# Active live game lookup
# ---------------------------------------------------------------------------


class ActiveGameSessionOut(BaseModel):
    """Same wire shape as the session dict shipped in game_started /
    move_played / game_ended frames — kept identical so the frontend
    can reuse one TS type. Used by GET /api/live/my-active-game as a
    fallback for clients that missed the in-memory game_started push
    (multi-replica deploys, transient WS drops, hard refresh between
    turns)."""

    game_id: str
    white_user_id: int
    black_user_id: int
    turn: str
    status: str
    result: Optional[str] = None
    pdn: str
    fen: str
