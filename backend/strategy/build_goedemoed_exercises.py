"""Mine verified forced-win exercises from the Goedemoed volume's solutions.

The Goedemoed 'A Course in Draughts' exercise volume prints its diagrams
(handled by ``build_goedemoed_source.py`` -> ``position_library``) and,
elsewhere in the same volume, the *solutions* as move sequences. This
script reads those solution sequences from the PDF text layer and pairs
each one with the diagram it solves **purely by legality**:

    A solution is replayed, ply by ply, on every detected diagram FEN.
    The board on which the *entire* line is legal is the diagram it solves.
    A forced line of ~8-15 plies is legal on exactly one board, so the
    match is unique and simultaneously *proves* the auto-detected FEN and
    the side to move are correct (a wrong FEN cannot admit the full line).

This sidesteps the volume's scrambled, per-chapter solution numbering and
the two-column solution-page layout entirely.

Two modes (run from backend/):

    # 1. Extract + match from the PDF, then merge (needs the source PDF):
    python -m strategy.build_goedemoed_exercises \
        --pdf /home/user/dilf/docs/corpus/Exercise_2.pdf

    # 2. Merge only, from the committed intermediate (no PDF needed):
    python -m strategy.build_goedemoed_exercises

Outputs:
    pages/goedemoed/solutions_verified.json   intermediate (committed)
    strategy_exercises.json                   GOEDEMOED rows merged in
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
sys.path.insert(0, str(_BACKEND))

_OUT = _HERE / "pages" / "goedemoed"
_VERIFIED = _OUT / "solutions_verified.json"
_EXERCISES = _HERE / "strategy_exercises.json"
_LIBRARY = _HERE / "position_library.json"

_MIN_PREFIX = 6          # shortest prefix accepted for a unique-prefix match
_VALID = re.compile(r"^\d{1,2}([-x]\d{1,2})+$")


# ----------------------------------------------------------------------------
# 1. Solution-text extraction (PDF text layer, two columns, format-agnostic)
# ----------------------------------------------------------------------------
def _page_stream(pdf: Path, pg: int) -> list[str]:
    """Column-ordered token lines for one page.

    ``pdftotext -layout`` lays the two solution columns side by side on each
    line; we find the dominant column gap and read the left column fully,
    then the right, restoring natural reading order.
    """
    out = subprocess.run(
        ["pdftotext", "-layout", "-f", str(pg), "-l", str(pg), str(pdf), "-"],
        capture_output=True, text=True,
    ).stdout
    lines = [ln.rstrip() for ln in out.split("\n")]
    gaps: Counter[int] = Counter()
    for ln in lines:
        for m in re.finditer(r" {3,}", ln):
            if 30 <= m.start() <= 70:
                gaps[m.start()] += 1
                break
    split = gaps.most_common(1)[0][0] if gaps else 200
    return [ln[:split] for ln in lines] + [ln[split:] for ln in lines if len(ln) > split]


def _segment(text: str) -> list[list[str]]:
    """Split a page's solution text into move sequences.

    Sequences are delimited by the books's *internal* move numbering: a new
    solution begins at each ``1.`` and ends at the next ``1.`` or a W+/B+
    terminator. Parenthesised variations are stripped first.
    """
    text = re.sub(r"\([^()]*\)", " ", text)
    text = re.sub(r"\([^()]*\)", " ", text)   # one level of nesting
    seqs: list[list[str]] = []
    cur: list[str] = []
    for raw in text.split():
        raw = raw.strip()
        m = re.match(r"^(\d+)\.(.*)$", raw)
        if m:
            no, mv = int(m.group(1)), m.group(2).rstrip("!?").strip()
            if no == 1 and cur:
                seqs.append(cur)
                cur = []
            if _VALID.match(mv):
                cur.append(mv)
        else:
            tok = raw.rstrip("!?+").strip()
            if tok in ("W", "B") or raw.startswith(("W+", "B+")):
                if cur:
                    seqs.append(cur)
                    cur = []
            elif _VALID.match(tok):
                if "-" in tok and "x" not in tok and len(tok.split("-")) > 2:
                    if cur:                      # quiet multi-step = not a move
                        seqs.append(cur)
                        cur = []
                else:
                    cur.append(tok)
    if cur:
        seqs.append(cur)
    return [s for s in seqs if len(s) >= 2]


def _all_sequences(pdf: Path) -> list[list[str]]:
    seen: dict[tuple, bool] = {}
    for pg in range(2, 205):
        for s in _segment("\n".join(_page_stream(pdf, pg))):
            seen[tuple(s)] = True
    return [list(s) for s in seen]


# ----------------------------------------------------------------------------
# 2. Legality matching against the detected diagram FENs
# ----------------------------------------------------------------------------
def _load_fens() -> list[dict]:
    lib = json.loads(_LIBRARY.read_text())
    items = lib if isinstance(lib, list) else lib.get("positions", lib)
    return [p for p in items if p.get("source") == "GOEDEMOED" and p.get("valid")]


def _tok_sig(tok: str) -> tuple[int, int, bool]:
    nums = [int(x) for x in re.split("[-x]", tok)]
    return nums[0], nums[-1], "x" in tok


def _canonical(move) -> str:
    """Engine Move -> PDN string (full capture path, like existing rows)."""
    sep = "x" if move.captures else "-"
    return sep.join(str(p) for p in move.path)


_PIECE_VALUE = {1: 100, 3: 100, 2: 300, 4: 300}  # man=100, king=300 (WHITE/BLACK man/king ids)


def match_sequences(sequences: list[list[str]]) -> dict[str, dict]:
    from game_engine import (
        fen_to_board, get_legal_moves, apply_move, game_result,
        WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING,
    )

    val = {WHITE_MAN: 100, WHITE_KING: 300, BLACK_MAN: 100, BLACK_KING: 300}
    white_pieces = {WHITE_MAN, WHITE_KING}

    def net_material(state, mover: str) -> int:
        s = 0
        for sq in range(1, 51):
            pc = state.board[sq]
            if pc not in val:
                continue
            signed = val[pc] if pc in white_pieces else -val[pc]
            s += signed if mover == "white" else -signed
        return s

    fens = _load_fens()
    # First-ply index: (frm, to, capture, turn) -> [(fen, id, turn)]
    index: dict[tuple, list] = defaultdict(list)
    for p in fens:
        for turn in ("white", "black"):
            st = fen_to_board(p["fen"])
            st.turn = turn
            for m in get_legal_moves(st):
                key = (m.path[0], m.path[-1], bool(m.captures), turn)
                index[key].append((p["fen"], p["id"], turn))

    def tok_match(state, tok):
        a, b, cap = _tok_sig(tok)
        for m in get_legal_moves(state):
            if m.path[0] == a and m.path[-1] == b and bool(m.captures) == cap:
                return m
        return None

    def replay(fen, turn, toks):
        """Replay the line; return (n_legal_plies, canonical_moves, outcome).

        ``outcome`` is computed on the legal prefix actually played:
          - "win"      the line ends in a terminal win for the mover, or
          - "material" the mover nets >= 2 men (200) by the end, else
          - ""         the line replays legally but is not decisive.
        """
        st = fen_to_board(fen)
        st.turn = turn
        mover = st.turn
        start = net_material(st, mover)
        canon: list[str] = []
        for tok in toks:
            m = tok_match(st, tok)
            if m is None:
                break
            canon.append(_canonical(m))
            st = apply_move(st, m)
        if (game_result(st) or "") == mover:
            outcome = "win"
        elif net_material(st, mover) - start >= 200:
            outcome = "material"
        else:
            outcome = ""
        return len(canon), canon, outcome

    matched: dict[str, dict] = {}
    for toks in sequences:
        a, b, cap = _tok_sig(toks[0])
        cands = index.get((a, b, cap, "white"), []) + index.get((a, b, cap, "black"), [])
        results, seen = [], set()
        for fen, did, turn in cands:
            if (did, turn) in seen:
                continue
            seen.add((did, turn))
            n, canon, outcome = replay(fen, turn, toks)
            if n > 0:
                results.append((n, did, turn, canon, outcome))
        if not results:
            continue
        full = [(d, t, c, o) for n, d, t, c, o in results if n == len(toks)]
        if full:
            dids = {d for d, _, _, _ in full}
            if len(dids) != 1:
                continue
            did = next(iter(dids))
            _, turn, canon, outcome = next(r for r in full if r[0] == did)
            kind, plies = "full", len(canon)
        else:
            maxn = max(n for n, _, _, _, _ in results)
            if maxn < _MIN_PREFIX:
                continue
            best = [(d, t, c, o) for n, d, t, c, o in results if n == maxn]
            dids = {d for d, _, _, _ in best}
            if len(dids) != 1:
                continue
            did = next(iter(dids))
            _, turn, canon, outcome = next(r for r in best if r[0] == did)
            kind, plies = "prefix", maxn
        # Legality pins the FEN + side to move uniquely, but a line is only an
        # *exercise* if it is actually decisive. Keep the proven-winning ones.
        if not outcome:
            continue
        if did not in matched or matched[did]["plies"] < plies:
            matched[did] = {
                "moves": canon, "side": turn, "plies": plies,
                "kind": kind, "outcome": outcome,
            }
    return matched


# ----------------------------------------------------------------------------
# 3. Emit exercise rows and merge into strategy_exercises.json
# ----------------------------------------------------------------------------
def _difficulty(plies: int) -> int:
    # App difficulty scale is 1-3.
    return 1 if plies <= 4 else 2 if plies <= 8 else 3


def _rows_from_matched(matched: dict[str, dict]) -> list[dict]:
    fens = {p["id"]: p for p in _load_fens()}
    rows = []
    for did, info in sorted(matched.items()):
        p = fens.get(did)
        if not p:
            continue
        side = info["side"]
        side_fr = "blancs" if side == "white" else "noirs"
        kind = info["kind"]
        tail = "" if kind == "full" else " (début de la solution)"
        rows.append({
            "name": f"GOEDEMOED — combinaison (p.{p['page']} #{p['number']})",
            "description": (
                f"GOEDEMOED — diagramme {p['number']} page {p['page']}. "
                f"Les {side_fr} jouent et gagnent.{tail}"
            ),
            "initial_fen": p["fen"] if p["fen"].startswith(side[0].upper())
                           else f"{side[0].upper()}:{p['fen'].split(':', 1)[1]}",
            "solution_moves": info["moves"],
            "difficulty": _difficulty(info["plies"]),
            "category": "combinaisons_manuels",
            "hint": "Cherchez la combinaison forcée.",
            "source": "GOEDEMOED",
            "page": p["page"],
            "number": p["number"],
            "diagram_id": did,
            "fen_kind": "auto_verified",   # auto FEN, proven by a decisive legal line
            "outcome": info["outcome"],    # "win" (terminal) or "material" (>= 2 men)
            "solution_kind": kind,
        })
    return rows


def merge(rows: list[dict]) -> None:
    data = json.loads(_EXERCISES.read_text())
    kept = [e for e in data.get("exercises", []) if e.get("source") != "GOEDEMOED"]
    merged = kept + rows
    data["exercises"] = merged
    data["n_exercises"] = len(merged)
    _EXERCISES.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"merged {len(rows)} GOEDEMOED rows -> {len(merged)} total exercises")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", help="source PDF; if given, re-extract+match before merging")
    args = ap.parse_args(argv)

    if args.pdf:
        sequences = _all_sequences(Path(args.pdf))
        print(f"extracted {len(sequences)} distinct solution sequences")
        matched = match_sequences(sequences)
        full = sum(1 for v in matched.values() if v["kind"] == "full")
        pref = sum(1 for v in matched.values() if v["kind"] == "prefix")
        print(f"verified matches: {len(matched)}/{len(_load_fens())} "
              f"(full={full}, prefix={pref})")
        _VERIFIED.write_text(json.dumps(matched, ensure_ascii=False, indent=1))
    else:
        if not _VERIFIED.is_file():
            sys.exit("no solutions_verified.json — run once with --pdf first")
        matched = json.loads(_VERIFIED.read_text())
        print(f"loaded {len(matched)} verified matches from {_VERIFIED.name}")

    merge(_rows_from_matched(matched))


if __name__ == "__main__":
    main()
