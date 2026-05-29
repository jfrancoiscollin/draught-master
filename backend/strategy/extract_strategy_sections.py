"""Extract pedagogical section headings from each source's PDF and map
them to the diagrams they introduce.

For every page of a source PDF we look for ``Leçon N``, ``Thème N``,
``Partie N`` (and a couple of source-specific patterns) and pair each
``DIAGRAMME N`` reference with the most recent preceding heading.  The
result is a static lookup ``pages/<source>/diagram_sections.json``
keyed by ``(page, diagram_number)``::

    {
      "48-6": {
        "leçon": "Thème 4",
        "title": "Libérer le chemin"
      }
    }

The manual API serves this to the frontend so each passage card can be
titled by its pedagogical context (chapter / theme) instead of the
generic "Diagramme N · page X".

Run from the repo root::

    python -m backend.strategy.extract_strategy_sections sijbrands
    python -m backend.strategy.extract_strategy_sections springer
    python -m backend.strategy.extract_strategy_sections roozenburg
    python -m backend.strategy.extract_strategy_sections keller
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_PAGES_DIR = Path(__file__).parent / "pages"
# dilf lives as a sibling clone, not nested under draught-master.
_PDF_DIR = Path(__file__).resolve().parents[3] / "dilf" / "docs" / "corpus"

# Patterns that mark a section heading in our four corpus PDFs.
# Two regimes:
#  1. Sijbrands-style: heading marker on its own line, title on the
#     next non-empty line ("Thème 4" \n "Libérer le chemin").
#  2. Springer/Keller-style: marker + title on the same line
#     ("Thème 1 Le classique d'attaque" or "3 - LE JEU DES NOIRS").
# We capture the marker; if same-line text follows, it's used as the
# title directly.
_HEADING_RE = re.compile(
    r"^(Leçon\s+\d+|Thème\s+\d+|Partie\s+n°?\d+|Chapitre\s+\d+|\d+\s*[-–]\s*[A-ZÉÈÊ][^\n]+|[A-ZÉÈÊ]{4,}[^\n]*)\s*(.*)$",
    re.MULTILINE,
)

# Detects an in-page diagram reference.  Sijbrands/Springer use the
# all-caps form "DIAGRAMME N".  We accept the lowercase variant too
# (Roozenburg captions diagrams with sentence case).
_DIAGRAM_REF_RE = re.compile(r"\bDIAGRAMME\s+(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class SourceCfg:
    slug: str
    pdf: str


_SOURCES: dict[str, SourceCfg] = {
    "sijbrands":  SourceCfg("sijbrands",  "sijbrandscourse.pdf"),
    "springer":   SourceCfg("springer",   "springercourse.pdf"),
    "roozenburg": SourceCfg("roozenburg", "roozenburgcourse.pdf"),
    "keller":     SourceCfg("keller",     "le_systeme_keller.pdf"),
}


def _page_text(pdf: Path, page: int) -> str:
    """Return the text of a single page via ``pdftotext``."""
    out = subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), str(pdf), "-"],
        capture_output=True, text=True, check=False,
    )
    return out.stdout


def _extract_sections(pdf: Path, total_pages: int) -> dict[int, dict[str, str]]:
    """Walk every page; track the most recent heading + title line.
    Returns a per-page mapping: every page from the source PDF gets
    the section heading / title that was in scope at the *start* of
    the page (i.e. the running state from the previous pages, updated
    by any heading found on this page).

    Page-indexed rather than ``(page, diagram_number)`` — Keller's PDF
    references diagrams without explicit numbers ("le diagramme
    suivant", "le diagramme ci-dessus") so a number-based lookup
    misses every Keller passage.
    """
    current_heading = ""
    current_title = ""
    out: dict[int, dict[str, str]] = {}
    for page in range(1, total_pages + 1):
        text = _page_text(pdf, page)
        lines = text.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            m = _HEADING_RE.match(stripped)
            if not m:
                continue
            if stripped.startswith(("DIAGRAMME", "EXERCICE")):
                continue
            current_heading = m.group(1).strip()
            same_line_title = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else ""
            if same_line_title:
                current_title = same_line_title
            else:
                for j in range(i + 1, min(i + 6, len(lines))):
                    title_candidate = lines[j].strip()
                    if title_candidate:
                        current_title = title_candidate
                        break
        if current_heading:
            out[page] = {"heading": current_heading, "title": current_title}
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: extract_strategy_sections <source>")
        return 1
    source = argv[1].lower()
    cfg = _SOURCES.get(source)
    if cfg is None:
        print(f"unknown source {source!r}; expected one of {list(_SOURCES)}")
        return 1
    pdf = _PDF_DIR / cfg.pdf
    if not pdf.is_file():
        print(f"PDF not found: {pdf}")
        return 1
    # Get total page count.
    info = subprocess.run(
        ["pdfinfo", str(pdf)], capture_output=True, text=True, check=True,
    )
    pages = 1
    for line in info.stdout.splitlines():
        if line.startswith("Pages:"):
            pages = int(line.split(":", 1)[1].strip())
            break
    print(f"Scanning {cfg.pdf} ({pages} pages)…")
    sections = _extract_sections(pdf, pages)
    # Serialise with string keys so the JSON round-trips cleanly.
    payload = {str(p): v for p, v in sorted(sections.items())}
    out_path = _PAGES_DIR / cfg.slug / "diagram_sections.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(payload)} entries → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
