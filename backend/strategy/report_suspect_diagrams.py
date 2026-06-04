"""Worklist of *suspect* Goedemoed diagrams — auto-detected FENs that are
almost certainly wrong, ranked by confidence, with a hint at the faulty area.

Why these are trustworthy suspects
----------------------------------
Each printed solution line is replayed (ply by ply) on every detected diagram
FEN. When a line's first >= 4 plies are legal on **exactly one** diagram, that
diagram is uniquely *pinned* as the one the solution belongs to — yet if the
**full** line does not replay, the pinned FEN must be wrong at the point where
the line breaks. The breaking move's squares localise the error.

So every row is a diagram where:
  * we are confident *which* diagram it is (unique legal prefix), and
  * we are confident the FEN is *wrong* (the rest of the proven line is illegal).

Fixing it (via the in-app "✎ Corriger la position" annotator -> paste the JSON
into ``diagrams_fens.json``) both renders the right board **and** unlocks a
verified solution on the next exercise rebuild.

The longer the legal prefix, the smaller the error (e.g. 62/63 = the whole line
works bar the last move -> a single late square is off). Work top-down.

Already hand-verified diagrams (present in ``diagrams_fens.json``) are skipped,
so the list shrinks as corrections land.

Usage (from backend/, needs the source PDFs)::

    python -m strategy.report_suspect_diagrams \
        --pdf2 /home/user/dilf/docs/corpus/Exercise_2.pdf \
        --pdf3 /home/user/dilf/docs/corpus/Exercise_3.pdf \
        --out strategy/SUSPECT_DIAGRAMS.md
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

from game_engine import apply_move, board_to_fen, fen_to_board, get_legal_moves

from .api import _load_diagram_fens
from .build_goedemoed_exercises import _all_sequences, _load_fens, _tok_sig

_MIN_PREFIX = 4  # shortest legal prefix that still pins a unique diagram

# Piece codes for the single-square repair search.
_EMPTY, _WM, _WK, _BM, _BK = 0, 1, 2, 3, 4
_STATES = (_EMPTY, _WM, _WK, _BM, _BK)
_PIECE_FR = {_EMPTY: "vide", _WM: "pion blanc", _WK: "dame blanche",
             _BM: "pion noir", _BK: "dame noire"}


def _tok_move(state, tok):
    a, b, cap = _tok_sig(tok)
    for m in get_legal_moves(state):
        if m.path[0] == a and m.path[-1] == b and bool(m.captures) == cap:
            return m
    return None


def _prefix_len(fen: str, turn: str, toks: list[str]) -> int:
    st = fen_to_board(fen)
    st.turn = turn
    n = 0
    for tok in toks:
        m = _tok_move(st, tok)
        if m is None:
            return n
        n += 1
        st = apply_move(st, m)
    return n


def _full_legal(fen: str, turn: str, toks: list[str]) -> bool:
    st = fen_to_board(fen)
    st.turn = turn
    for tok in toks:
        m = _tok_move(st, tok)
        if m is None:
            return False
        st = apply_move(st, m)
    return True


def _single_square_fix(fen: str, turn: str, toks: list[str]):
    """If exactly one single-square edit makes the *whole* line replay, return
    ``(square, old_piece_fr, new_piece_fr)``; else None.

    A long forced line going fully legal from one piece change is near-certain
    proof of a localised detection error — and gives the operator the precise
    correction to confirm against the crop. Diagrams needing >=2 edits (or none)
    are left as mere *candidates*: those include solution-extraction artifacts
    (an un-stripped variation desyncs a long line), which are NOT FEN errors.
    """
    base = fen_to_board(fen)
    fixes = set()
    for sq in range(1, 51):
        orig = base.board[sq]
        for st in _STATES:
            if st == orig:
                continue
            base.board[sq] = st
            ok = _full_legal(board_to_fen(base), turn, toks)
            base.board[sq] = orig
            if ok:
                fixes.add((sq, orig, st))
    if len({(sq, st) for sq, _, st in fixes}) != 1:
        return None
    sq, orig, st = next(iter(fixes))
    return sq, _PIECE_FR[orig], _PIECE_FR[st]


def suspects(source: str, pdf: Path, verify_fixes: bool = False) -> list[dict]:
    """Ranked suspect diagrams for one source (most confident first)."""
    seqs = _all_sequences(pdf)
    fens = _load_fens(source)
    lib = {p["id"]: p for p in fens}
    id2pn = {p["id"]: (p["page"], p["number"]) for p in fens}
    human = set(_load_diagram_fens(source).keys())

    index: dict[tuple, list] = defaultdict(list)
    for p in fens:
        for turn in ("white", "black"):
            st = fen_to_board(p["fen"])
            st.turn = turn
            for m in get_legal_moves(st):
                index[(m.path[0], m.path[-1], bool(m.captures), turn)].append(p["id"])

    found: dict[tuple, dict] = {}
    for toks in seqs:
        a, b, cap = _tok_sig(toks[0])
        cands = set(index.get((a, b, cap, "white"), []) + index.get((a, b, cap, "black"), []))
        scored = []
        for did in cands:
            p = lib[did]
            for turn in ("white", "black"):
                n = _prefix_len(p["fen"], turn, toks)
                if n > 0:
                    scored.append((n, did, turn))
        if not scored:
            continue
        maxn = max(n for n, _, _ in scored)
        if maxn == len(toks) or maxn < _MIN_PREFIX:
            continue  # full match (not suspect) or too short to pin
        best = [(d, t) for n, d, t in scored if n == maxn]
        if len({d for d, _ in best}) != 1:
            continue  # ambiguous pin
        did, turn = best[0]
        pn = id2pn[did]
        if pn in human:
            continue  # already corrected
        brk = toks[maxn]
        sq = [int(x) for x in re.split("[-x]", brk) if x]
        row = {
            "page": pn[0], "number": pn[1], "side": "B" if turn == "black" else "W",
            "prefix": maxn, "len": len(toks), "breaks_at": brk, "suspect_squares": sq[:2],
            "fen": lib[did]["fen"], "turn": turn, "toks": toks, "fix": None,
        }
        if pn not in found or found[pn]["prefix"] < maxn:
            found[pn] = row

    rows = list(found.values())
    if verify_fixes:
        for r in rows:
            r["fix"] = _single_square_fix(r["fen"], r["turn"], r["toks"])
    for r in rows:  # drop bulky internals before returning
        r.pop("fen", None); r.pop("turn", None); r.pop("toks", None)
    return sorted(rows, key=lambda c: (-c["prefix"], c["page"], c["number"]))


def _render_md(by_source: dict[str, list[dict]]) -> str:
    out = ["# Diagrammes suspects (FEN auto probablement faux)", ""]
    out.append(
        "Diagrammes épinglés de façon unique par une solution imprimée mais dont "
        "la ligne ne se rejoue pas entièrement. Corriger via « ✎ Corriger la "
        "position » (coller le JSON dans `diagrams_fens.json`).\n\n"
        "**Attention** : un *long* préfixe n'implique PAS une petite erreur — une "
        "ligne longue qui casse tard est souvent un artefact d'extraction "
        "(variante non retirée), pas un FEN faux. Le signal fiable est la section "
        "« corrections confirmées » : une retouche d'**une seule case** y rend la "
        "solution *entière* légale (preuve quasi-certaine), avec la case exacte à "
        "vérifier sur le crop. Les autres sont de simples candidats."
    )
    for source, rows in by_source.items():
        confirmed = [r for r in rows if r.get("fix")]
        candidates = [r for r in rows if not r.get("fix")]
        out += ["", f"## {source}", "",
                f"### ✅ Corrections confirmées (1 case) — {len(confirmed)}", ""]
        if confirmed:
            out += ["| page | # | trait | ligne | case | correction |",
                    "|---:|---:|:--:|:--:|---:|:--|"]
            for c in sorted(confirmed, key=lambda c: (c["page"], c["number"])):
                sq, old, new = c["fix"]
                out.append(
                    f"| {c['page']} | {c['number']} | {c['side']} | "
                    f"{c['len']} coups | {sq} | {old} → {new} |"
                )
        else:
            out.append("_(aucune — relancer avec `--verify-fixes`)_")
        out += ["", f"### ❓ Candidats (à vérifier, peut contenir des artefacts) — {len(candidates)}", "",
                "| page | # | trait | préfixe légal | casse au coup | cases à inspecter |",
                "|---:|---:|:--:|:--:|:--:|:--|"]
        for c in candidates:
            out.append(
                f"| {c['page']} | {c['number']} | {c['side']} | "
                f"{c['prefix']}/{c['len']} | {c['breaks_at']} | {c['suspect_squares']} |"
            )
    return "\n".join(out) + "\n"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf2", default="/home/user/dilf/docs/corpus/Exercise_2.pdf")
    ap.add_argument("--pdf3", default="/home/user/dilf/docs/corpus/Exercise_3.pdf")
    ap.add_argument("--out", default="strategy/SUSPECT_DIAGRAMS.md")
    ap.add_argument("--verify-fixes", action="store_true",
                    help="search a unique single-square fix per suspect (slower)")
    args = ap.parse_args(argv)

    by_source = {}
    for source, pdf in (("GOEDEMOED", args.pdf2), ("GOEDEMOED3", args.pdf3)):
        p = Path(pdf)
        if not p.is_file():
            print(f"skip {source}: {pdf} not found")
            continue
        rows = suspects(source, p, verify_fixes=args.verify_fixes)
        by_source[source] = rows
        n_fix = sum(1 for r in rows if r.get("fix"))
        print(f"{source}: {len(rows)} suspects, {n_fix} with a confirmed 1-square fix")

    Path(args.out).write_text(_render_md(by_source), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
