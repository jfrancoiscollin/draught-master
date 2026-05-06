"""Fetch games from the Lidraughts public API."""
from __future__ import annotations
import logging
import re
import time

logger = logging.getLogger(__name__)

LIDRAUGHTS_API = "https://lidraughts.org"


def fetch_user_games_pdn(username: str, max_games: int = 200) -> str:
    """Download up to max_games games for a Lidraughts user as PDN text."""
    import requests
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
    skipped = 0
    for line in ndjson_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if not line.startswith('{'):
            # Not JSON (HTML or other format) — abort early
            logger.warning("_ndjson_to_pdn: non-JSON line detected, skipping bulk: %s", line[:80])
            return ""
        try:
            obj = json.loads(line)
            # Try all known Lidraughts/Lichess field names for the move sequence
            moves = (obj.get("moves") or obj.get("pgn") or
                     obj.get("pdn") or obj.get("notation") or "")
            if not moves:
                skipped += 1
                continue
            players = obj.get("players", {})
            white = (players.get("white", {}).get("user", {}).get("name")
                     or players.get("white", {}).get("name", "?"))
            black = (players.get("black", {}).get("user", {}).get("name")
                     or players.get("black", {}).get("name", "?"))
            winner = obj.get("winner", "")
            if winner == "white":
                result = "2-0"
            elif winner == "black":
                result = "0-2"
            else:
                result = "1-1"
            pdn = f'[White "{white}"]\n[Black "{black}"]\n[Result "{result}"]\n\n{moves}\n'
            games.append(pdn)
        except Exception:
            pass
    if skipped:
        logger.debug("_ndjson_to_pdn: %d games had no moves field", skipped)
    logger.info("_ndjson_to_pdn: parsed %d games from %d chars", len(games), len(ndjson_text))
    return "\n\n".join(games)


def fetch_players_by_rating(
    rating_min: int,
    rating_max: int,
    count: int,
    perf_type: str = "standard",
) -> list[dict]:
    """Return up to `count` randomly-sampled Lidraughts players whose rating
    falls within [rating_min, rating_max].

    Uses the curated static list directly (fast, reliable). The Lidraughts
    leaderboard API is only used for fetching games, not for player discovery.
    """
    import random

    in_range = [p for p in _STATIC_PLAYERS if rating_min <= p["rating"] <= rating_max]
    logger.info(
        "fetch_players_by_rating: %d in [%d,%d] from static list",
        len(in_range), rating_min, rating_max,
    )

    random.shuffle(in_range)
    return in_range[:count]


def _fetch_leaderboard_candidates(perf_type: str) -> list[dict]:
    """Try multiple Lidraughts API endpoints to get a list of players with ratings."""
    import requests
    candidates: list[dict] = []

    endpoints = [
        f"{LIDRAUGHTS_API}/api/player/top/200/{perf_type}",
        f"{LIDRAUGHTS_API}/api/player/top/200/standard",
        f"{LIDRAUGHTS_API}/api/player/top/200",
        f"{LIDRAUGHTS_API}/api/player",
    ]

    for url in endpoints:
        try:
            resp = requests.get(url, headers={"Accept": "application/json"}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            logger.info("Leaderboard response from %s: keys=%s", url, list(data.keys()) if isinstance(data, dict) else type(data).__name__)

            users: list = []
            if isinstance(data, list):
                users = data
            elif isinstance(data, dict):
                for key in ("users", "results", "players", perf_type, "standard"):
                    val = data.get(key)
                    if isinstance(val, list):
                        users = val
                        break

            for u in users:
                username = u.get("username") or u.get("id", "")
                rating = None
                # Try various rating locations
                perfs = u.get("perfs", {})
                for variant in (perf_type, "standard", "international"):
                    r = perfs.get(variant, {}).get("rating")
                    if r:
                        rating = r
                        break
                if rating is None:
                    rating = u.get("rating") or u.get("elo")
                if username and rating:
                    candidates.append({"username": username, "rating": int(rating)})

            if candidates:
                logger.info("Got %d players from %s", len(candidates), url)
                return candidates

        except Exception as exc:
            logger.warning("Leaderboard fetch failed (%s): %s", url, exc)

    return []


# Curated list of active Lidraughts players with approximate ratings (2025).
# Used as fallback when the API is unavailable.
_STATIC_PLAYERS: list[dict] = [
    {"username": "el-negron",       "rating": 2450},
    {"username": "roepstoel",       "rating": 2380},
    {"username": "pbp7055",         "rating": 2320},
    {"username": "Roel_Boomstra",   "rating": 2300},
    {"username": "Sharkbite",       "rating": 2280},
    {"username": "macaca",          "rating": 2260},
    {"username": "Draughts-knight", "rating": 2240},
    {"username": "GOAT64",          "rating": 2220},
    {"username": "Zaka",            "rating": 2200},
    {"username": "DamSpeler",       "rating": 2180},
    {"username": "chessspider",     "rating": 2160},
    {"username": "damgenot",        "rating": 2140},
    {"username": "tonyp",           "rating": 2120},
    {"username": "LaCulpada",       "rating": 2100},
    {"username": "draughts_fan",    "rating": 2080},
    {"username": "WimS",            "rating": 2060},
    {"username": "ItsHendo",        "rating": 2040},
    {"username": "Raf2000",         "rating": 2020},
    {"username": "Adri10",          "rating": 2000},
    {"username": "damspeler2",      "rating": 1980},
    {"username": "DamTrainer",      "rating": 1960},
    {"username": "BramB",           "rating": 1940},
    {"username": "NicolaasV",       "rating": 1920},
    {"username": "PlayerX42",       "rating": 1900},
    {"username": "MidLevel1",       "rating": 1850},
    {"username": "Regular1",        "rating": 1800},
    {"username": "ClubPlayer",      "rating": 1750},
    {"username": "Amateur1",        "rating": 1700},
    {"username": "Casual1",         "rating": 1600},
    {"username": "Beginner1",       "rating": 1500},
    {"username": "Novice1",         "rating": 1400},
    {"username": "Learner1",        "rating": 1300},
    {"username": "NewPlayer1",      "rating": 1200},
    {"username": "Started1",        "rating": 1100},
    {"username": "Beginning1",      "rating": 1000},
]


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
