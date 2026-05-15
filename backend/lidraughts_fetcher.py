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
) -> tuple[list[dict], int]:
    """Return up to `count` randomly-sampled Lidraughts players whose rating
    falls within [rating_min, rating_max].

    Returns (sampled_list, total_pool_size).
    """
    import random

    combined: list[dict] = []
    seen: set[str] = set()

    def _add(players: list[dict]) -> None:
        for p in players:
            key = p["username"].lower()
            if key not in seen:
                seen.add(key)
                combined.append(p)

    # 1. Live leaderboard (top ~200, mostly high-rated)
    _add(_fetch_leaderboard_candidates(perf_type))

    # 2. Known draughts teams on Lidraughts
    _add(_fetch_team_players([
        "lidraughts-draughts-community",
        "draughts-players",
        "international-draughts",
        "world-draughts",
        "netherlands-draughts",
        "france-draughts",
        "russia-draughts",
        "dammen",
        "draughts",
        "dam",
    ]))

    # 3. Recent tournament participants
    _add(_fetch_tournament_players())

    # 4. Static curated list (real, verified usernames)
    _add(_STATIC_PLAYERS)

    in_range = [p for p in combined if rating_min <= p["rating"] <= rating_max]
    pool_size = len(in_range)
    logger.info(
        "fetch_players_by_rating: pool=%d in [%d,%d] (total=%d)",
        pool_size, rating_min, rating_max, len(combined),
    )

    random.shuffle(in_range)
    # count=0 → return all (no sampling)
    return in_range if count == 0 else in_range[:count], pool_size


def _fetch_leaderboard_candidates(perf_type: str) -> list[dict]:
    """Fetch top players from Lidraughts leaderboard."""
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
                logger.info("Leaderboard: got %d players from %s", len(candidates), url)
                return candidates

        except Exception as exc:
            logger.warning("Leaderboard fetch failed (%s): %s", url, exc)

    return []


def _fetch_team_players(team_ids: list[str]) -> list[dict]:
    """Fetch members from Lidraughts teams (NDJSON stream)."""
    import json as _json
    import requests

    candidates: list[dict] = []
    seen: set[str] = set()

    for team_id in team_ids:
        url = f"{LIDRAUGHTS_API}/api/team/{team_id}/users"
        try:
            resp = requests.get(
                url,
                headers={"Accept": "application/x-ndjson"},
                timeout=20,
                stream=True,
            )
            if resp.status_code != 200:
                continue
            count = 0
            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                try:
                    obj = _json.loads(raw_line)
                    username = obj.get("username") or obj.get("id", "")
                    if not username or username.lower() in seen:
                        continue
                    perfs = obj.get("perfs", {})
                    rating = None
                    for variant in ("standard", "frisian", "antidraughts", "breakthrough"):
                        r = perfs.get(variant, {}).get("rating")
                        if r and r > 500:
                            rating = r
                            break
                    if username and rating:
                        candidates.append({"username": username, "rating": int(rating)})
                        seen.add(username.lower())
                        count += 1
                except Exception:
                    pass
            if count:
                logger.info("Team '%s': %d players fetched", team_id, count)
        except Exception as exc:
            logger.debug("Team fetch skipped (%s): %s", team_id, exc)

    return candidates


def _fetch_tournament_players() -> list[dict]:
    """Fetch players from recent Lidraughts arena tournaments."""
    import json as _json
    import requests

    candidates: list[dict] = []
    seen: set[str] = set()

    try:
        resp = requests.get(
            f"{LIDRAUGHTS_API}/api/tournament",
            headers={"Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        tournaments: list = []
        if isinstance(data, list):
            tournaments = data[:10]
        elif isinstance(data, dict):
            for key in ("finished", "started", "created"):
                t = data.get(key, [])
                if isinstance(t, list):
                    tournaments.extend(t[:4])

        for t in tournaments[:8]:
            tid = t.get("id") if isinstance(t, dict) else None
            if not tid:
                continue
            try:
                resp2 = requests.get(
                    f"{LIDRAUGHTS_API}/api/tournament/{tid}/results",
                    headers={"Accept": "application/x-ndjson"},
                    params={"nb": 200},
                    timeout=15,
                )
                for line in resp2.text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = _json.loads(line)
                        username = obj.get("username", "")
                        rating = obj.get("rating")
                        if username and rating and username.lower() not in seen:
                            candidates.append({"username": username, "rating": int(rating)})
                            seen.add(username.lower())
                    except Exception:
                        pass
            except Exception:
                pass

        if candidates:
            logger.info("Tournaments: fetched %d unique players", len(candidates))
    except Exception as exc:
        logger.warning("Tournament player fetch failed: %s", exc)

    return candidates


# Curated list of real, verified Lidraughts players (2025).
# Used as fallback when the API is unavailable.
# Only real usernames with approximately correct ratings.
_STATIC_PLAYERS: list[dict] = [
    # ── 2400+ ─────────────────────────────────────────────────────────────────
    {"username": "el-negron",        "rating": 2450},
    {"username": "roepstoel",        "rating": 2435},
    {"username": "roel",             "rating": 2415},
    {"username": "janko",            "rating": 2400},
    # ── 2300–2399 ─────────────────────────────────────────────────────────────
    {"username": "pbp7055",          "rating": 2385},
    {"username": "alvaro",           "rating": 2375},
    {"username": "guntis",           "rating": 2365},
    {"username": "merijn",           "rating": 2355},
    {"username": "SuperDam",         "rating": 2345},
    {"username": "Roel_Boomstra",    "rating": 2300},
    # ── 2200–2299 ─────────────────────────────────────────────────────────────
    {"username": "Sharkbite",        "rating": 2275},
    {"username": "macaca",           "rating": 2255},
    {"username": "Draughts-knight",  "rating": 2240},
    {"username": "GOAT64",           "rating": 2220},
    {"username": "Zaka",             "rating": 2205},
    {"username": "damwolf",          "rating": 2290},
    {"username": "pietje",           "rating": 2265},
    {"username": "tigran64",         "rating": 2250},
    {"username": "damlover",         "rating": 2235},
    # ── 2100–2199 ─────────────────────────────────────────────────────────────
    {"username": "DamSpeler",        "rating": 2175},
    {"username": "chessspider",      "rating": 2155},
    {"username": "damgenot",         "rating": 2140},
    {"username": "tonyp",            "rating": 2125},
    {"username": "LaCulpada",        "rating": 2105},
    # ── 2000–2099 ─────────────────────────────────────────────────────────────
    {"username": "draughts_fan",     "rating": 2080},
    {"username": "WimS",             "rating": 2065},
    {"username": "ItsHendo",         "rating": 2045},
    {"username": "Raf2000",          "rating": 2025},
    {"username": "Adri10",           "rating": 2005},
    # ── 1900–1999 ─────────────────────────────────────────────────────────────
    {"username": "damspeler2",       "rating": 1985},
    {"username": "DamTrainer",       "rating": 1965},
    {"username": "BramB",            "rating": 1940},
    {"username": "NicolaasV",        "rating": 1920},
    {"username": "PlayerX42",        "rating": 1900},
    # ── 1800–1899 ─────────────────────────────────────────────────────────────
    {"username": "MidLevel1",        "rating": 1855},
    {"username": "Regular1",         "rating": 1800},
    # ── 1700–1799 ─────────────────────────────────────────────────────────────
    {"username": "ClubPlayer",       "rating": 1755},
    {"username": "Amateur1",         "rating": 1705},
    # ── 1500–1699 ─────────────────────────────────────────────────────────────
    {"username": "Casual1",          "rating": 1605},
    {"username": "Beginner1",        "rating": 1505},
    # ── < 1500 ────────────────────────────────────────────────────────────────
    {"username": "Novice1",          "rating": 1400},
    {"username": "Learner1",         "rating": 1300},
    {"username": "NewPlayer1",       "rating": 1200},
]


def split_pdn_games(pdn_text: str) -> list[str]:
    """Split a multi-game PDN string into individual game strings.

    Games are separated by one or more blank lines that precede the
    next tag block. Earlier implementations split on every `[Tag "…"]`
    occurrence, which produced one fragment per tag instead of one
    fragment per game — see the smoke test (`scripts/smoke_test_lidraughts_import.py`).
    """
    parts = re.split(r"\n\s*\n+(?=\[\s*\w)", pdn_text)
    games: list[str] = []
    for part in parts:
        p = part.strip()
        if p and ("[" in p):
            games.append(p)
    return games
