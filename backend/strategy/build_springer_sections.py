"""Rebuild Springer's per-page section metadata from the source PDF.

The Springer course ("Cours Springer", niveau 5) is structured as 10 *thèmes*,
each with a canonical title (Thème 1 "Le classique d'attaque", Thème 2
"L'attaque Hoogland", … Thème 10 "Se préparer à une partie"). The canonical
ordered list lives in the PDF's table of contents (pages 4-7) and is echoed at
the top of every theme's intro page.

The previous extractor (``extract_strategy_sections.py``) was generic and noisy
on this book: it mapped early pages to the wrong themes (Thème 3, 6, 8, 10 on
the front-matter pages), latched onto paragraph numbers ("1.1") and stray body
lines ("DIAGRAMME 7", "PROBLÈME 24") as chapter titles, and so the manual view
showed themes out of order with garbage names.

This script rebuilds ``pages/springer/diagram_sections.json`` cleanly:

  1. Each thème opens on an intro page carrying the marker
     "Ce que vous apprenez dans ce thème:"; the page's first text line is the
     book-faithful thème title. Scanning the body for that marker yields the
     ordered ``(theme_no, title, first_page)`` directly — themes already appear
     in ascending page order, so theme_no is just the running index.
  2. Forward-fill each thème's heading/title across its pages until the next
     thème's intro page. The final thème runs to the start of the back-matter
     "Combinaisons" solutions part (which is not a thème and is left unmapped).

Output shape (unchanged from before)::

    { "<page>": {"heading": "Thème N", "title": "<canonical title>"}, … }

Re-runnable / idempotent: it always rederives from the PDF and overwrites.

Usage (from backend/)::

    python -m strategy.build_springer_sections
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

# The corpus PDF is not vendored into the repo; it lives in the sibling
# ``dilf`` checkout. Allow an override via env for portability.
_DEFAULT_PDF = Path("/home/user/dilf/docs/corpus/springercourse.pdf")
_PDF = Path(os.environ.get("SPRINGER_PDF", _DEFAULT_PDF))

_OUT = Path(__file__).resolve().parent / "pages" / "springer" / "diagram_sections.json"

# Number of pages in the PDF (cheap to hardcode; verified at runtime).
_N_PAGES = 409
# Front matter (cover + introduction + table of contents, pages 1-7) is skipped
# when scanning the body; the first thème opens on page 8.
_FIRST_BODY_PAGE = 8

# Every thème's intro page carries this marker; its first text line is the
# thème's canonical title.
_INTRO_RE = re.compile(r"Ce que vous apprenez dans ce th[eè]me")
# The back-matter solutions part ("Combinaisons" / "Niveau 5") that follows the
# last thème — not a thème, left unmapped.
_SOLUTIONS_RE = re.compile(r"^\s*Combinaisons\s*$\s*^\s*Niveau\b", re.MULTILINE)


def _page_text(page: int) -> str:
    """Return the text layer of one 1-based PDF page via pdftotext."""
    out = subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), str(_PDF), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def _first_line(txt: str) -> str:
    """First non-empty line of a page's text, whitespace-collapsed."""
    for line in txt.splitlines():
        line = line.strip()
        if line:
            return " ".join(line.split())
    return ""


def _solutions_start_page() -> int:
    """First page of the back-matter solutions part, or _N_PAGES+1 if none."""
    for page in range(_FIRST_BODY_PAGE, _N_PAGES + 1):
        if _SOLUTIONS_RE.search(_page_text(page)):
            return page
    return _N_PAGES + 1


def find_theme_pages() -> list[tuple[int, str, int]]:
    """Return ordered ``[(theme_no, title, first_page), …]`` for the 10 thèmes.

    Themes appear strictly in ascending page order, so theme_no is the running
    1-based index of the intro pages found.
    """
    themes: list[tuple[int, str, int]] = []
    for page in range(_FIRST_BODY_PAGE, _N_PAGES + 1):
        txt = _page_text(page)
        if _INTRO_RE.search(txt):
            title = _first_line(txt)
            themes.append((len(themes) + 1, title, page))
    return themes


def build() -> dict[str, dict[str, str]]:
    themes = find_theme_pages()
    solutions = _solutions_start_page()

    out: dict[str, dict[str, str]] = {}
    for idx, (theme_no, title, start_page) in enumerate(themes):
        end_page = (themes[idx + 1][2]
                    if idx + 1 < len(themes) else solutions)
        heading = f"Thème {theme_no}"
        for pg in range(start_page, end_page):
            out[str(pg)] = {"heading": heading, "title": title}
    return out


def main() -> None:
    if not _PDF.is_file():
        raise SystemExit(f"source PDF not found: {_PDF}")

    sections = build()
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(sections, indent=2, ensure_ascii=False))

    themes = find_theme_pages()
    print(f"wrote {len(sections)} page entries to {_OUT}")
    print(f"located {len(themes)}/10 thème intro pages")
    for theme_no, title, start_page in themes:
        print(f"  Thème {theme_no:>2} (p.{start_page}): {title}")
    if len(themes) != 10:
        print(f"WARNING: expected 10 thèmes, found {len(themes)}")


if __name__ == "__main__":
    main()
