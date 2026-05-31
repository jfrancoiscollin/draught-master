"""Runtime accessor over ``position_library.json``.

The JSON is built offline by ``build_position_library.py``; this module
loads it once (``lru_cache``) and exposes typed, filtered views used by
the strategy API, the study-exercise generator and the thematic
knowledge base.

Keeping read access here means consumers never touch the file layout or
re-implement the "valid only" / "by theme" filters.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

_LIB_PATH = Path(__file__).parent / "position_library.json"


@lru_cache(maxsize=1)
def _payload() -> dict:
    if not _LIB_PATH.is_file():
        return {"positions": [], "stats": {}, "sources": []}
    return json.loads(_LIB_PATH.read_text())


def all_positions() -> list[dict]:
    """Every consolidated diagram position (valid and invalid)."""
    return list(_payload()["positions"])


def valid_positions(
    source: Optional[str] = None,
    *,
    kind: Optional[str] = None,
    with_capture: Optional[bool] = None,
) -> list[dict]:
    """Positions that passed engine sanity checks, optionally filtered.

    Args:
        source: restrict to one manual (e.g. ``"SIJBRANDS"``).
        kind: ``"human"`` or ``"auto"`` provenance.
        with_capture: keep only positions where a capture is available
            to the side to move (i.e. candidate tactical positions).
    """
    out: list[dict] = []
    for p in _payload()["positions"]:
        if not p.get("valid"):
            continue
        if source and p["source"] != source.upper():
            continue
        if kind and p["kind"] != kind:
            continue
        if with_capture is not None and bool(p.get("has_capture")) != with_capture:
            continue
        out.append(p)
    return out


def get_position(source: str, page: int, number: int) -> Optional[dict]:
    """Look up a single diagram by its source/page/number coordinates."""
    pid = f"{source.upper()}_p{page:04d}_d{number}"
    for p in _payload()["positions"]:
        if p["id"] == pid:
            return p
    return None


def themes(source: Optional[str] = None) -> dict[str, list[dict]]:
    """Group **valid** positions by their manual theme (chapter title).

    This is the thematic spine of the strategic knowledge base: each key
    is a human-authored lesson title ("Le débordement", "Bloquer des
    pions", …) mapped to the concrete positions illustrating it.
    """
    grouped: dict[str, list[dict]] = {}
    for p in valid_positions(source):
        theme = p.get("theme")
        if not theme:
            continue
        grouped.setdefault(theme, []).append(p)
    return grouped


def stats() -> dict:
    return _payload().get("stats", {})
