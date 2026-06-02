"""Rebuild Keller's per-page section metadata from the source PDF's TOC.

The Keller strategic manual ("Le système Keller", by Jean-Pierre Dubois) is a
*positional system* treatise, not an exercise book. Its table of contents
(``SOMMAIRE``, PDF page 4-5) lays out a two-level structure:

  * **Major sections** printed flush-left in ALL CAPS with no leading number
    (``PRESENTATION``, ``LE JEU COMBINATOIRE``, ``LES STRATEGIES DES BLANCS``,
    ``LE JEU DES NOIRS``, ``L'EVOLUTION DES VARIANTES``,
    ``LE SYSTEME KELLER FERME``, ``PARTIES COMMENTEES``, ``CONCLUSION``), plus
    the ``PREFACE`` / ``INTRODUCTION`` front matter.
  * **Numbered chapters** ``N - TITRE`` that restart at 1 inside each major
    section (``1 - LES FONDATIONS``, ``2 - LE JEU DES BLANCS`` …), and inside
    ``PARTIES COMMENTEES`` the six annotated games ``Partie n°N : …``.
  * **Decimal sub-entries** ``N.M - …`` (e.g. ``6.1 - L'attaque (14-19)``)
    which are *sub-chapters*; they fold into their parent numbered chapter.

The previous builder was a one-off *themer*: it left the noisy generic
``heading``/``title`` extraction in place (table-of-contents dot-leader lines
as headings, body sentences as titles) and only bolted on a ``theme`` field.
That made the manual's table-of-contents view show garbage ("1 - LES
COMBINAISONS FONDAMENTALES ........ 86" with title "4", body sentences, etc.)
and out of book order.

This script rebuilds ``pages/keller/diagram_sections.json`` cleanly,
mirroring ``build_sijbrands_sections.py``:

  1. Parse the SOMMAIRE for the canonical *ordered* chapter list, keeping each
     chapter's printed label and its body start page (the printed page numbers
     coincide with the PDF page numbers in this book).
  2. Drop decimal sub-entries (they continue their parent chapter).
  3. Collapse chapters that begin on the same physical page (the book packs
     several short chapters onto one page). Per page we keep a single
     representative heading: a numbered chapter or annotated game wins over a
     bare major-section banner that introduces it on the same page, and the
     first one listed wins among same-rank collisions — i.e. the page is
     attributed to the most specific chapter the book starts there.
  4. Forward-fill each surviving chapter's heading across its pages until the
     next chapter starts, in ascending book order.

Output shape::

    { "<page>": {"heading": "<book label>", "title": ""}, … }

The ``heading`` is the chapter label exactly as the book prints it; it is
unique per chapter (the titles differ even when the leading number repeats
across major sections), so the manual's consecutive-heading grouping yields
one clean chapter per book heading, in order. ``title`` is left empty: the
heading already carries the full book-faithful name, so the manual renders it
verbatim. KELLER is registered in ``_CURATED_SECTION_SOURCES`` so these titles
are trusted as-is rather than run through the noisy-data heuristic.

Re-runnable / idempotent: it always rederives from the PDF and overwrites.
The PDF path is overridable via the ``KELLER_PDF`` env var.

Usage (from backend/)::

    python -m strategy.build_keller_sections
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

_DEFAULT_PDF = Path("/home/user/dilf/docs/corpus/le_systeme_keller.pdf")
_PDF = Path(os.environ.get("KELLER_PDF", _DEFAULT_PDF))

_OUT = Path(__file__).resolve().parent / "pages" / "keller" / "diagram_sections.json"

# Number of pages in the PDF (cheap to hardcode; verified at runtime).
_N_PAGES = 103

# The table of contents lives on these pages.
_TOC_FIRST, _TOC_LAST = 4, 5

# A TOC line ends with a dot-leader and a printed page number, e.g.
#   "1 – LES FONDATIONS................................................6"
# We capture the label (everything before the leader) and the page number.
_TOC_LINE_RE = re.compile(r"^\s*(.+?)\s*\.{2,}\s*(\d+)\s*$")

# A decimal sub-entry ("6.1 - …", "2.3 - …"): folds into its parent chapter.
_DECIMAL_RE = re.compile(r"^\s*\d+\.\d+\b")

# A "specific" chapter (numbered chapter or an annotated game): outranks a bare
# major-section banner that opens on the same page.
_SPECIFIC_RE = re.compile(r"^\s*(?:\d+\s*[-–]|Partie\s+n)", re.IGNORECASE)


def _toc_text() -> str:
    return subprocess.run(
        ["pdftotext", "-f", str(_TOC_FIRST), "-l", str(_TOC_LAST), str(_PDF), "-"],
        capture_output=True, text=True, check=True,
    ).stdout


def _norm(label: str) -> str:
    """Collapse internal whitespace."""
    return " ".join(label.split())


def parse_toc() -> list[tuple[str, int]]:
    """Return the ordered ``[(heading, start_page), …]`` chapter list.

    Reads the SOMMAIRE, keeps every dot-leader line, drops the ``SOMMAIRE``
    title and decimal sub-entries, and merges TOC lines that the PDF text layer
    wrapped across two physical lines (e.g. ``2 - Les variantes issues de 9...``
    followed by ``(23-28) ……… 80``).
    """
    lines = _toc_text().splitlines()

    chapters: list[tuple[str, int]] = []
    pending = ""  # accumulates a wrapped label awaiting its dot-leader/page
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        m = _TOC_LINE_RE.match(line)
        if not m:
            # A label fragment whose page number wrapped onto the next line.
            # Keep it (unless it is the SOMMAIRE banner or a stray page number).
            stripped = line.strip()
            if stripped.upper() == "SOMMAIRE" or stripped.isdigit():
                continue
            pending = (pending + " " + stripped).strip() if pending else stripped
            continue

        label = _norm((pending + " " + m.group(1)).strip() if pending else m.group(1))
        pending = ""
        page = int(m.group(2))

        if label.upper() == "SOMMAIRE":
            continue
        if _DECIMAL_RE.match(label):
            continue  # sub-chapter: folds into its parent
        chapters.append((label, page))

    return chapters


def _collapse_same_page(chapters: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """One representative chapter per start page, preserving book order.

    The book often starts several short chapters on one physical page. Since
    the per-page mapping can carry a single heading, keep the most specific
    chapter the book opens on that page: a numbered chapter / annotated game
    outranks a bare major-section banner, and the first listed wins among
    equals.
    """
    by_page: dict[int, str] = {}
    order: list[int] = []
    for label, page in chapters:
        if page not in by_page:
            by_page[page] = label
            order.append(page)
            continue
        # Collision: prefer a specific chapter over a generic banner; among
        # same-rank entries keep the one already chosen (the first listed).
        kept = by_page[page]
        if not _SPECIFIC_RE.match(kept) and _SPECIFIC_RE.match(label):
            by_page[page] = label
    return [(by_page[p], p) for p in order]


def build() -> dict[str, dict[str, str]]:
    chapters = _collapse_same_page(parse_toc())
    if not chapters:
        raise SystemExit("no chapters parsed from the table of contents")

    out: dict[str, dict[str, str]] = {}
    for idx, (heading, start) in enumerate(chapters):
        end = chapters[idx + 1][1] if idx + 1 < len(chapters) else _N_PAGES + 1
        for page in range(start, end):
            if 1 <= page <= _N_PAGES:
                out[str(page)] = {"heading": heading, "title": ""}
    return out


def main() -> None:
    if not _PDF.is_file():
        raise SystemExit(f"source PDF not found: {_PDF}")

    sections = build()
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(sections, indent=2, ensure_ascii=False))

    chapters = _collapse_same_page(parse_toc())
    print(f"wrote {len(sections)} page entries to {_OUT}")
    print(f"{len(chapters)} chapters in book order:")
    for heading, page in chapters:
        print(f"  p{page:>3}  {heading}")


if __name__ == "__main__":
    main()
