"""Attach manual example positions to the strategic knowledge-base tips.

For every tip in ``knowledge_base.json`` this finds the diagram positions
(from the consolidated ``position_library``) that *actually* exhibit the
tip's pattern — by reusing the very same feature extractor and matching
rules the game advisor uses at runtime (``scan_advisor._board_features``
+ phase/conditions/require_all). So an example is only attached when the
real position would trigger the tip in a game: no text-matching guesswork.

The result is written back as an ``example_positions`` list on each tip
(provenance + FEN), letting the UI show "seen in the manuals" boards next
to the abstract advice.

Run from ``backend/``::

    python -m strategy.enrich_tips           # write into knowledge_base.json
    python -m strategy.enrich_tips --dry-run # report only

Idempotent: existing ``example_positions`` are recomputed from scratch.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import scan_advisor as adv
from game_engine import fen_to_board, get_legal_moves

from . import position_library as lib

_KB_PATH = Path(__file__).resolve().parent.parent / "knowledge_base.json"

# Cap per tip — enough to illustrate, few enough to stay readable.
_MAX_EXAMPLES = 5
_EXAMPLE_FIELDS = ("id", "source", "page", "number", "fen", "kind")


def _features_for(position: dict) -> tuple[set[str], str]:
    """Production feature set + game phase for one library position."""
    st = fen_to_board(position["fen"])
    counts = adv._piece_counts(st)
    phase = adv._phase(adv._total_pieces(counts))
    legal_cnt = len(get_legal_moves(st))
    feats = adv._board_features(st, counts, phase, [], None, legal_cnt)
    return feats, phase


def _matches(tip: dict, feats: set[str], phase: str) -> bool:
    if phase not in tip.get("phase", []):
        return False
    conds = tip.get("conditions", [])
    if not conds:
        return False
    if tip.get("require_all", False):
        return all(c in feats for c in conds)
    return any(c in feats for c in conds)


def _pick(matched: list[dict]) -> list[dict]:
    """Human-verified first, de-duplicated by FEN, spread across sources.

    The examples illustrate a tip, so variety matters: rather than fill the
    cap from the alphabetically-first sources, we round-robin across sources
    (human-verified positions taking priority within each), so every source
    that matches the tip gets a chance to appear.
    """
    from collections import OrderedDict

    by_source: "OrderedDict[str, list[dict]]" = OrderedDict()
    for p in sorted(
        matched,
        key=lambda p: (0 if p["kind"] == "human" else 1, p["source"], p["page"], p["number"]),
    ):
        by_source.setdefault(p["source"], []).append(p)

    seen: set[str] = set()
    out: list[dict] = []
    # One pass per round; each round takes the next position from each source.
    while len(out) < _MAX_EXAMPLES and any(by_source.values()):
        for queue in by_source.values():
            while queue:
                p = queue.pop(0)
                if p["fen"] in seen:
                    continue
                seen.add(p["fen"])
                out.append({k: p.get(k) for k in _EXAMPLE_FIELDS})
                break
            if len(out) >= _MAX_EXAMPLES:
                break
    return out


def compute_enriched() -> list[dict]:
    """Return the tips list with freshly-computed ``example_positions``.

    Pure (no file write), so a freshness test can compare it against the
    committed ``knowledge_base.json`` and catch a stale artefact whenever the
    position library changes (e.g. a new manual is scanned in).
    """
    tips = json.loads(_KB_PATH.read_text())["tips"]
    positions = lib.valid_positions()
    # Precompute features once per position.
    precomputed = [(p, *_features_for(p)) for p in positions]

    for tip in tips:
        matched = [p for (p, feats, phase) in precomputed if _matches(tip, feats, phase)]
        examples = _pick(matched)
        if examples:
            tip["example_positions"] = examples
        else:
            # Idempotent: drop any stale examples when nothing matches now.
            tip.pop("example_positions", None)
    return tips


def enrich(dry_run: bool = False) -> dict[str, int]:
    tips = compute_enriched()
    report = {t["id"]: len(t["example_positions"]) for t in tips if t.get("example_positions")}

    if not dry_run:
        payload = {"tips": tips}
        _KB_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return report


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    report = enrich(dry_run=dry)
    total_examples = sum(report.values())
    print(
        f"[{'dry-run' if dry else 'ok'}] {len(report)} tips enriched "
        f"with {total_examples} example positions"
    )
    for tip_id, n in sorted(report.items(), key=lambda kv: -kv[1]):
        print(f"     {tip_id:28s} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
