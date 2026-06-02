"""Tell apart readable prose from move-score dumps in the strategy corpus.

The scanned manuals (especially Goedemoed's "A Course in Draughts") are
exercise/game collections: many extracted paragraphs are pure move notation
and game citations with no explanatory text. Surfacing those as "lessons"
makes the manual unreadable. We gate the manual + reading recommender on
:func:`has_prose` so only passages that contain a real sentence appear.
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[A-Za-zÀ-ÿ]{2,}")


def longest_word_run(text: str) -> int:
    """Length of the longest run of consecutive word-tokens, where a token
    that starts with a digit (a move like ``35-30``, a move number ``12.``,
    a citation index ``7)``) breaks the run. A long run ⇒ a real sentence."""
    best = cur = 0
    for tok in text.split():
        if tok[:1].isdigit():
            cur = 0
        elif _WORD.search(tok):
            cur += 1
            if cur > best:
                best = cur
        # punctuation / bracket tokens (e.g. "<24>", "—") are neutral
    return best


def has_prose(text: str, min_run: int = 8) -> bool:
    """True when the passage carries at least one genuine sentence rather
    than being a move-score / game-citation dump."""
    return longest_word_run(text) >= min_run


def lead_excerpt(text: str, min_run: int = 4) -> str:
    """Return ``text`` trimmed to start at its first real sentence.

    The PDF chunks often open with a move sequence, a diagram header or a game
    citation before the explanation ("1.1) 35-30 … In order to prevent …").
    We drop that leading noise so a manual card *leads* with prose. The first
    run of ``min_run`` consecutive word-tokens marks the sentence start; if
    none is found the text is returned unchanged (the caller already filtered
    on :func:`has_prose`).
    """
    tokens = list(re.finditer(r"\S+", text))
    run = 0
    start: int | None = None
    for i, tok in enumerate(tokens):
        s = tok.group()
        if s[:1].isdigit():
            run = 0
            start = None
        elif _WORD.search(s):
            if run == 0:
                start = i
            run += 1
            if run >= min_run and start is not None:
                return text[tokens[start].start():].strip()
        # neutral tokens ("<24>", "—", "!") keep the current run going
    return text.strip()


def decolumnize(text: str) -> str:
    """Un-interleave a two-column page block.

    The scanned manuals are laid out in two columns; pdftotext reads each
    physical line left-to-right across the gutter, so the stored text reads
    "<left-col line>     <right-col line>" — every other sentence belongs to a
    different column ("…entre le · Dans le passé, Van Dijk…"). We detect a
    recurring whitespace gutter (a wide gap at a roughly stable column on most
    lines) and rejoin the whole left column first, then the whole right column.

    Returns ``text`` unchanged when no consistent two-column gutter is found
    (single-column blocks must pass through untouched). Splits each line at its
    own gutter so no character is dropped at the seam.
    """
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n")]
    # A gutter on a line = a run of ≥4 spaces with text on both sides.
    gutters: list[int] = []
    for ln in lines:
        m = re.search(r"\S(\s{4,})\S", ln)
        if m:
            gutters.append(m.start(1))
    # Need the gutter on a clear majority of non-empty lines to call it 2-col.
    non_empty = [ln for ln in lines if ln.strip()]
    if len(gutters) < max(3, (len(non_empty) + 1) // 2):
        return text

    gutters.sort()
    cut = gutters[len(gutters) // 2]  # median gutter column

    left: list[str] = []
    right: list[str] = []
    for ln in lines:
        if not ln.strip():
            continue
        # Find this line's own gutter nearest the median cut; fall back to cut.
        split_at = None
        for m in re.finditer(r"\s{3,}", ln):
            if m.start() >= cut - 12:
                split_at = m.start()
                break
        if split_at is None:
            # No wide gap near the cut: whole line is one column. Assign by
            # where its text sits relative to the cut.
            (left if len(ln) <= cut + 4 else right).append(ln.strip())
        else:
            left.append(ln[:split_at].strip())
            right.append(ln[split_at:].strip())

    merged = " ".join(x for x in left if x)
    rcol = " ".join(x for x in right if x)
    if rcol:
        merged = f"{merged} {rcol}".strip()
    return merged


def normalize_whitespace(text: str) -> str:
    """Flatten PDF line-wrap artefacts into clean flowing prose.

    Extracted text keeps the book's column layout: two-column interleaving
    (handled by :func:`decolumnize`), hard newlines mid-sentence and long runs
    of leading spaces (indentation). Rendered as-is in the browser that yields
    garbled or ragged lines. We de-column each paragraph, then collapse every
    run of whitespace to one space, keeping a real paragraph break where the
    source had a blank line.
    """
    paragraphs = re.split(r"\n[ \t]*\n", text.replace("\r\n", "\n"))
    cleaned = [re.sub(r"\s+", " ", decolumnize(p)).strip() for p in paragraphs]
    return "\n\n".join(p for p in cleaned if p)
