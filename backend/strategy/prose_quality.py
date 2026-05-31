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
