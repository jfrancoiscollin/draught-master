"""
Post-extraction text correction for lesson content.

Two correction layers applied in order:

  1. Generic PDF extraction artifacts — `clean_extracted_text()` handles patterns
     that appear in any pdfplumber-extracted text regardless of book:
       - Stray ordinal 'e' on its own line (PDF superscript extraction artifact),
         e.g. "\\n1998\\ne\\n30 temps" → "\\n1998\\n30e temps"
       - Broken URL colon-slash: "http ://" → "http://"

  2. Book-specific content patches — `apply_book_corrections()` applies an
     explicit list of (old, new) replacements per chapter ID, preserving
     corrections that cannot be inferred from patterns alone (grammar fixes,
     typos, incomplete sentences).

Entry point for the extraction workflow: `post_process_lessons()`.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

# (old, new, human-readable reason)
Patch = Tuple[str, str, str]
CorrectionsMap = Dict[str, List[Patch]]


# ── Generic PDF-artifact cleanup ──────────────────────────────────────────────

def clean_extracted_text(text: str) -> str:
    """
    Remove common PDF extraction artifacts from a lesson text block.

    Handles two recurring patterns produced by pdfplumber when processing
    books with superscript ordinal suffixes or URLs:

    1. Superscript 'e' extracted on its own line before an ordinal phrase.
       Example: "Riga 1998\\ne\\n30 temps" → "Riga 1998\\n30e temps"
       Example: "\\ne\\n\\nOn voit alors dans la position du 3 diagramme"
                → "\\nOn voit alors dans la position du 3e diagramme"

    2. URL with space before "://": "http ://" → "http://"
    """
    # Superscript ordinal 'e' extracted on its own line immediately before a number.
    # pdfplumber renders "30e temps" as three tokens: "30", superscript-"e", "temps".
    # The superscript lands on a separate line, producing "...\ne\n30 temps".
    # Fix: capture the full number after \ne\n and attach 'e' as ordinal suffix.
    text = re.sub(r'\ne\n(\d+)', r'\n\1e', text)

    # Pattern 2: broken URL protocol separator
    text = text.replace('http ://', 'http://')

    return text


# ── Book-specific corrections ─────────────────────────────────────────────────

# Corrections identified during the Sens du Jeu extraction review.
# Keys are string chapter IDs (matching the JSON keys / BookConfig chapter_ids as str).
# Each value is a list of (old_text, new_text, reason) tuples.
SENS_DU_JEU_CORRECTIONS: CorrectionsMap = {
    '101': [
        (
            'sans lequel l’occupation territoriale joue un rôle majeur',
            'dans lequel l’occupation territoriale joue un rôle majeur',
            'Grammar: "sans lequel" contradicts meaning; territory IS a key factor',
        ),
    ],
    '102': [
        (
            'au jeu de de dames',
            'au jeu de dames',
            'Duplicate word: "de de" → "de"',
        ),
        (
            'micro faiblesses',
            'micro-faiblesses',
            'Compound noun requires hyphen',
        ),
        (
            'Si les trait est aux noirs',
            'Si le trait est aux noirs',
            'Gender agreement: "les trait" → "le trait"',
        ),
    ],
    '107': [
        (
            'Jeoeren KOS',
            'Joeren KOS',
            'Name typo: Jeoeren → Joeren',
        ),
    ],
    '108': [
        (
            'tirent avantagent q’une aile',
            'tirent avantage d’une aile',
            '"avantagent q\'" is wrong form; correct: "avantage d\'"',
        ),
    ],
    '110': [
        (
            'On Remarque au passage',
            'on remarque au passage',
            'Incorrect capitalisation mid-sentence',
        ),
        (
            'qui rend stérilise la formation',
            'qui stérilise la formation',
            'Spurious "rend" creates double verb',
        ),
        (
            'découvrirons plus .\n',
            'découvrirons plus tard.\n',
            'Incomplete phrase: "plus" → "plus tard"',
        ),
    ],
    '111': [
        (
            'temps de reserve',
            'temps de réserve',
            'Missing accent: reserve → réserve',
        ),
    ],
    '115': [
        (
            'les blancs qu’une seule alternative',
            'les blancs n’ont qu’une seule alternative',
            'Missing verb: "n’ont" omitted from "n’ont qu’une"',
        ),
    ],
    '120': [
        (
            'les blancs on tune jolie manière',
            'les blancs ont une jolie manière',
            'OCR split: "on tune" → "ont une"',
        ),
    ],
}


# ── Core functions ────────────────────────────────────────────────────────────

def apply_book_corrections(
    lessons: Dict[str, Dict[str, Any]],
    corrections: CorrectionsMap,
) -> tuple[Dict[str, Dict[str, Any]], List[str]]:
    """
    Apply book-specific text patches to a lessons dict.

    Returns (patched_lessons, list_of_applied_corrections).
    Does NOT mutate the input — returns a shallow copy with modified text fields.
    Warns (but does not raise) when a patch's old_text is not found.
    """
    import warnings
    patched = {k: dict(v) for k, v in lessons.items()}
    applied: List[str] = []

    for ch_id, patches in corrections.items():
        if ch_id not in patched:
            warnings.warn(f'text_correction: chapter {ch_id!r} not in lessons dict', stacklevel=2)
            continue
        text = patched[ch_id].get('text', '')
        for old, new, reason in patches:
            if old in text:
                text = text.replace(old, new)
                applied.append(f'[ch{ch_id}] {reason}')
            else:
                warnings.warn(
                    f'text_correction: ch{ch_id} patch not found: {old[:60]!r}',
                    stacklevel=2,
                )
        patched[ch_id]['text'] = text

    return patched, applied


def post_process_lessons(
    lessons: Dict[str, Dict[str, Any]],
    corrections: CorrectionsMap | None = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Full post-processing pipeline for extracted lesson text.

    1. Run generic artifact cleanup on every chapter's text.
    2. Apply book-specific corrections from `corrections` (if provided).

    Returns the corrected lessons dict.  Does NOT write to disk.
    """
    # Step 1: generic cleanup
    result = {}
    for ch_id, lesson in lessons.items():
        entry = dict(lesson)
        entry['text'] = clean_extracted_text(entry.get('text', ''))
        result[ch_id] = entry

    # Step 2: book-specific patches
    if corrections:
        result, _ = apply_book_corrections(result, corrections)

    return result
