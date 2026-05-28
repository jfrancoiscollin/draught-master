"""Rules-based FEN detector for printed draughts diagrams.

Goal: pre-fill the manual annotation workflow.  Given a tight crop of a
printed diagram (the JPEGs in ``pages/<source>/diagrams/``), guess the
position as a FEN string of the form ``W:W3,5,...:B12,14,...`` (kings
prefixed with ``K``).  The operator then validates with one click in
the in-app editor instead of placing every piece from scratch.

Approach (no deep learning yet — ~30 hand-annotated boards isn't enough
to outperform the print's regularities).  For Sijbrands' stylized
diagrams every square is roughly the same size and pieces are flat
circles with high contrast vs. the blue background, so a per-square
brightness + inner-vs-outer check covers almost everything:

    1. Slice the crop into a 10×10 grid (cells = W/10, H/10).
    2. For each *playable* (dark) square, grab a central patch.
    3. Classify by patch mean intensity:
       - very bright → white piece
       - very dark   → black piece
       - else        → empty
    4. King flag: inside the piece, compare an inner sub-patch to the
       surrounding ring.  Kings carry a contrasting central marker
       (dark dot in a white piece; bright dot in a black piece).

The board's playable-square parity is "dark square at (row=0, col=1)"
— i.e. ``(row + col) % 2 == 1``.  Square numbering follows the
international draughts convention: row 0 holds squares 1–5, row 1 holds
6–10, …, row 9 holds 46–50.

This is calibrated on Sijbrands.  Other sources may need their own
thresholds (Springer's print is darker; Roozenburg uses thinner
outlines).  Kept source-agnostic in the signature so the caller can
override the thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class DetectorConfig:
    # All thresholds are on 0–255 grayscale means.  Defaults are tuned
    # for Sijbrands' light-blue diagrams; other sources can pass a
    # different config without code changes.
    white_piece_min: float = 190.0  # patch brighter than this → white piece
    black_piece_max: float = 80.0   # patch darker than this → black piece
    # King = significant inner/outer contrast inside the piece.  Tuned
    # conservatively — false positives (calling a piece a king) are
    # worse than false negatives (the operator just clicks "promote").
    king_contrast_min: float = 55.0
    # Cell-relative fractions.  The crop usually IS the board, but a
    # tiny inset on the inner patch makes detection robust to slight
    # rendering shifts between pages.
    cell_inset: float = 0.20         # piece sample = central 60% of the cell
    king_inner_frac: float = 0.25    # inner sub-patch = central 25% of the piece
    # Board-bound detection.  We classify a row/column as "in the board"
    # iff at least ``board_coverage_min`` of its pixels are darker than
    # ``board_pixel_max``.  This separates the board (90%+ blue/piece
    # pixels) from the caption ("DIAGRAMME N" — 5–15% dark text on
    # otherwise white background) and the page padding (~0% non-white).
    # Row mean alone won't work: a row of mostly-white-pieces has the
    # same mean as a caption row.
    board_pixel_max: float = 230.0
    board_coverage_min: float = 0.5


def _longest_run(mask: np.ndarray) -> tuple[int, int]:
    """``(start, end)`` of the longest contiguous run of True in ``mask``.

    Used to isolate the board from captions and dotted dividers: those
    print elements show up as 1–3 row spikes outside the threshold,
    while the board is one solid block of board-coloured rows.  Picking
    the longest run ignores the spikes for free.

    Returns ``(0, 0)`` if no True values.
    """
    if not mask.any():
        return 0, 0
    best_start = best_end = 0
    cur_start = -1
    for i, v in enumerate(mask):
        if v and cur_start < 0:
            cur_start = i
        elif not v and cur_start >= 0:
            if i - cur_start > best_end - best_start:
                best_start, best_end = cur_start, i
            cur_start = -1
    if cur_start >= 0 and len(mask) - cur_start > best_end - best_start:
        best_start, best_end = cur_start, len(mask)
    return best_start, best_end


def _detect_board_bounds(
    arr: np.ndarray,
    pixel_max: float,
    coverage_min: float,
) -> tuple[int, int, int, int]:
    """Return ``(y0, y1, x0, x1)`` of the board inside the crop.

    The crop pipeline leaves white page padding around the board (left
    and bottom are typical) and sometimes a centered "DIAGRAMME N"
    caption above the board, sometimes a dotted section divider below.

    Approach: a row is "board" iff at least ``coverage_min`` of its
    pixels are darker than ``pixel_max``.  Board rows are 90%+ board-
    coloured; caption rows are <20% (mostly white background); padding
    rows are 0%.  Same for columns.  We then take the longest
    contiguous block of "board" rows/columns to isolate the board from
    the caption / divider on the other side of the white gap.

    Final pass squarifies anchored to the bbox's bottom-right — when
    the row and column blocks disagree, captions/dividers sit above or
    below the board, never beside, so trimming the top is the safer
    move.
    """
    h, w = arr.shape
    inked = arr < pixel_max
    row_cov = inked.mean(axis=1)
    col_cov = inked.mean(axis=0)
    y0, y1 = _longest_run(row_cov >= coverage_min)
    x0, x1 = _longest_run(col_cov >= coverage_min)
    if y1 == y0 or x1 == x0:
        return 0, h, 0, w  # all-white crop — defensive fallback
    bbox_h = y1 - y0
    bbox_w = x1 - x0
    if bbox_h > bbox_w:
        y0 = y1 - bbox_w
    elif bbox_w > bbox_h:
        x0 = x1 - bbox_h
    return y0, y1, x0, x1


def _square_to_rc(square: int) -> tuple[int, int]:
    """International numbering 1–50 → (row, col) on the 10×10 grid."""
    row = (square - 1) // 5
    num_in_row = (square - 1) % 5
    # Row parity flips which column the playable squares sit on.
    # Even rows: cols 1, 3, 5, 7, 9.  Odd rows: cols 0, 2, 4, 6, 8.
    col = num_in_row * 2 + (1 if row % 2 == 0 else 0)
    return row, col


def _rc_to_square(row: int, col: int) -> int:
    """Inverse of ``_square_to_rc``.  Caller guarantees playable parity."""
    return row * 5 + col // 2 + 1


def _patch_mean(arr: np.ndarray, y0: int, y1: int, x0: int, x1: int) -> float:
    """Mean grayscale intensity in a region.  ``arr`` is HxW grayscale."""
    return float(arr[y0:y1, x0:x1].mean())


def detect_fen(image_path: Path, *, config: DetectorConfig | None = None) -> str:
    """Return ``W:W...:B...`` FEN string predicted from the crop.

    Always assumes white to move (``W:`` prefix) — printed diagrams
    don't encode the side to move and the manual annotator defaults
    to white anyway.
    """
    cfg = config or DetectorConfig()
    img = Image.open(image_path).convert("L")  # grayscale; color isn't needed
    full = np.asarray(img, dtype=np.float32)
    y0, y1, x0, x1 = _detect_board_bounds(
        full, cfg.board_pixel_max, cfg.board_coverage_min
    )
    arr = full[y0:y1, x0:x1]
    h, w = arr.shape
    cell_h = h / 10.0
    cell_w = w / 10.0

    whites: list[str] = []
    blacks: list[str] = []

    for row in range(10):
        for col in range(10):
            if (row + col) % 2 == 0:
                continue  # light square — never holds a piece
            y_mid = (row + 0.5) * cell_h
            x_mid = (col + 0.5) * cell_w
            # Piece patch — large enough to average out compression noise
            # but small enough that it sits inside the circle.
            inset = cfg.cell_inset
            y0 = int(y_mid - cell_h * (0.5 - inset))
            y1 = int(y_mid + cell_h * (0.5 - inset))
            x0 = int(x_mid - cell_w * (0.5 - inset))
            x1 = int(x_mid + cell_w * (0.5 - inset))
            piece_mean = _patch_mean(arr, y0, y1, x0, x1)

            square = _rc_to_square(row, col)

            if piece_mean >= cfg.white_piece_min:
                # Likely white piece.  Probe for king marker by comparing
                # the inner patch (king dot) against the surrounding ring.
                king = _is_king(arr, y_mid, x_mid, cell_h, cell_w, cfg, "white")
                whites.append(f"K{square}" if king else str(square))
            elif piece_mean <= cfg.black_piece_max:
                king = _is_king(arr, y_mid, x_mid, cell_h, cell_w, cfg, "black")
                blacks.append(f"K{square}" if king else str(square))
            # else: empty — skip

    return f"W:W{','.join(whites)}:B{','.join(blacks)}"


def _is_king(
    arr: np.ndarray,
    y_mid: float,
    x_mid: float,
    cell_h: float,
    cell_w: float,
    cfg: DetectorConfig,
    color: str,
) -> bool:
    """Detect the central marker that distinguishes a king from a man.

    Sijbrands prints a small dark dot at the center of white kings and
    a small white dot at the center of black kings.  We compare the
    mean intensity of an inner sub-patch to the surrounding ring and
    require the contrast to exceed ``king_contrast_min``.
    """
    inset = cfg.cell_inset
    piece_half_h = cell_h * (0.5 - inset)
    piece_half_w = cell_w * (0.5 - inset)
    inner_half_h = piece_half_h * cfg.king_inner_frac
    inner_half_w = piece_half_w * cfg.king_inner_frac

    inner = _patch_mean(
        arr,
        int(y_mid - inner_half_h),
        int(y_mid + inner_half_h),
        int(x_mid - inner_half_w),
        int(x_mid + inner_half_w),
    )
    # Outer ring = full piece patch minus inner — approximated by sampling
    # the four corners of the piece patch (avoids re-masking).
    outer_samples = []
    for dy in (-1, 1):
        for dx in (-1, 1):
            cy = y_mid + dy * piece_half_h * 0.7
            cx = x_mid + dx * piece_half_w * 0.7
            outer_samples.append(
                _patch_mean(
                    arr,
                    int(cy - inner_half_h),
                    int(cy + inner_half_h),
                    int(cx - inner_half_w),
                    int(cx + inner_half_w),
                )
            )
    outer = float(np.mean(outer_samples))

    # White king = bright outer, dark inner.  Black king = dark outer, bright inner.
    contrast = outer - inner if color == "white" else inner - outer
    return contrast >= cfg.king_contrast_min
