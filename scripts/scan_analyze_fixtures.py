"""Produce ``scan_analysis_debutant.json`` from the 166 BeginnerPosition fixtures.

The new CADRAGE_MANUELS.md "zéro invention" principle requires that
every tactical claim in the manuel is sourced from the Scan engine PV,
not from Claude's reading of the board. This script is the pipeline
step that produces that source: it iterates over
``backend/manuels/fixtures_debutant.py``, runs each starting position
through the Scan engine, and emits the JSON contract documented in
``dilf/docs/pre_process_corpus/scan/README.md``.

Run from the repo root::

    # produce the full file (Scan binary required; ~15-30 min @ 10s/pos)
    python scripts/scan_analyze_fixtures.py --output /path/to/dilf/docs/pre_process_corpus/scan/scan_analysis_debutant.json

    # quick smoke pass: only the first 5 positions
    python scripts/scan_analyze_fixtures.py --output out.json --limit 5

    # incremental: skip positions already analysed in the output file
    # (default behavior; use --force to re-analyse everything)
    python scripts/scan_analyze_fixtures.py --output out.json

    # produce a skeleton with verified=false (no Scan required) — useful
    # to commit the file structure before the real analysis runs
    python scripts/scan_analyze_fixtures.py --output out.json --stub

Design notes
------------
- ``eval_start`` and ``eval_after_pv`` come from a single deep
  ``go think`` per position. Scan's negamax score after deep search
  IS the position's evaluation under best play, which equals the eval
  at the end of the PV. A separate ``play_pv → re-eval`` pass would
  give a more granular ``eval_start`` (the static eval before search);
  it's tracked as future work. For now both fields hold the same number
  and ``notes`` records the simplification.
- ``verified=true`` iff Scan returned a non-None analysis AND the PV is
  non-empty. Forced single-move positions (``forced=True``) still
  qualify (they have a determinate best move even with no search).
- ``winning_for`` is derived from ``eval_after_pv`` with a ±0.5 pawn
  threshold (under that, "draw"). The cadrage requires Scan to be
  authoritative on the verdict; the threshold is just the label
  mapping, not a tactical judgement.
- ``notes`` auto-compares the first PV move to the first token of
  ``published_notation``. Divergence → flag for ``A_VERIFIER_MOTEUR``.
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scan_analyze_fixtures")


def collect_fixtures() -> List[Any]:
    """Discover every ``BEG_*`` BeginnerPosition exposed by the module."""
    mod = importlib.import_module("manuels.fixtures_debutant")
    fixtures = []
    for name in dir(mod):
        if not name.startswith("BEG_"):
            continue
        obj = getattr(mod, name)
        # Heuristic: a BeginnerPosition has both `id` and `state`.
        if hasattr(obj, "id") and hasattr(obj, "state"):
            fixtures.append(obj)
    # Sort by id so the JSON output is stable across runs.
    fixtures.sort(key=lambda f: f.id)
    return fixtures


def first_token(notation: str) -> Optional[str]:
    """First move of a published_notation string. ``"42-37 (19x28) …"`` → ``"42-37"``."""
    if not notation:
        return None
    return notation.split()[0].strip()


def winning_for(eval_score: float, threshold: float = 0.5) -> str:
    if eval_score > threshold:
        return "white"
    if eval_score < -threshold:
        return "black"
    return "draw"


def analysis_stub(fx: Any) -> Dict[str, Any]:
    """Skeleton entry used when Scan isn't available — verified=false so
    the manuel writer never picks it up by accident."""
    return {
        "verified": False,
        "eval_start": 0.0,
        "best_move": None,
        "pv": [],
        "eval_after_pv": 0.0,
        "winning_for": "draw",
        "scan_depth": 0,
        "notes": "Stub — Scan analysis not yet run.",
    }


def _hub_pos_from_pedagogy_state(state: Any) -> str:
    """Build a Hub v2 position string from a ``pedagogy.game.GameState``.

    The backend's own ``scan_engine._build_pos`` expects a
    ``game_engine.GameState`` (51-cell board array), which is a
    different type from the frozenset-based one in dilf. Adapt here
    rather than round-trip through FEN.
    """
    chars: List[str] = []
    for sq in range(1, 51):
        if sq in state.white_men:
            chars.append("w")
        elif sq in state.white_kings:
            chars.append("W")
        elif sq in state.black_men:
            chars.append("b")
        elif sq in state.black_kings:
            chars.append("B")
        else:
            chars.append("e")
    turn = "W" if state.turn == "white" else "B"
    return turn + "".join(chars)


def analyse_one(fx: Any, engine: Any, movetime_s: float) -> Dict[str, Any]:
    hub_pos = _hub_pos_from_pedagogy_state(fx.state)
    t0 = time.monotonic()
    result = engine.evaluate_pos(hub_pos, movetime_s)
    elapsed = time.monotonic() - t0

    if result is None:
        log.warning("%s: Scan timed out after %.1fs", fx.id, elapsed)
        return {
            **analysis_stub(fx),
            "notes": f"Scan timed out (movetime={movetime_s}s).",
        }

    score = result["score"]
    pv = result["pv"]
    best = result["bestMove"]
    forced = result.get("forced", False)

    # Auto-compare PV[0] vs published_notation[0]. The cadrage treats
    # the published notation as suspect when it diverges from Scan.
    # Only relevant when published_notation describes a tactical solution
    # (≥ 2 tokens, or contains a capture/parens). Chapters 1-2 use a
    # single move as illustrative historic notation, not as a solution
    # — no comparison there.
    published_tokens = (fx.published_notation or "").split()
    looks_like_solution = (
        len(published_tokens) >= 2
        or any(c in fx.published_notation for c in ("x", "×", "("))
    )
    notes_parts: List[str] = []
    if forced:
        notes_parts.append("Forced move (no search).")
    if looks_like_solution and published_tokens and best:
        published_first = published_tokens[0]
        if published_first.replace("×", "x") != best.replace("×", "x"):
            notes_parts.append(
                f"DIVERGENCE: published_notation starts with {published_first!r}, "
                f"Scan PV starts with {best!r}. Flag in A_VERIFIER_MOTEUR.md."
            )
        else:
            notes_parts.append("PV first move matches published_notation.")
    if not pv:
        notes_parts.append("Scan returned empty PV.")
    notes_parts.append(
        "Single-pass eval: eval_start == eval_after_pv (deep-search score)."
    )

    return {
        "verified": bool(pv) or forced,
        "eval_start": score,
        "best_move": best,
        "pv": pv,
        "eval_after_pv": score,
        "winning_for": winning_for(score),
        "scan_depth": 0,  # Hub v2 doesn't expose final depth directly; future work.
        "notes": " ".join(notes_parts),
    }


def load_existing(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_atomic(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--output", required=True, type=Path,
                   help="Path to scan_analysis_debutant.json (typically inside the "
                        "dilf checkout: docs/pre_process_corpus/scan/).")
    p.add_argument("--movetime", type=float, default=10.0,
                   help="Per-position Scan time budget in seconds (default 10).")
    p.add_argument("--limit", type=int, default=None,
                   help="Stop after N positions (smoke-test). Default: all 166.")
    p.add_argument("--start-from", type=str, default=None,
                   help="Skip fixtures with id < this value (resume support).")
    p.add_argument("--force", action="store_true",
                   help="Re-analyse positions even if already in the output file.")
    p.add_argument("--stub", action="store_true",
                   help="Don't invoke Scan; emit verified=false skeleton entries. "
                        "Useful for committing the file structure first.")
    args = p.parse_args()

    fixtures = collect_fixtures()
    log.info("Discovered %d fixtures.", len(fixtures))

    existing = load_existing(args.output)
    log.info("Loaded %d existing entries from %s.", len(existing), args.output)

    engine = None
    if not args.stub:
        from scan_engine import ScanEngine, SCAN_PATH  # noqa: WPS433 — late import (no Scan in stub mode)
        engine = ScanEngine(SCAN_PATH, use_book=False)
        log.info("Scan engine ready (path=%s).", SCAN_PATH)

    n_done = 0
    n_skipped = 0
    for fx in fixtures:
        if args.start_from and fx.id < args.start_from:
            continue
        if args.limit is not None and n_done >= args.limit:
            break
        if fx.id in existing and not args.force:
            n_skipped += 1
            continue

        if args.stub:
            existing[fx.id] = analysis_stub(fx)
        else:
            existing[fx.id] = analyse_one(fx, engine, args.movetime)

        n_done += 1
        if n_done % 5 == 0:
            log.info("Progress: %d analysed, %d skipped.", n_done, n_skipped)
            write_atomic(args.output, existing)  # Checkpoint every 5.

    write_atomic(args.output, existing)
    log.info("Done. %d analysed, %d skipped. Wrote %s (%d entries).",
             n_done, n_skipped, args.output, len(existing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
