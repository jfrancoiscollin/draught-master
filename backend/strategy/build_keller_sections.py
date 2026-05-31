"""Tag every Keller diagram page with its printed *chapter theme*.

The Keller manual ("Le système Keller") groups its diagrams into numbered
chapters whose titles sit in the page text layer as ``N - TITRE`` headings
(e.g. "1 – LES FONDATIONS", "5 - LE JEU D'ENCERCLEMENT", "6 - L'AVANCÉE À
24"). The generic theme resolver in ``build_position_library`` only matches a
strict "Leçon|Thème|Chapitre|Partie N" pattern, so Keller's "N - TITRE"
headings produced no theme at all (0/113 positions themed).

This one-off script (run locally; not imported at runtime) reads the chapter
title on each diagram page, strips the leading number, normalises the
ALL-CAPS title to sentence case, forward-fills it across pages that only
continue a chapter, and writes the per-page ``theme`` field that
``build_position_library`` already honours (the source-agnostic fallback
added for Goedemoed):

    backend/strategy/pages/keller/diagram_sections.json
        { "<page>": {"heading": <raw>, "title": <raw>, "theme": <clean>}, ... }

Existing ``heading``/``title`` keys are preserved; only ``theme`` is added.

Usage (from backend/):
    python -m strategy.build_keller_sections
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_SECTIONS = Path(__file__).resolve().parent / "pages" / "keller" / "diagram_sections.json"

# A genuine chapter heading: "N - TITRE" / "N – TITRE". The number is a
# sub-chapter index that repeats across sections, so we drop it and keep the
# title.
_CHAPTER_RE = re.compile(r"^\s*(\d+)\s*[-–]\s*(.+?)\s*$")
# Move sequences inside a heading mean it is wrapped prose, not a title.
_MOVE_RE = re.compile(r"\d{1,2}[-x]\d{1,2}")


def _clean_title(title: str) -> str:
    """ALL-CAPS book title → sentence case, French apostrophes tidied."""
    t = " ".join(title.split())
    # Sentence case while keeping standalone capitalised tokens reasonable.
    t = t.capitalize()
    # Re-tidy the elided article casing: "L'avancee" not "L'Avancee" is fine,
    # but ``capitalize`` lowercases after the apostrophe — acceptable for FR.
    return t


def _chapter_of(heading: str | None) -> str | None:
    h = (heading or "").strip()
    m = _CHAPTER_RE.match(h)
    if not m:
        return None
    title = m.group(2).strip()
    if "...." in title:            # table-of-contents dot leader
        return None
    if _MOVE_RE.search(title):       # wrapped solution text
        return None
    if re.search(r"\d{2,}\s*$", title):  # trailing page number (TOC)
        return None
    if len(title) < 4:
        return None
    return _clean_title(title)


def build() -> dict[str, dict]:
    sections = json.loads(_SECTIONS.read_text())
    pages = sorted(sections, key=int)

    # Forward-fill: a page with no chapter heading of its own continues the
    # previous chapter. The heading sequence is monotone per section.
    out: dict[str, dict] = {}
    current: str | None = None
    for pg in pages:
        sec = dict(sections[pg])          # preserve heading/title
        theme = _chapter_of(sec.get("heading"))
        if theme:
            current = theme
        if current:
            sec["theme"] = current
        out[pg] = sec
    return out


def main(argv=None):
    sections = build()
    _SECTIONS.write_text(json.dumps(sections, indent=2, ensure_ascii=False))

    from collections import Counter
    dist = Counter(v["theme"] for v in sections.values() if v.get("theme"))
    tagged = sum(1 for v in sections.values() if v.get("theme"))
    print(f"{tagged}/{len(sections)} pages tagged across {len(dist)} chapter themes:")
    for theme, n in dist.most_common():
        print(f"  {n:3d} pages  {theme}")


if __name__ == "__main__":
    main()
