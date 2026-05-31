"""Tag every Goedemoed diagram page with its printed *section theme*.

The Goedemoed volume groups its diagrams into didactic sections — "Judging
positions", "Which move do you play?", "Calculation", "Combinations",
"Forcings", "Strategy"… — whose titles sit in the page text layer. Unlike the
French manuals, these are not numbered "Leçon N" headings, so the generic
theme resolver in ``build_position_library`` cannot pick them up.

This one-off script (run locally; not imported at runtime) reads the section
title on each diagram page, forward-fills it across pages that only continue a
section, translates it to the app's French convention, and writes:

    backend/strategy/pages/goedemoed/diagram_sections.json
        { "<page>": {"theme": "<french section theme>"}, ... }

``build_position_library`` then attaches ``theme`` to each Goedemoed position,
making the non-tactical study diagrams (Judging, Which-move, Good-or-not,
Strategy, Analysing…) browsable in the strategy knowledge base.

Usage (from backend/):
    python -m strategy.build_goedemoed_sections \
        --pdf /home/user/dilf/docs/corpus/Exercise_2.pdf
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_OUT = _HERE / "pages" / "goedemoed"

# Section cues printed in the volume → canonical French study theme. Order
# matters: the first cue found in a heading line wins, so put the more
# specific attack variants before the generic "Combinations"/"Forcings".
_CUES: list[tuple[str, str]] = [
    ("which move", "Quel coup jouer ?"),
    ("good or not", "Bon ou pas ?"),
    ("judging position", "Juger la position"),
    ("analysing position", "Analyser la position"),
    ("finish the position", "Finir la position"),
    ("composing", "Composer un coup"),
    ("cool shot", "Jolis coups"),
    ("centre attack", "Attaque au centre"),
    ("classical attack", "Attaque classique"),
    ("roozenburg", "Attaque Roozenburg"),
    ("highland", "Attaque Highland"),
    ("calculation", "Calcul"),
    ("forcing", "Coups forcés"),
    ("combination", "Combinaisons"),
    ("strategy", "Stratégie"),
    ("make a movie", "Dérouler la partie"),
    ("movie", "Dérouler la partie"),
]

_MOVE_RE = re.compile(r"\d{1,2}[-x]\d{1,2}")


def _classify(line: str) -> str | None:
    low = line.lower()
    for cue, theme in _CUES:
        if cue in low:
            return theme
    return None


def _heading_on(pdf: Path, page: int) -> str | None:
    """The section theme declared on this page, if any.

    A genuine heading is a short title line (not a sentence or a move
    sequence) that matches one of the known section cues.
    """
    txt = subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
        capture_output=True, text=True,
    ).stdout
    for ln in txt.split("\n"):
        s = ln.strip()
        theme = _classify(s)
        if theme and len(s) <= 42 and not _MOVE_RE.search(s):
            return theme
    return None


def build(pdf: Path) -> dict[str, dict[str, str]]:
    manifest = json.loads((_OUT / "diagrams_manifest.json").read_text())
    pages = sorted({e["page"] for e in manifest["entries"]})

    # Forward-fill: a page with no heading of its own continues the previous
    # section. (Longest such run in the volume is ~6 pages.)
    out: dict[str, dict[str, str]] = {}
    current: str | None = None
    for page in pages:
        h = _heading_on(pdf, page)
        if h:
            current = h
        if current:
            out[str(page)] = {"theme": current}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    args = ap.parse_args(argv)

    sections = build(Path(args.pdf))
    (_OUT / "diagram_sections.json").write_text(
        json.dumps(sections, indent=2, ensure_ascii=False))

    from collections import Counter
    dist = Counter(v["theme"] for v in sections.values())
    print(f"{len(sections)} diagram pages tagged across {len(dist)} themes:")
    for theme, n in dist.most_common():
        print(f"  {n:3d} pages  {theme}")


if __name__ == "__main__":
    main()
