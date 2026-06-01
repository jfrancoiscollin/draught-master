"""Rebuild Sijbrands' per-page section metadata from the source PDF.

The Sijbrands course ("Cours de jeu de dames") is structured as 10 *thèmes*,
each holding 4 *leçons* (Leçon 1-4 in thème 1, 5-8 in thème 2, … 37-40 in
thème 10). Every leçon has a title; the canonical ordered list lives in the
PDF's table of contents.

The previous extractor (``extract_strategy_sections.py``) was generic and
noisy on this book: it split the body heading "Leçon N <title>" into a bare
"Leçon N" with whatever body line followed as the "title", and it also latched
onto stray table-of-contents cross-references — so the manual view showed
chapters out of order ("Leçon 24" first, duplicate "Thème 1", DIAGRAMME refs
as titles).

This script rebuilds ``pages/sijbrands/diagram_sections.json`` cleanly:

  1. Parse the TOC for the canonical ordered ``(theme_no, lesson_no, title)``.
  2. Scan the body pages for the first occurrence of each "Leçon N" heading —
     the page where that lesson's content starts. Theme-intro pages (which
     list all 4 lessons of a thème under "Dans ce thème/cours:") are skipped,
     as is the front matter (title page + TOC, pages 1-4).
  3. Forward-fill each lesson's heading across its pages until the next lesson
     starts, in book order (ascending PDF page).

The book has two parts that each run Leçon 1 → 40 in order: the lesson part
(pages ~6-134) and the answers part ("Les réponses", pages ~135-202). Both are
mapped; within each part the headings are strictly ascending, so the manual's
consecutive-heading grouping yields clean chapters.

Output shape (unchanged from before)::

    { "<page>": {"heading": "Leçon N", "title": "<canonical title>"}, … }

Re-runnable / idempotent: it always rederives from the PDF and overwrites.

Usage (from backend/)::

    python -m strategy.build_sijbrands_sections
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# The corpus PDF is not vendored into the repo; it lives in the sibling
# ``dilf`` checkout. Allow an override via env for portability.
import os

_DEFAULT_PDF = Path("/home/user/dilf/docs/corpus/sijbrandscourse.pdf")
_PDF = Path(os.environ.get("SIJBRANDS_PDF", _DEFAULT_PDF))

_OUT = Path(__file__).resolve().parent / "pages" / "sijbrands" / "diagram_sections.json"

# Number of pages in the PDF (cheap to hardcode; verified at runtime).
_N_PAGES = 202
# Front matter (cover + table of contents) to skip when scanning the body.
_FIRST_BODY_PAGE = 5

# A "Leçon N" heading at the start of a text line, optionally followed (on the
# same line) by the lesson title — the book-faithful chapter title.
_LECON_RE = re.compile(r"^\s*Leçon\s+(\d+)\b[ \t]*(\S.*)?$", re.MULTILINE)
# Theme-intro pages list every lesson of the thème under one of these markers.
_INTRO_RE = re.compile(r"Dans ce (?:thème|cours)")
# Marks the start of the second part of the book (answers to the exercises),
# which restarts the Leçon 1 → 40 sequence with its own pagination.
_ANSWERS_RE = re.compile(r"Les réponses")


def _page_text(page: int) -> str:
    """Return the text layer of one 1-based PDF page via pdftotext."""
    out = subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), str(_PDF), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def parse_toc() -> dict[int, tuple[int, str]]:
    """Return ``{lesson_no: (theme_no, title)}`` from the table of contents.

    The TOC lists, per thème, four ``Leçon N`` lines followed (in a separate
    text column) by the four titles in the same order. We read the lesson
    numbers and titles from the TOC's body-heading echo block — the part that
    repeats each lesson as "Leçon N <title>    P.PP" on one line, which is the
    most reliable spot to pair number↔title.
    """
    full = subprocess.run(
        ["pdftotext", str(_PDF), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    # Each thème's intro page echoes "Leçon N <title>   <page-ref>" lines. These
    # appear throughout the document (one per thème intro). Collect the first
    # title seen for each lesson number — they are identical everywhere.
    titles: dict[int, str] = {}
    pat = re.compile(r"^\s*Leçon\s+(\d+)\s+(.+?)\s+\d+\.\d+\s*$", re.MULTILINE)
    for m in pat.finditer(full):
        n = int(m.group(1))
        title = " ".join(m.group(2).split())
        if n not in titles and title:
            titles[n] = title

    # Map lesson -> theme (1-4 -> 1, 5-8 -> 2, …).
    return {n: ((n - 1) // 4 + 1, t) for n, t in titles.items()}


def _answers_start_page() -> int:
    """First page of the answers part ("Les réponses"), or _N_PAGES+1 if none."""
    for page in range(_FIRST_BODY_PAGE, _N_PAGES + 1):
        if _ANSWERS_RE.search(_page_text(page)):
            return page
    return _N_PAGES + 1


# A body line that follows "Leçon N" but is clearly not the title.
_NOT_A_TITLE = re.compile(r"^(?:DIAGRAMME|EXERCICE|Diagramme|Exercice)\b")


def _lesson_starts(first: int, last: int) -> dict[int, tuple[int, str | None]]:
    """Return ``{lesson_no: (first_page, inline_title|None)}`` in [first, last].

    A lesson-start page carries exactly one "Leçon N" heading near its top and
    is not a theme-intro page (which lists all four lessons of the thème). When
    the heading line also carries the title ("Leçon 3 De la magie") we keep that
    inline title — it is the book-faithful chapter title and occasionally
    differs from the terse TOC entry. The first page a lesson number appears on
    within the range is its start; later pages forward-fill.
    """
    starts: dict[int, tuple[int, str | None]] = {}
    for page in range(first, last + 1):
        txt = _page_text(page)
        if _INTRO_RE.search(txt):
            continue  # theme-intro page: lists all 4 lessons, not a start
        matches = list(_LECON_RE.finditer(txt))
        if len(matches) != 1:
            continue  # 0 = no heading; >1 = a list/intro page, not a single start
        m = matches[0]
        n = int(m.group(1))
        inline = (m.group(2) or "").strip() or None
        if inline and _NOT_A_TITLE.match(inline):
            inline = None  # title wrapped off this line; use the TOC fallback
        if n not in starts:
            starts[n] = (page, inline)
    return starts


def find_lesson_pages() -> dict[int, tuple[int, str | None]]:
    """Lesson → (first body page, inline title) for the *lesson part*.

    Kept for the build summary; the answers part repeats the same numbers so
    the lesson part alone tells us which of the 40 lessons we located.
    """
    answers = _answers_start_page()
    return _lesson_starts(_FIRST_BODY_PAGE, answers - 1)


def _fill_part(starts: dict[int, tuple[int, str | None]], part_end: int,
               toc: dict[int, tuple[int, str]]) -> dict[str, dict[str, str]]:
    """Forward-fill one part's lesson headings across its page range.

    Title precedence: the book-faithful inline body title, else the TOC title.
    """
    ordered = sorted(starts.items(), key=lambda kv: kv[1][0])  # by start page
    out: dict[str, dict[str, str]] = {}
    for idx, (lesson, (start_page, inline)) in enumerate(ordered):
        end_page = (ordered[idx + 1][1][0]
                    if idx + 1 < len(ordered) else part_end)
        title = inline or toc.get(lesson, (0, ""))[1]
        heading = f"Leçon {lesson}"
        for pg in range(start_page, end_page):
            out[str(pg)] = {"heading": heading, "title": title}
    return out


def build() -> dict[str, dict[str, str]]:
    toc = parse_toc()
    answers = _answers_start_page()

    out: dict[str, dict[str, str]] = {}
    # Lesson part: front matter end .. just before the answers.
    out.update(_fill_part(
        _lesson_starts(_FIRST_BODY_PAGE, answers - 1), answers, toc))
    # Answers part: restarts at Leçon 1, fills to the end of the book.
    if answers <= _N_PAGES:
        out.update(_fill_part(
            _lesson_starts(answers, _N_PAGES), _N_PAGES + 1, toc))
    return out


def main() -> None:
    if not _PDF.is_file():
        raise SystemExit(f"source PDF not found: {_PDF}")

    sections = build()
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(sections, indent=2, ensure_ascii=False))

    starts = find_lesson_pages()
    toc = parse_toc()
    missing = [n for n in range(1, 41) if n not in starts]
    print(f"wrote {len(sections)} page entries to {_OUT}")
    print(f"located {len(starts)}/40 lesson body headings")
    if missing:
        print(f"WARNING: could not locate lesson headings for: {missing}")
    missing_titles = [n for n in starts if n not in toc]
    if missing_titles:
        print(f"WARNING: no TOC title for lessons: {sorted(missing_titles)}")


if __name__ == "__main__":
    main()
