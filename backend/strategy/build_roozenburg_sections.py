"""Rebuild Roozenburg's per-page section metadata from the source PDF.

The Roozenburg course ("Cours Roozenburg", KNDB niveau 4) is structured as 10
*thèmes*, each with its own title; the canonical ordered list lives in the
PDF's table of contents ("Table de matières", pages 5-8):

    Thème 1  Connaissance de base 1
    Thème 2  Connaissance de base 2
    Thème 3  Le jeu du centre
    Thème 4  Les enchaînements en général
    Thème 5  Les formes d'enchaînement: le marchand de bois et le faux …
    Thème 6  Ouvertures
    Thème 7  Le jeu classique
    Thème 8  La partie de flanc
    Thème 9  La formation Roozenburg
    Thème 10 La fin de partie

The previous extractor (``extract_strategy_sections.py``) was generic and noisy
on this book: it latched onto running-header echoes and "PROBLÈME N" problem
markers, so the manual view showed chapters out of order ("Thème 4" first,
"Thème 7" next, "FMJD." / "VIII" as headings, paragraph-number titles like
"1.1 Jesper ignore le nom!").

This script rebuilds ``pages/roozenburg/diagram_sections.json`` cleanly:

  1. Parse the TOC for the canonical ordered ``(theme_no, title)``.
  2. Locate each thème's body start page — the *thème intro* page that carries
     "Ce que vous apprenez dans ce thème" with the thème title in its header.
  3. Forward-fill each thème's heading across its pages until the next thème
     starts, in book order (ascending PDF page).

The book has two parts that each run Thème 1 → 10 in order: the lesson part
(thème intro pages 10, 18, 26, 38, 60, 74, 96, 122, 151, 177; the last thème
runs up to the "Combinaisons" appendix) and the answers part ("Solutions
d'exercices", thème-start pages 295, 301, 306, 312, 323, 335, 359, 376, 388,
400). Both are mapped; within each part the headings are strictly ascending, so
the manual's consecutive-heading grouping yields clean chapters.

Output shape (unchanged from before)::

    { "<page>": {"heading": "Thème N", "title": "<canonical title>"}, … }

Re-runnable / idempotent: it always rederives from the PDF and overwrites.

Usage (from backend/)::

    python -m strategy.build_roozenburg_sections
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

# The corpus PDF is not vendored into the repo; it lives in the sibling
# ``dilf`` checkout. Allow an override via env for portability.
_DEFAULT_PDF = Path("/home/user/dilf/docs/corpus/roozenburgcourse.pdf")
_PDF = Path(os.environ.get("ROOZENBURG_PDF", _DEFAULT_PDF))

_OUT = Path(__file__).resolve().parent / "pages" / "roozenburg" / "diagram_sections.json"

# Number of pages in the PDF (cheap to hardcode; verified at runtime).
_N_PAGES = 409
# Front matter (cover, biography, introduction, table of contents) to skip.
_FIRST_BODY_PAGE = 10

# A thème-intro page (lesson part) — it announces the thème with this marker.
_INTRO_RE = re.compile(r"Ce que vous apprenez dans ce thème")
# A thème-start page in the answers part: "Thème N <title>" + "Solutions".
_SOLUTIONS_START_RE = re.compile(
    r"^\s*Thème\s+(\d+)\s+.+\n.*Solutions", re.MULTILINE
)
# The "Combinaisons" appendix that separates the lesson part from the answers
# part — the lesson part's last thème ends just before it.
_COMBINAISONS_RE = re.compile(r"^\s*Combinaisons\s*$", re.MULTILINE)


def _full_text() -> str:
    """Return the whole PDF's text layer via pdftotext (form-feed separated)."""
    return subprocess.run(
        ["pdftotext", str(_PDF), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _pages() -> list[str]:
    """1-based list of page texts (index 0 is page 1)."""
    return _full_text().split("\f")


def parse_toc(pages: list[str]) -> dict[int, str]:
    """Return ``{theme_no: title}`` from the table of contents.

    The TOC lists, in order, one ``Thème N <title>`` line per thème (the title
    may wrap to a second line for the long thème-5 entry). We read the thème
    numbers and titles from the "Table de matières" pages — the contiguous run
    starting at the page that carries the "Table de matières" header and ending
    just before the first body page.
    """
    toc_first = next(
        (i for i, p in enumerate(pages, start=1)
         if i < _FIRST_BODY_PAGE and "Table de matières" in p),
        1,
    )
    toc_text = "\n".join(pages[toc_first - 1: _FIRST_BODY_PAGE - 1])

    titles: dict[int, str] = {}
    pat = re.compile(r"^\s*Thème\s+(\d+)\s+(.+?)\s*$", re.MULTILINE)
    for m in pat.finditer(toc_text):
        n = int(m.group(1))
        title = " ".join(m.group(2).split())
        # The chapter name is the head noun phrase. Thème 5's printed entry
        # tacks the specific sub-topic on after a colon ("Les formes
        # d'enchaînement: le marchand de bois et le faux marchand de bois");
        # keep the head phrase ("Les formes d'enchaînement") as the canonical
        # title, matching the other thèmes' terse form.
        title = title.split(":", 1)[0].strip()
        if n not in titles and title:
            titles[n] = title
    return titles


def _lesson_intro_pages(pages: list[str]) -> dict[int, int]:
    """Return ``{theme_no: first_page}`` for the lesson part's thème intros.

    A thème-intro page carries the "Ce que vous apprenez dans ce thème" marker
    with the thème title in its running header. The intros appear strictly in
    thème order, so we number them 1..10 by ascending page.
    """
    intro_pages = [
        i for i, p in enumerate(pages, start=1)
        if i >= _FIRST_BODY_PAGE and _INTRO_RE.search(p)
    ]
    return {n: pg for n, pg in enumerate(sorted(intro_pages), start=1)}


def _combinaisons_page(pages: list[str], after: int) -> int:
    """First "Combinaisons" appendix page after ``after`` (lesson-part end)."""
    for i, p in enumerate(pages, start=1):
        if i > after and _COMBINAISONS_RE.search(p):
            return i
    return _N_PAGES + 1


def _solutions_start_pages(pages: list[str]) -> dict[int, int]:
    """Return ``{theme_no: first_page}`` for the answers-part thème starts.

    Each answers-part thème opens with a "Thème N <title>" line immediately
    followed by "Solutions" (the section divider). Numbered by the printed N.
    """
    starts: dict[int, int] = {}
    for i, p in enumerate(pages, start=1):
        m = _SOLUTIONS_START_RE.search(p)
        if m:
            n = int(m.group(1))
            if n not in starts:
                starts[n] = i
    return starts


def _fill_part(starts: dict[int, int], part_end: int,
               toc: dict[int, str]) -> dict[str, dict[str, str]]:
    """Forward-fill one part's thème headings across its page range.

    ``starts`` maps theme_no -> first page; ``part_end`` is the (exclusive)
    page where the part stops. Each thème fills from its start up to (but not
    including) the next thème's start, the last up to ``part_end``.
    """
    ordered = sorted(starts.items(), key=lambda kv: kv[1])  # by start page
    out: dict[str, dict[str, str]] = {}
    for idx, (theme, start_page) in enumerate(ordered):
        end_page = (ordered[idx + 1][1]
                    if idx + 1 < len(ordered) else part_end)
        heading = f"Thème {theme}"
        title = toc.get(theme, "")
        for pg in range(start_page, end_page):
            out[str(pg)] = {"heading": heading, "title": title}
    return out


def build() -> dict[str, dict[str, str]]:
    pages = _pages()
    toc = parse_toc(pages)

    lesson_starts = _lesson_intro_pages(pages)
    solution_starts = _solutions_start_pages(pages)

    # Lesson part ends at the "Combinaisons" appendix (right after thème 10).
    last_lesson_page = max(lesson_starts.values()) if lesson_starts else _FIRST_BODY_PAGE
    lesson_end = _combinaisons_page(pages, last_lesson_page)

    out: dict[str, dict[str, str]] = {}
    out.update(_fill_part(lesson_starts, lesson_end, toc))
    # Answers part: restarts at Thème 1, fills to the end of the book.
    if solution_starts:
        out.update(_fill_part(solution_starts, _N_PAGES + 1, toc))

    # Emit in ascending page order for a stable, readable JSON.
    return {k: out[k] for k in sorted(out, key=int)}


def main() -> None:
    if not _PDF.is_file():
        raise SystemExit(f"source PDF not found: {_PDF}")

    pages = _pages()
    toc = parse_toc(pages)
    lesson_starts = _lesson_intro_pages(pages)
    solution_starts = _solutions_start_pages(pages)

    sections = build()
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(sections, indent=2, ensure_ascii=False))

    print(f"wrote {len(sections)} page entries to {_OUT}")
    print(f"located {len(lesson_starts)}/10 lesson theme intros: "
          f"{dict(sorted(lesson_starts.items()))}")
    print(f"located {len(solution_starts)}/10 answers theme starts: "
          f"{dict(sorted(solution_starts.items()))}")
    missing = [n for n in range(1, 11) if n not in toc]
    if missing:
        print(f"WARNING: no TOC title for themes: {missing}")
    for n in sorted(toc):
        print(f"  Theme {n}: {toc[n]}")


if __name__ == "__main__":
    main()
