"""Parse the manuel Débutant prose (`docs/manuels/debutant/manuel_debutant.md`)
into per-chapter lesson dicts consumable by the legacy /api/lessons route.

Output shape matches what the frontend `LessonPanel` expects :

    {
      "<chapter>": {
        "title": str,
        "text": str,       # full prose of the chapter (markdown kept as-is)
        "category": str,   # for grouping in the UI ; we reuse the chapter slug
        "diagrams": []     # no embedded FENs for now — the puzzles surface via
                           # the exercise list, not the lesson reader
      },
      ...
    }

Only chapters that match `## Chapitre N — Title` are exposed. Préface,
Conclusion and Annexes are dropped (they don't map to puzzles and
would inflate the chapter selector unnecessarily).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # backend/manuels/ → backend → repo
_MANUEL_DEBUTANT_MD = _REPO_ROOT / "docs" / "manuels" / "debutant" / "manuel_debutant.md"

_CHAPTER_HEADER = re.compile(r"^## Chapitre (\d+)\s*[—–-]\s*(.+)$", re.MULTILINE)


@lru_cache(maxsize=1)
def load_debutant_chapters() -> Dict[str, Dict[str, Any]]:
    if not _MANUEL_DEBUTANT_MD.exists():
        return {}
    text = _MANUEL_DEBUTANT_MD.read_text(encoding="utf-8")
    chapters: Dict[str, Dict[str, Any]] = {}
    matches = list(_CHAPTER_HEADER.finditer(text))
    for i, m in enumerate(matches):
        chapter_num = m.group(1)
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        # Trim trailing "## ..." sections after the last chapter (Conclusion, Annexes)
        body = text[start:end]
        next_top = re.search(r"^## (?!Chapitre )", body, re.MULTILINE)
        if next_top:
            body = body[: next_top.start()]
        chapters[chapter_num] = {
            "title": f"Chapitre {chapter_num} — {title}",
            "text": body.strip(),
            "category": f"debutant_ch{int(chapter_num):02d}",
            "diagrams": [],
        }
    return chapters
