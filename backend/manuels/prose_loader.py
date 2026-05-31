"""Parse the manuel Débutant prose (`docs/manuels/debutant/manuel_debutant.md`)
into per-chapter lesson dicts consumable by the legacy /api/lessons route.

Output shape matches what the frontend `LessonPanel` expects :

    {
      "<chapter>": {
        "title": str,
        "text": str,             # full prose of the chapter (markdown kept as-is)
        "category": str,         # for grouping in the UI ; we reuse the chapter slug
        "diagrams": [            # board positions referenced inline in the prose
          {"ref": "BEG_CH04_005",
           "fen": "W:W...:B...",
           "label": "BEG_CH04_005"},
          ...
        ]
      },
      ...
    }

Only chapters that match `## Chapitre N — Title` are exposed. Préface,
Conclusion and Annexes are dropped (they don't map to puzzles and
would inflate the chapter selector unnecessarily).

`diagrams` are extracted from `BEG_CHnn_mmm` occurrences inside the
chapter text (typically rendered as inline code in the markdown). Each
ref is deduplicated by first occurrence ; the matching fixture's FEN
is resolved via `manuels.fixtures_debutant`.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from pedagogy.game import state_to_fen

from . import fixtures_debutant as fx


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # backend/manuels/ → backend → repo
_MANUEL_DEBUTANT_MD = _REPO_ROOT / "docs" / "manuels" / "debutant" / "manuel_debutant.md"

_CHAPTER_HEADER = re.compile(r"^## Chapitre (\d+)\s*[—–-]\s*(.+)$", re.MULTILINE)
_FIXTURE_REF = re.compile(r"BEG_CH\d{2}_\d{3}")
# Metadata block placed under the chapter header — declares which dilf
# motifs and which structural weakness families the chapter covers, so
# the narrative chips (GameNarrativeSummary) can deep-link to the right
# lesson. Two distinct comment lines instead of YAML to keep parsing
# trivial and the markdown readable:
#
#     ## Chapitre 5 — L'envoi à dame
#     <!-- pedagogy-motifs: envoi_a_dame -->
#     <!-- pedagogy-weaknesses: holes, outposts -->
#
# Both lines are optional; missing → empty list.
_META_MOTIFS = re.compile(r"<!--\s*pedagogy-motifs:\s*([^>]*?)-->")
_META_WEAKNESSES = re.compile(r"<!--\s*pedagogy-weaknesses:\s*([^>]*?)-->")


def _parse_csv(raw: str) -> List[str]:
    return [tok.strip() for tok in raw.split(",") if tok.strip()]


def _metadata_for(chapter_text: str) -> Dict[str, List[str]]:
    m_motifs = _META_MOTIFS.search(chapter_text)
    m_weak = _META_WEAKNESSES.search(chapter_text)
    return {
        "motifs": _parse_csv(m_motifs.group(1)) if m_motifs else [],
        "weaknesses": _parse_csv(m_weak.group(1)) if m_weak else [],
    }


def _diagrams_for(chapter_text: str) -> List[Dict[str, str]]:
    diagrams: List[Dict[str, str]] = []
    seen: set[str] = set()
    for m in _FIXTURE_REF.finditer(chapter_text):
        ref = m.group(0)
        if ref in seen:
            continue
        seen.add(ref)
        pos = getattr(fx, ref, None)
        if pos is None:
            continue
        diagrams.append({
            "ref": ref,
            "fen": state_to_fen(pos.state),
            "label": ref,
        })
    return diagrams


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
        body = body.strip()
        meta = _metadata_for(body)
        chapters[chapter_num] = {
            "title": f"Chapitre {chapter_num} — {title}",
            "text": body,
            "category": f"debutant_ch{int(chapter_num):02d}",
            "diagrams": _diagrams_for(body),
            "motifs": meta["motifs"],
            "weaknesses": meta["weaknesses"],
        }
    return chapters


@lru_cache(maxsize=1)
def lessons_by_motif() -> Dict[str, List[str]]:
    """Inverted index motif slug → ordered chapter numbers covering it."""
    idx: Dict[str, List[str]] = {}
    for num, chap in load_debutant_chapters().items():
        for slug in chap.get("motifs", []):
            idx.setdefault(slug, []).append(num)
    return idx


@lru_cache(maxsize=1)
def lessons_by_weakness() -> Dict[str, List[str]]:
    """Inverted index weakness family → ordered chapter numbers covering it."""
    idx: Dict[str, List[str]] = {}
    for num, chap in load_debutant_chapters().items():
        for family in chap.get("weaknesses", []):
            idx.setdefault(family, []).append(num)
    return idx
