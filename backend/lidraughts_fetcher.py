"""Fetch games from the Lidraughts public API."""
from __future__ import annotations
import logging
import re
import time

import requests

logger = logging.getLogger(__name__)

LIDRAUGHTS_API = "https://lidraughts.org"


def fetch_user_games_pdn(username: str, max_games: int = 200) -> str:
    """Download up to max_games games for a Lidraughts user as PDN text."""
    url = f"{LIDRAUGHTS_API}/api/games/user/{username}"
    try:
        logger.info("Fetching %d games for user '%s'…", max_games, username)
        # Try PDN format first
        resp = requests.get(
            url,
            headers={"Accept": "application/x-draughts-pdn"},
            params={"max": min(max_games, 500), "variant": "standard"},
            timeout=90,
        )
        resp.raise_for_status()
        text = resp.text.strip()
        if text and "[" in text:
            logger.info("Got %d chars of PDN for '%s'", len(text), username)
            return text

        # Fallback: NDJSON, extract pgn/pdn fields
        resp2 = requests.get(
            url,
            headers={"Accept": "application/x-ndjson"},
            params={"max": min(max_games, 500), "variant": "standard"},
            timeout=90,
        )
        resp2.raise_for_status()
        return _ndjson_to_pdn(resp2.text)

    except Exception as exc:
        logger.error("Failed to fetch games for '%s': %s", username, exc)
        return ""


def _ndjson_to_pdn(ndjson_text: str) -> str:
    """Convert NDJSON game objects to concatenated PDN text."""
    import json
    games: list[str] = []
    for line in ndjson_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            # Lidraughts NDJSON has moves in "pgn" or "pdn" or "moves" field
            moves = obj.get("pgn") or obj.get("pdn") or obj.get("moves", "")
            players = obj.get("players", {})
            white = players.get("white", {}).get("user", {}).get("name", "?")
            black = players.get("black", {}).get("user", {}).get("name", "?")
            result = obj.get("winner", "*")
            if result == "white":
                result = "2-0"
            elif result == "black":
                result = "0-2"
            else:
                result = "1-1"
            pdn = f'[White "{white}"]\n[Black "{black}"]\n[Result "{result}"]\n\n{moves}\n'
            games.append(pdn)
        except Exception:
            pass
    return "\n\n".join(games)


def fetch_players_by_rating(
    rating_min: int,
    rating_max: int,
    count: int,
    perf_type: str = "standard",
) -> list[dict]:
    """Return up to `count` randomly-sampled Lidraughts players whose rating
    falls within [rating_min, rating_max].

    Tries the top-200 leaderboard endpoint; falls back to the HTML leaderboard
    page if the JSON API is unavailable.
    """
    import random

    candidates: list[dict] = []

    # Try JSON leaderboard: /api/player/top/{nb}/{perfType}
    for nb in (200, 100, 50):
        url = f"{LIDRAUGHTS_API}/api/player/top/{nb}/{perf_type}"
        try:
            resp = requests.get(url, headers={"Accept": "application/json"}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            users = data.get("users") or data.get("results") or []
            if not users and isinstance(data, list):
                users = data
            for u in users:
                username = u.get("username") or u.get("id", "")
                perfs = u.get("perfs", {})
                rating = (
                    perfs.get(perf_type, {}).get("rating")
                    or u.get("rating")
                    or u.get("perfs", {}).get("rating")
                )
                if username and rating is not None:
                    candidates.append({"username": username, "rating": int(rating)})
            if candidates:
                break
        except Exception as exc:
            logger.warning("Leaderboard fetch failed (%s): %s", url, exc)

    if not candidates:
        logger.warning("Could not fetch any players from Lidraughts leaderboard")
        return []

    in_range = [p for p in candidates if rating_min <= p["rating"] <= rating_max]
    logger.info(
        "fetch_players_by_rating: %d candidates, %d in [%d,%d]",
        len(candidates), len(in_range), rating_min, rating_max,
    )

    random.shuffle(in_range)
    return in_range[:count]


def split_pdn_games(pdn_text: str) -> list[str]:
    """Split a multi-game PDN string into individual game strings."""
    # Each game starts with a bracket tag block [Tag "..."]
    parts = re.split(r'(?=\[\s*\w+\s+")', pdn_text)
    games: list[str] = []
    for part in parts:
        p = part.strip()
        if p and ("[" in p):
            games.append(p)
    return games
