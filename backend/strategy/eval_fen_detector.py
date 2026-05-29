"""Evaluate the rules-based FEN detector against the human annotations.

Compares ``fen_detector.detect_fen(crop)`` to the ground-truth FENs in
``pages/<source>/diagrams_fens.json``.  Reports per-sample status,
exact-match rate, and per-square classification accuracy.  Run from
the repo root::

    python -m backend.strategy.eval_fen_detector            # all sources
    python -m backend.strategy.eval_fen_detector SIJBRANDS  # one source

Designed to be re-runnable each time the detector is tuned: rapid
iteration loop is the whole point at this stage of the project.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from .fen_detector import detect_fen

_PAGES_DIR = Path(__file__).parent / "pages"


def _parse_fen(fen: str) -> dict[int, str]:
    """``W:W3,K5:B12`` → ``{3: 'W', 5: 'WK', 12: 'B'}``.

    Returns a sparse map; absent squares are implicitly empty.  This
    representation makes per-square diffs trivial.
    """
    out: dict[int, str] = {}
    # Strip leading ``W:`` (side to move).  Detector + ground truth both
    # ignore the side-to-move so we don't bother comparing it.
    _, _, body = fen.partition(":")
    for chunk in body.split(":"):
        if not chunk:
            continue
        color = chunk[0]  # 'W' or 'B'
        for tok in chunk[1:].split(","):
            if not tok:
                continue
            if tok.startswith("K"):
                kind = f"{color}K"
                sq = int(tok[1:])
            else:
                kind = color
                sq = int(tok)
            out[sq] = kind
    return out


def _square_diff(gold: dict[int, str], pred: dict[int, str]) -> list[tuple[int, str, str]]:
    """List of ``(square, gold_kind, pred_kind)`` where they disagree.

    ``'.'`` denotes empty.  Includes squares present in either map.
    """
    diffs = []
    for sq in sorted(set(gold) | set(pred)):
        g = gold.get(sq, ".")
        p = pred.get(sq, ".")
        if g != p:
            diffs.append((sq, g, p))
    return diffs


def evaluate(source: str) -> tuple[int, int, int, int]:
    """Return ``(samples, exact_matches, squares_total, squares_correct)``.

    Prints a per-sample summary to stdout — verbose by design so the
    operator can spot the failure patterns (which squares, which piece
    type) without re-running individually.
    """
    src_dir = _PAGES_DIR / source.lower()
    fens_path = src_dir / "diagrams_fens.json"
    crops_dir = src_dir / "diagrams"
    manifest_path = src_dir / "diagrams_manifest.json"
    if not fens_path.is_file():
        print(f"[skip] {source}: no diagrams_fens.json")
        return 0, 0, 0, 0
    if not manifest_path.is_file():
        print(f"[skip] {source}: no diagrams_manifest.json")
        return 0, 0, 0, 0

    fens = json.loads(fens_path.read_text())["entries"]
    manifest = {(e["page"], e["number"]): e["crop"] for e in json.loads(manifest_path.read_text())["entries"]}

    samples = 0
    exact = 0
    sq_total = 0
    sq_correct = 0
    confusion: Counter[tuple[str, str]] = Counter()

    print(f"\n=== {source} ===")
    for entry in fens:
        page = entry["page"]
        number = entry["number"]
        crop = manifest.get((page, number))
        if crop is None:
            print(f"  p.{page} #{number}: no crop in manifest — skip")
            continue
        crop_path = crops_dir / crop
        gold_fen = entry["fen"]
        pred_fen = detect_fen(crop_path)
        gold = _parse_fen(gold_fen)
        pred = _parse_fen(pred_fen)
        diffs = _square_diff(gold, pred)
        samples += 1
        is_exact = not diffs
        if is_exact:
            exact += 1
        # Per-square: 50 playable squares, count agreements (kind match
        # including the empty case) and tally the confusion matrix on the
        # mismatched squares only.
        sq_total += 50
        sq_correct += 50 - len(diffs)
        for _, g, p in diffs:
            confusion[(g, p)] += 1
        status = "OK " if is_exact else f"x{len(diffs):2d}"
        print(f"  [{status}] p.{page:>3} #{number:>2}  gold={gold_fen}")
        if not is_exact:
            print(f"           pred={pred_fen}")
            for sq, g, p in diffs:
                print(f"           sq {sq:>2}: gold={g:>2}  pred={p:>2}")

    print(f"\n  exact-match: {exact}/{samples} = {exact / max(samples, 1):.1%}")
    print(f"  squares:     {sq_correct}/{sq_total} = {sq_correct / max(sq_total, 1):.2%}")
    if confusion:
        print("  confusion (gold → pred), on disagreeing squares only:")
        for (g, p), n in confusion.most_common():
            print(f"    {g:>2} → {p:>2}: {n}")
    return samples, exact, sq_total, sq_correct


def main(argv: list[str]) -> int:
    sources = argv[1:] if len(argv) > 1 else ["SIJBRANDS", "SPRINGER", "ROOZENBURG", "KELLER"]
    totals = (0, 0, 0, 0)
    for src in sources:
        s, e, t, c = evaluate(src)
        totals = (totals[0] + s, totals[1] + e, totals[2] + t, totals[3] + c)
    s, e, t, c = totals
    if len(sources) > 1 and s:
        print(f"\n=== ALL ===")
        print(f"  exact-match: {e}/{s} = {e / s:.1%}")
        print(f"  squares:     {c}/{t} = {c / t:.2%}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
