"""
Board detection algorithms.

Two strategies are supported:

  border_lines  (sens_du_jeu style)
    Gray/white boards have an invisible interior but a thick black border.
    We scan for horizontal pixel runs darker than 50 (the border lines),
    group them by x-range, then pair adjacent runs at the expected distance.

  dark_squares  (combinaisons style)
    Classic dark/light boards have a checkerboard fill.
    We look for columns of squares with alternating dark/light fill and
    use the grid to infer board boundaries.
"""
from __future__ import annotations
from typing import List, Tuple

import numpy as np

Board = Tuple[int, int, int, int]   # (x1, y1, x2, y2) pixel coords


# ── border_lines strategy ────────────────────────────────────────────────────

def find_boards_border_lines(
    gray: np.ndarray,
    min_run: int = 400,
    expected_px: int = 505,
    dark_threshold: int = 50,
    size_tolerance: float = 0.10,
) -> List[Board]:
    """
    Detect boards by finding horizontal black border lines.

    Works for boards where the squares are gray/white (no dark fill) but
    the board perimeter is a solid black line of at least `min_run` pixels wide.
    """
    h, w = gray.shape
    dark = (gray < dark_threshold).astype(np.uint8)

    # Collect all horizontal dark runs ≥ min_run
    h_lines: List[Tuple[int, int, int]] = []   # (y, x_start, x_end)
    for y in range(h):
        row = dark[y, :]
        t = np.diff(np.concatenate([[0], row, [0]]))
        starts = np.where(t == 1)[0]
        ends = np.where(t == -1)[0]
        for s, e in zip(starts, ends):
            if e - s >= min_run:
                h_lines.append((y, int(s), int(e)))

    # Group by coarse x-range (same board = same horizontal span)
    x_ranges: dict = {}
    for y, xs, xe in h_lines:
        key = (xs // 30 * 30, xe // 30 * 30)
        x_ranges.setdefault(key, []).append((y, xs, xe))

    boards: List[Board] = []
    for key, items in x_ranges.items():
        ys = sorted(set(y for y, _, _ in items))
        # Cluster consecutive y values that belong to the same border line
        clusters: List[List[int]] = []
        cur: List[int] = [ys[0]]
        for y in ys[1:]:
            if y - cur[-1] <= 12:
                cur.append(y)
            else:
                clusters.append(cur)
                cur = [y]
        clusters.append(cur)

        # Each consecutive cluster pair is a candidate board
        for i in range(len(clusters) - 1):
            y_top = int(np.mean(clusters[i]))
            y_bot = int(np.mean(clusters[i + 1]))
            size = y_bot - y_top
            lo = expected_px * (1 - size_tolerance)
            hi = expected_px * (1 + size_tolerance)
            if lo < size < hi:
                x_left = int(min(xs for _, xs, _ in items))
                x_right = int(max(xe for _, _, xe in items))
                boards.append((x_left, y_top, x_right, y_bot))

    return _deduplicate(boards)


# ── dark_squares strategy ────────────────────────────────────────────────────

def find_boards_dark_squares(
    gray: np.ndarray,
    dark_threshold: int = 80,
    min_board_px: int = 350,
    max_board_px: int = 700,
) -> List[Board]:
    """
    Detect boards by locating columns of alternating dark/light squares.

    Works for classic dark/light checkerboard boards.
    Uses a column-projection approach: dark squares create a periodic signal
    in the vertical sum that reveals the board boundaries.
    """
    dark = (gray < dark_threshold).astype(np.float32)
    col_sum = dark.sum(axis=0)       # darkness per column
    row_sum = dark.sum(axis=1)       # darkness per row

    # Simple approach: find vertical stripes with high darkness fraction
    h, w = gray.shape
    min_dark_frac = 0.08   # at least 8 % of a column must be dark to count

    col_dark = (col_sum / h) > min_dark_frac
    row_dark = (row_sum / w) > min_dark_frac

    x_segments = _find_segments(col_dark)
    y_segments = _find_segments(row_dark)

    boards: List[Board] = []
    for x1, x2 in x_segments:
        for y1, y2 in y_segments:
            size = max(x2 - x1, y2 - y1)
            if min_board_px < size < max_board_px:
                boards.append((x1, y1, x2, y2))

    return _deduplicate(boards)


# ── shared helpers ────────────────────────────────────────────────────────────

def _find_segments(mask: np.ndarray, gap: int = 5) -> List[Tuple[int, int]]:
    """Find contiguous True segments in a 1-D boolean mask."""
    segs = []
    in_seg = False
    start = 0
    n = len(mask)
    for i in range(n):
        if mask[i] and not in_seg:
            start = i
            in_seg = True
        elif not mask[i] and in_seg:
            segs.append((start, i))
            in_seg = False
    if in_seg:
        segs.append((start, n))

    # Merge close segments
    merged = []
    for seg in segs:
        if merged and seg[0] - merged[-1][1] <= gap:
            merged[-1] = (merged[-1][0], seg[1])
        else:
            merged.append(list(seg))
    return [tuple(s) for s in merged]  # type: ignore


def _deduplicate(boards: List[Board], min_dist: int = 80) -> List[Board]:
    """Remove near-duplicate board detections."""
    boards = sorted(boards, key=lambda b: (b[1], b[0]))
    unique: List[Board] = []
    for b in boards:
        if not any(abs(b[0] - u[0]) < min_dist and abs(b[1] - u[1]) < min_dist for u in unique):
            unique.append(b)
    return unique


def find_boards(
    gray: np.ndarray,
    style: str,
    min_border_run: int = 400,
    expected_board_px: int = 505,
) -> List[Board]:
    """Dispatch to the correct detection strategy."""
    if style == 'border_lines':
        return find_boards_border_lines(gray, min_run=min_border_run, expected_px=expected_board_px)
    elif style == 'dark_squares':
        return find_boards_dark_squares(gray)
    else:
        raise ValueError(f'Unknown board style: {style!r}. Use "border_lines" or "dark_squares".')
