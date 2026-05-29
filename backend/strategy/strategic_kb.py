"""Thematic strategic knowledge base, derived from the position library.

The scanned manuals are organised into lessons (``diagram_sections.json``
gives each page a "Leçon N — <title>"). This module turns that into a
browsable knowledge base: every lesson *theme* maps to the concrete,
engine-validated diagram positions that illustrate it.

It's a pure view over ``position_library`` — no second artifact to keep
fresh. Consumers: the strategy API (``/kb-themes`` & ``/kb-theme``) and
the tip-enrichment script.
"""

from __future__ import annotations

from typing import Optional

from . import position_library as lib

# Fields exposed for an example position — enough for the frontend to
# render a Board and a "see in <manual>" deep link, nothing more.
_EXAMPLE_FIELDS = (
    "id",
    "source",
    "page",
    "number",
    "fen",
    "kind",
    "side_to_move",
    "has_capture",
)


def _slim(position: dict) -> dict:
    return {k: position.get(k) for k in _EXAMPLE_FIELDS}


def representative(positions: list[dict], limit: int = 6) -> list[dict]:
    """Pick a small, varied sample to illustrate a theme.

    Human-verified positions come first (highest trust), then auto ones,
    de-duplicated by FEN and spread across pages so the sample isn't all
    from one diagram cluster.
    """
    seen_fen: set[str] = set()
    ranked = sorted(
        positions,
        key=lambda p: (0 if p["kind"] == "human" else 1, p["page"], p["number"]),
    )
    out: list[dict] = []
    for p in ranked:
        if p["fen"] in seen_fen:
            continue
        seen_fen.add(p["fen"])
        out.append(_slim(p))
        if len(out) >= limit:
            break
    return out


def theme_index(source: Optional[str] = None) -> list[dict]:
    """Summary card per theme, richest themes first."""
    grouped = lib.themes(source)
    cards: list[dict] = []
    for theme, items in grouped.items():
        sources = sorted({p["source"] for p in items})
        headings = sorted(
            {p["section_heading"] for p in items if p.get("section_heading")}
        )
        cards.append(
            {
                "theme": theme,
                "sources": sources,
                "lessons": headings,
                "n_positions": len(items),
                "n_human": sum(1 for p in items if p["kind"] == "human"),
                "n_with_capture": sum(1 for p in items if p.get("has_capture")),
                "examples": representative(items, limit=3),
            }
        )
    cards.sort(key=lambda c: (-c["n_positions"], c["theme"]))
    return cards


def theme_detail(theme: str, source: Optional[str] = None, limit: int = 50) -> dict:
    """All positions filed under one theme (capped)."""
    items = [p for p in lib.valid_positions(source) if p.get("theme") == theme]
    items.sort(key=lambda p: (p["source"], p["page"], p["number"]))
    return {
        "theme": theme,
        "n_positions": len(items),
        "positions": [_slim(p) for p in items[:limit]],
    }
