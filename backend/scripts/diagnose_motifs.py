"""Diagnostic: run every dilf MotifDetector on a real PDN, ply by ply,
without Scan (mocked scores). Prints how often each detector fires.

If even on a real game with multi-ply combinations the detectors
return 0 hits, the chain is broken upstream of the storage layer.
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from collections import Counter
from game_engine import initial_state, get_legal_moves, apply_move
from pedagogy.engine_adapter import GameEngineAdapter, ge_state_to_dilf, ge_move_to_dilf
from pedagogy.motifs import ALL_DETECTORS  # type: ignore

try:
    from main import _find_move_by_pdn  # type: ignore
except Exception:
    sys.exit("main._find_move_by_pdn unavailable — run from backend/")


def parse_first_game(text: str) -> tuple[list[str], str | None, str | None]:
    """Return (move_tokens, white_player, black_player) from the FIRST PDN
    game in `text`."""
    # split on blank-line-then-tag, take first block
    head = re.split(r"\n\s*\n+(?=\[\s*\w)", text)[0]
    tags = dict(re.findall(r'\[(\w+)\s+"([^"]*)"\]', head))
    move_section = re.search(r"\][^\[]*$", head, re.DOTALL)
    body = move_section.group(0) if move_section else head
    body = re.sub(r"(1-0|0-1|2-0|0-2|1-1|2-1|1-2|1/2-1/2|\*)\s*$", "", body.strip())
    move_tokens = re.findall(r"\b\d+[-x]\d+(?:[-x]\d+)*\b", body)
    return move_tokens, tags.get("White"), tags.get("Black")


def main() -> int:
    pdn_path = BACKEND.parent / "docs" / "parties" / "Bourges2-Seilh.pdn"
    text = pdn_path.read_text(encoding="utf-8")
    move_tokens, white, black = parse_first_game(text)
    print(f"Game: {white} vs {black} — {len(move_tokens)} plies")
    if not move_tokens:
        return 1

    engine = GameEngineAdapter()
    ge_state = initial_state()
    states = [ge_state]
    moves = []
    for i, tok in enumerate(move_tokens):
        legal = get_legal_moves(ge_state)
        mv = _find_move_by_pdn(tok, legal)
        if mv is None:
            print(f"FAIL ply {i+1}: {tok}")
            return 1
        ge_state = apply_move(ge_state, mv)
        states.append(ge_state)
        moves.append(mv)
    print(f"Replay OK : {len(moves)} plies\n")

    # Run every detector on every (state_before, move, state_after) triple.
    hits: Counter[str] = Counter()
    errs: Counter[str] = Counter()
    per_ply_summary: list[tuple[int, str, list[str]]] = []
    for i, ge_move in enumerate(moves):
        state_before = ge_state_to_dilf(states[i])
        state_after = ge_state_to_dilf(states[i + 1])
        dilf_move = ge_move_to_dilf(ge_move, states[i].board)
        fired = []
        for cls in ALL_DETECTORS:
            det = cls()
            try:
                m = det.detect(
                    state_before=state_before,
                    move=dilf_move,
                    state_after=state_after,
                    pv=None,
                    scan_score_before=0.0,
                    scan_score_after=0.0,
                    engine=engine,
                )
                if m is not None:
                    hits[m.motif] += 1
                    fired.append(f"{m.motif}/{m.role}")
            except Exception as exc:
                errs[f"{cls.__name__}: {type(exc).__name__}"] += 1
        if fired:
            per_ply_summary.append((i + 1, move_tokens[i], fired))

    print(f"Total motif hits: {sum(hits.values())}")
    for motif, n in hits.most_common():
        print(f"  {motif}: {n}")
    if errs:
        print("\nDetector errors (silent in real pipeline):")
        for k, v in errs.items():
            print(f"  {k}: {v}")

    print(f"\nPlies with at least one motif: {len(per_ply_summary)}/{len(moves)}")
    for ply, tok, fired in per_ply_summary[:10]:
        print(f"  ply {ply:3d} ({tok}): {fired}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
