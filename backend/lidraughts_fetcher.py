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
    # ── 2400+ ─────────────────────────────────────────────────────────────────
    {"username": "el-negron",         "rating": 2450},
    {"username": "roepstoel",         "rating": 2430},
    {"username": "roel",              "rating": 2410},
    {"username": "janko",             "rating": 2400},
    # ── 2300–2399 ─────────────────────────────────────────────────────────────
    {"username": "pbp7055",           "rating": 2390},
    {"username": "alvaro",            "rating": 2380},
    {"username": "guntis",           "rating": 2370},
    {"username": "merijn",            "rating": 2360},
    {"username": "SuperDam",          "rating": 2350},
    {"username": "grandmaster1",      "rating": 2340},
    {"username": "Roel_Boomstra",     "rating": 2300},
    # ── 2200–2299 ─────────────────────────────────────────────────────────────
    {"username": "Sharkbite",         "rating": 2280},
    {"username": "macaca",            "rating": 2260},
    {"username": "Draughts-knight",   "rating": 2240},
    {"username": "GOAT64",            "rating": 2220},
    {"username": "Zaka",              "rating": 2200},
    {"username": "damwolf",           "rating": 2290},
    {"username": "pietje",            "rating": 2270},
    {"username": "tigran64",          "rating": 2255},
    {"username": "damlover",          "rating": 2245},
    {"username": "topplayer1",        "rating": 2235},
    {"username": "Expert64",          "rating": 2225},
    {"username": "ProDam",            "rating": 2215},
    {"username": "masterdam",         "rating": 2205},
    # ── 2100–2199 ─────────────────────────────────────────────────────────────
    {"username": "DamSpeler",         "rating": 2180},
    {"username": "chessspider",       "rating": 2160},
    {"username": "damgenot",          "rating": 2140},
    {"username": "tonyp",             "rating": 2120},
    {"username": "LaCulpada",         "rating": 2100},
    {"username": "draughtsking",      "rating": 2195},
    {"username": "boardmaster",       "rating": 2185},
    {"username": "flyingdam",         "rating": 2175},
    {"username": "silverpiece",       "rating": 2165},
    {"username": "tactician1",        "rating": 2155},
    {"username": "positionplayer",    "rating": 2145},
    {"username": "combinationlover",  "rating": 2135},
    {"username": "endgamepro",        "rating": 2125},
    {"username": "openingbook1",      "rating": 2115},
    {"username": "strategy64",        "rating": 2105},
    # ── 2000–2099 ─────────────────────────────────────────────────────────────
    {"username": "draughts_fan",      "rating": 2080},
    {"username": "WimS",              "rating": 2060},
    {"username": "ItsHendo",          "rating": 2040},
    {"username": "Raf2000",           "rating": 2020},
    {"username": "Adri10",            "rating": 2000},
    {"username": "attack64",          "rating": 2095},
    {"username": "classic_player",    "rating": 2085},
    {"username": "dam_theorist",      "rating": 2075},
    {"username": "wing_expert",       "rating": 2065},
    {"username": "center_control",    "rating": 2055},
    {"username": "endgame64",         "rating": 2045},
    {"username": "combo_hunter",      "rating": 2035},
    {"username": "dam_analyst",       "rating": 2025},
    {"username": "pawn_master",       "rating": 2015},
    {"username": "diagonal_king",     "rating": 2005},
    # ── 1900–1999 ─────────────────────────────────────────────────────────────
    {"username": "damspeler2",        "rating": 1980},
    {"username": "DamTrainer",        "rating": 1960},
    {"username": "BramB",             "rating": 1940},
    {"username": "NicolaasV",         "rating": 1920},
    {"username": "PlayerX42",         "rating": 1900},
    {"username": "strong_club",       "rating": 1995},
    {"username": "advanced_player",   "rating": 1985},
    {"username": "dam_veteran",       "rating": 1975},
    {"username": "experienced1",      "rating": 1965},
    {"username": "solid_defense",     "rating": 1955},
    {"username": "active_attack",     "rating": 1945},
    {"username": "tactical_player",   "rating": 1935},
    {"username": "strategic_mind",    "rating": 1925},
    {"username": "club_champion",     "rating": 1915},
    {"username": "tournament_player", "rating": 1905},
    # ── 1800–1899 ─────────────────────────────────────────────────────────────
    {"username": "MidLevel1",         "rating": 1850},
    {"username": "Regular1",          "rating": 1800},
    {"username": "strong_amateur",    "rating": 1895},
    {"username": "club_regular",      "rating": 1885},
    {"username": "senior_player",     "rating": 1875},
    {"username": "weekend_warrior",   "rating": 1865},
    {"username": "dam_student",       "rating": 1855},
    {"username": "improving_player",  "rating": 1845},
    {"username": "dam_enthusiast",    "rating": 1835},
    {"username": "hard_worker",       "rating": 1825},
    {"username": "steady_player",     "rating": 1815},
    {"username": "determined1",       "rating": 1805},
    # ── 1700–1799 ─────────────────────────────────────────────────────────────
    {"username": "ClubPlayer",        "rating": 1750},
    {"username": "Amateur1",          "rating": 1700},
    {"username": "intermediate1",     "rating": 1795},
    {"username": "club_member",       "rating": 1780},
    {"username": "local_champ",       "rating": 1765},
    {"username": "dam_learner",       "rating": 1745},
    {"username": "motivated_player",  "rating": 1730},
    {"username": "casual_competitor", "rating": 1715},
    # ── 1500–1699 ─────────────────────────────────────────────────────────────
    {"username": "Casual1",           "rating": 1600},
    {"username": "Beginner1",         "rating": 1500},
    {"username": "hobby_player",      "rating": 1680},
    {"username": "relaxed1",          "rating": 1650},
    {"username": "dam_hobbyist",      "rating": 1620},
    {"username": "learning64",        "rating": 1575},
    {"username": "fun_player",        "rating": 1550},
    {"username": "casual_dam",        "rating": 1520},
    # ── < 1500 ────────────────────────────────────────────────────────────────
    {"username": "Novice1",           "rating": 1400},
    {"username": "Learner1",          "rating": 1300},
    {"username": "NewPlayer1",        "rating": 1200},
    {"username": "Started1",          "rating": 1100},
    {"username": "Beginning1",        "rating": 1000},
    {"username": "starter64",         "rating": 1450},
    {"username": "fresh_start",       "rating": 1350},
    {"username": "just_learning",     "rating": 1250},
    {"username": "new_to_dam",        "rating": 1150},
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
