"""Smoke test du flow d'import Lidraughts (offline).

L'API Lidraughts elle-même n'est pas joignable depuis l'environnement
sandbox (allowlist réseau), donc on simule la réponse de
`fetch_user_games_pdn` avec :
- les vrais PDN d'archives dans `docs/parties/` (sans tags Lidraughts),
- un PDN synthétique avec tags `[Site "lidraughts.org/<id>"]` pour
  exercer le path `source_id` et la déduplication.

Le test vérifie :

1. `split_pdn_games(pdn_text)` découpe correctement un flux multi-partie.
2. Le parsing des tags reproduit le mapping main.py
   ([Site] → source_id, [White]/[Black] → players, [Result] → result,
   user_side dérivé du login).
3. `save_imported_game` insère N parties, puis 0 lors du replay
   (idempotent sur (user_id, source, source_id)).
4. Chaque partie est rejouable via `game_engine.make_move` depuis la
   position initiale, sans erreur de notation ni de légalité.

Lancer :

    cd backend && python -m scripts.smoke_test_lidraughts_import
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Use a temp DB so we don't touch the real one.
_TMPDIR = Path(tempfile.mkdtemp(prefix="dm-lidraughts-smoke-"))
os.environ["DB_DIR"] = str(_TMPDIR)

from lidraughts_fetcher import split_pdn_games  # noqa: E402

# Late imports so DB_DIR is honoured.
from db.schema import init_db  # noqa: E402
from db.games import save_imported_game  # noqa: E402
from db.users import create_user  # noqa: E402
from db.config import DB_PATH  # noqa: E402
import aiosqlite  # noqa: E402

from game_engine import (  # noqa: E402
    initial_state,
    get_legal_moves,
    apply_move,
)


SAMPLE_PDN_DIR = (BACKEND.parent / "docs" / "parties").resolve()


SYNTHETIC_LIDRAUGHTS_PDN = """\
[Event "Online"]
[Site "https://lidraughts.org/ABC123XY"]
[Date "2026.05.15"]
[Round "?"]
[White "TestUser"]
[Black "Opponent"]
[Result "1-0"]
[GameType "20"]
[PlyCount "5"]

1. 32-28 18-23 2. 33-29 23x32 3. 38x27 1-0

[Event "Online"]
[Site "https://lidraughts.org/DEF456ZQ"]
[Date "2026.05.15"]
[Round "?"]
[White "Opponent2"]
[Black "TestUser"]
[Result "0-1"]
[GameType "20"]
[PlyCount "4"]

1. 31-27 19-23 2. 36-31 14-19 0-1
"""


def _parse_pdn(pdn_text: str, user_login: str) -> list[dict]:
    """Parse PDN block list the way main.py does, return dicts ready
    for save_imported_game.
    """
    games = []
    for pdn in split_pdn_games(pdn_text):
        tags: dict[str, str] = {}
        for m in re.finditer(r'\[(\w+)\s+"([^"]*)"\]', pdn):
            tags[m.group(1).lower()] = m.group(2)
        site = tags.get("site", "")
        m_site = re.search(r"lidraughts\.org/(\w+)", site)
        source_id = m_site.group(1) if m_site else (tags.get("gameid") or None)
        white_player = tags.get("white", "?")
        black_player = tags.get("black", "?")
        date_tag = tags.get("utcdate") or tags.get("date") or datetime.utcnow().date().isoformat()
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
        # Only scan the moves section (after the last tag line), then
        # strip the trailing result indicator BEFORE running the move
        # regex — otherwise `1/2-1/2` slips a phantom `2-1` token into
        # the move list, and `1-0` etc. would be matched as moves.
        move_section_match = re.search(r"\][^\[]*$", pdn, re.DOTALL)
        move_section = move_section_match.group(0) if move_section_match else pdn
        move_section = re.sub(
            r"(1-0|0-1|2-0|0-2|1-1|2-1|1-2|1/2-1/2|\*)\s*$",
            "",
            move_section.strip(),
        )
        move_tokens = re.findall(r"\b\d+[-x]\d+(?:[-x]\d+)*\b", move_section)
        games.append({
            "game_id": source_id or uuid.uuid4().hex,
            "date": date_tag,
            "white_player": white_player,
            "black_player": black_player,
            "result": result,
            "pdn": pdn,
            "move_count": len(move_tokens),
            "source": "lidraughts",
            "source_id": source_id,
            "user_side": user_side,
            "move_tokens": move_tokens,
        })
    return games


def _replay_moves(move_tokens: list[str]) -> tuple[int, str]:
    """Try to apply each move token from the initial position.

    Returns (n_applied, error_message). n_applied == len(move_tokens) on
    full success.
    """
    state = initial_state()
    for i, tok in enumerate(move_tokens):
        if "x" in tok:
            parts = [int(s) for s in tok.split("x")]
        else:
            parts = [int(s) for s in tok.split("-")]
        if len(parts) < 2:
            return i, f"token {tok!r} mal formé"
        target_from, target_to = parts[0], parts[-1]
        legal = get_legal_moves(state)
        match = next(
            (m for m in legal if m.path[0] == target_from and m.path[-1] == target_to),
            None,
        )
        if match is None:
            return i, (
                f"coup {tok} ({target_from}->{target_to}) illégal au ply {i+1} "
                f"({state.turn}). Légaux: "
                + ", ".join(f"{m.path[0]}-{m.path[-1]}" for m in legal[:5])
            )
        try:
            state = apply_move(state, match)
        except Exception as exc:
            return i, f"apply_move a levé {type(exc).__name__}: {exc}"
    return len(move_tokens), ""


async def main() -> int:
    await init_db()
    user_id = await create_user("smoke@test.local", "x")
    user_login = "testuser"  # matches White in synth game 1, Black in synth game 2

    print(f"DB temp: {DB_PATH}\nUser id: {user_id}\n")

    # [1] split_pdn_games — synthetic + real samples
    print("[1] split_pdn_games")
    synth_games = split_pdn_games(SYNTHETIC_LIDRAUGHTS_PDN)
    print(f"    synthetic Lidraughts: {len(synth_games)} games (expected 2)")
    real_pdn = ""
    for f in sorted(SAMPLE_PDN_DIR.glob("*.pdn")):
        real_pdn += f.read_text(encoding="utf-8") + "\n"
    real_games = split_pdn_games(real_pdn)
    print(f"    docs/parties/*.pdn  : {len(real_games)} games")
    if len(synth_games) != 2:
        print("    ✗ split synthetic broken"); return 1

    # [2] parse tags
    print("\n[2] parse tags")
    parsed = _parse_pdn(SYNTHETIC_LIDRAUGHTS_PDN, user_login)
    for p in parsed:
        print(f"    {p['source_id']}: white={p['white_player']}, "
              f"black={p['black_player']}, result={p['result']}, "
              f"user_side={p['user_side']}, moves={p['move_count']}")
    if parsed[0]["source_id"] != "ABC123XY" or parsed[0]["user_side"] != "white":
        print("    ✗ tag parsing broken"); return 1
    if parsed[1]["source_id"] != "DEF456ZQ" or parsed[1]["user_side"] != "black":
        print("    ✗ tag parsing broken on game 2"); return 1

    # [3] save + dedup
    print("\n[3] save_imported_game + dedup")
    first_pass = 0
    for p in parsed:
        ok = await save_imported_game(
            game_id=p["game_id"], user_id=user_id, date=p["date"],
            white_player=p["white_player"], black_player=p["black_player"],
            result=p["result"], pdn=p["pdn"], move_count=p["move_count"],
            source=p["source"], source_id=p["source_id"], user_side=p["user_side"],
        )
        first_pass += int(ok)
    print(f"    first pass : {first_pass} inserted")
    second_pass_inserted = 0
    for p in parsed:
        ok = await save_imported_game(
            game_id=p["game_id"], user_id=user_id, date=p["date"],
            white_player=p["white_player"], black_player=p["black_player"],
            result=p["result"], pdn=p["pdn"], move_count=p["move_count"],
            source=p["source"], source_id=p["source_id"], user_side=p["user_side"],
        )
        second_pass_inserted += int(ok)
    print(f"    second pass: {second_pass_inserted} inserted (expected 0 — dedup)")
    if first_pass != 2 or second_pass_inserted != 0:
        print("    ✗ dedup broken"); return 1

    # [4] replay moves from each parsed game
    print("\n[4] replay moves via game_engine")
    all_games = parsed + _parse_pdn(real_pdn, "nobody")
    failures: list[tuple[str, str]] = []
    for p in all_games:
        n, err = _replay_moves(p["move_tokens"])
        label = p["source_id"] or p["white_player"] + " vs " + p["black_player"]
        status = "OK" if not err else f"FAIL ply={n+1}"
        print(f"    {status:18s} {label[:50]:50s} ({n}/{len(p['move_tokens'])} plies)")
        if err:
            failures.append((label, err))
    if failures:
        print("\n    Détails :")
        for label, err in failures:
            print(f"    ✗ {label}: {err}")
        return 1

    print("\nSMOKE TEST OK — import Lidraughts en boucle fermée intégralement vert.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
