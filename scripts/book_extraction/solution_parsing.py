"""
Solution text parsing for exercise pages.

Solution pages typically look like:

  SOLUTIONS :
  D1 – <optional description>
  Solution : 34-29 (23x34) 39x30.
  D2 – Solution : 32-27 ...
  ...

Key challenges encountered (and solved):
  1. D1 has no preceding newline when it comes right after SOLUTIONS header.
     Fix: prepend \\n before splitting so the regex always matches.
  2. Bracketed comments [plus fort que 34-30] contain spurious moves.
     Fix: re.sub to remove bracketed spans with DOTALL flag.
  3. Analysis text after the first solution line contains extra moves.
     Fix: parse only up to the first blank line after "Solution :".
  4. Multi-step position notation (16-22-26, 37-38-42-47) is not a valid move.
     Fix: reject moves with more than one '-' separator.
  5. Attribution lines with dates ("27-12-1975") contribute spurious moves.
     Fix: strip any line that contains a 4-digit year before parsing.
  6. Context annotations ("5-10 ?!") on their own line leak into solution.
     Fix: strip standalone lines that are just a move + ?/!/? annotation.
  7. Numbered game notation ("38.32-27") must be normalised to "32-27".
     Fix: strip the move-number prefix before extraction.
  8. "jouant :" is used as a solution marker in some French books.
     Fix: extend the Solution-marker search to include "jouant :".
"""
from __future__ import annotations
import re
from typing import Dict, List, Optional


def parse_solution_page(sol_text: str, split_pattern: str = r'\nD(\d+)\s*[–\-]\s*') -> Dict[int, List[str]]:
    """
    Parse a full SOLUTIONS page into a {diagram_number: [moves]} dict.

    The page may start with "SOLUTIONS :" (stripped before splitting).
    """
    text = re.sub(r'^SOLUTIONS\s*:?\s*\n?', '', sol_text, flags=re.M)
    # Prepend newline so D1 at the very start of the text is also matched
    text = '\n' + text
    entries = re.split(split_pattern, text)
    result: Dict[int, List[str]] = {}
    i = 1
    while i < len(entries) - 1:
        d_num = int(entries[i])
        body = entries[i + 1] if i + 1 < len(entries) else ''
        result[d_num] = extract_moves(body)
        i += 2
    return result


def extract_moves(sol_text: str, max_moves: int = 10) -> List[str]:
    """
    Extract the main solution line from a solution block.

    Looks for a "Solution :" / "jouant :" marker and grabs the text up to
    the first blank line.  Falls back to the first paragraph that contains
    two or more moves if no marker is found.
    """
    # Remove bracketed comments (may span newlines)
    clean = re.sub(r'\[[\s\S]*?\]', '', sol_text)
    # Strip attribution lines that contain a 4-digit year, e.g.
    # "Agafonow - Baba Sy (Suiker GMA, 27-12-1975)" → would contribute "27-12"
    clean = re.sub(r'^[^\n]*\b\d{4}\b[^\n]*$', '', clean, flags=re.M)
    # Strip standalone context/annotation lines: a single move followed by ?/!/
    # These appear before the real solution to indicate a questionable black move.
    # E.g. "5-10 ?!" or "5-10 ?" on its own line.
    clean = re.sub(r'^\s*\d{1,2}[-x]\d{1,2}\s*[?!]+\s*$', '', clean, flags=re.M)
    # Normalise numbered game notation: "38.32-27" → "32-27"
    clean = re.sub(r'\b\d{1,2}\.(\d{1,2}[-x])', r'\1', clean)
    # Remove parenthesised content (opponent's replies) — expand into the text
    # so move regex can pick them up as part of the variation.
    clean = re.sub(r'\(([^)]*)\)', r' \1 ', clean)

    # Find "Solution :" / "jouant :" marker and capture up to first blank line.
    # "Solution 1:", "Solution :", "Solution:", "jouant :" all accepted.
    m = re.search(
        r'(?:[Ss]olution\s*\d*\s*:?|[Jj]ouant\s*:)\s*(.+?)(?:\n\n|\Z)',
        clean, re.S,
    )
    if m:
        # Limit to max 3 lines (stops multi-paragraph capture)
        raw = '\n'.join(m.group(1).splitlines()[:3])
        raw = raw.replace('\n', ' ')
        return _parse_moves(raw, max_moves)

    # No explicit solution marker — scan paragraphs for the first one that
    # contains 2+ moves (solution sequences have multiple moves; isolated
    # context lines like "10-14" or "12x21" have only one).
    paragraphs = [p.replace('\n', ' ') for p in re.split(r'\n\n+', clean) if p.strip()]
    for para in paragraphs:
        moves = _parse_moves(para, max_moves)
        if len(moves) >= 2:
            return moves
    # Final fallback: return any paragraph that has at least one move
    for para in paragraphs:
        moves = _parse_moves(para, max_moves)
        if moves:
            return moves
    return []


def _parse_moves(text: str, max_moves: int = 10) -> List[str]:
    """
    Extract valid international draughts moves from raw text.

    Valid forms:
      A-B      simple move (one dash, two different squares)
      AxB      capture (one x, two different squares)
      AxBxC…  multi-jump capture (multiple x, all squares valid)

    Rejected:
      A-B-C    position sequence notation (not a move)
      AxBxB    repeated square
    """
    tokens = re.findall(r'\b(\d{1,2}(?:[-x]\d{1,2})+)\b', text)
    valid: List[str] = []
    for tok in tokens:
        if _is_valid_move(tok):
            valid.append(tok)
        if len(valid) >= max_moves:
            break
    return valid


def _is_valid_move(mv: str) -> bool:
    # Reject mixed separators like "5-10x20"
    has_dash = '-' in mv
    has_x = 'x' in mv

    if has_dash and has_x:
        return False   # mixed separators are not standard

    if has_dash:
        parts = mv.split('-')
        if len(parts) != 2:
            return False  # A-B-C is position notation, not a move
        try:
            a, b = int(parts[0]), int(parts[1])
            return 1 <= a <= 50 and 1 <= b <= 50 and a != b
        except ValueError:
            return False

    if has_x:
        parts = mv.split('x')
        try:
            nums = [int(p) for p in parts if p]
            return (
                all(1 <= n <= 50 for n in nums)
                and len(nums) >= 2
                and len(nums) == len(set(nums))   # no repeated square
            )
        except ValueError:
            return False

    return False


def get_turn_from_page(page_text: str, d_num: int) -> str:
    """
    Infer whose turn it is from text like 'D3 : trait aux blancs'.
    Defaults to 'W' (white to move).
    """
    m = re.search(rf'D{d_num}\s*:\s*trait\s+aux\s+(blancs|noirs)', page_text, re.I)
    if m:
        return 'W' if 'blancs' in m.group(1).lower() else 'B'
    return 'W'
