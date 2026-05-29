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
    # ``style`` switches the per-cell classifier between two regimes:
    # ``"blue"`` (Sijbrands/Springer) compares the central patch's mean
    # brightness to absolute thresholds, while ``"bw"`` (Roozenburg)
    # uses an inner-vs-ring contrast delta — B&W boards have white
    # pieces that match the empty-square colour in mean, so absolute
    # brightness alone can't separate them.
    style: str = "blue"
    white_piece_min: float = 190.0  # patch brighter than this → white piece
    black_piece_max: float = 80.0   # patch darker than this → black piece
    # B&W style only: inner < ring - bw_dark_delta and inner < bw_dark_max
    # → black piece (e.g. inner 110, ring 150 → diff -40 → black).
    # inner > ring + bw_light_delta and inner > bw_light_min → white
    # piece (e.g. inner 240, ring 190 → diff +50 → white).
    bw_dark_max: float = 150.0
    bw_dark_delta: float = 20.0
    # Tuned against 4 ground-truth Roozenburg crops (p.14 #1, #2; p.18 #1, #2).
    # Empty gray squares cluster at inner~190/ring~190, white pieces on gray
    # at inner 200-240/ring 175-210 — so the 200 inner threshold + small
    # delta cleanly separates them without false positives.
    bw_light_min: float = 200.0
    bw_light_delta: float = 5.0
    # King = significant inner/outer contrast inside the piece.  Tuned
    # conservatively — false positives (calling a piece a king) are
    # worse than false negatives (the operator just clicks "promote").
    king_contrast_min: float = 55.0
    # Cell-relative fractions.  The crop usually IS the board, but a
    # tiny inset on the inner patch makes detection robust to slight
    # rendering shifts between pages.
    cell_inset: float = 0.20         # piece sample = central 60% of the cell
    king_inner_frac: float = 0.25    # inner sub-patch = central 25% of the piece
    # Row-0 pieces in Sijbrands' crops are often clipped at the top
    # (board boundary cuts the upper half of corner kings).  The visible
    # portion sits at the bottom of the cell with reduced contrast vs.
    # the surrounding blue, so the default thresholds miss them.  Relax
    # by 10–15 on the top row only — verified on every annotated
    # ``WK at sq 5`` and ``BK at sq 4``; doesn't change any other row.
    top_row_white_min: float = 175.0
    top_row_black_max: float = 95.0
    # Board-bound detection.  We classify a row/column as "in the board"
    # iff at least ``board_coverage_min`` of its pixels are darker than
    # ``board_pixel_max``.  This separates the board (most pixels are
    # blue squares or piece outlines) from the caption ("DIAGRAMME N" —
    # ~20% dark text on white background) and the page padding (~0%).
    #
    # Threshold tuned at 0.35 to handle illustrative boards with many
    # white pieces — e.g. Sijbrands p.66 #2 has 30 whites in a frame
    # pattern; columns crossing them dip to ~0.49 coverage as the white
    # pixels (>230) don't count.  Caption rows top out at 0.26, so 0.35
    # keeps them excluded.
    board_pixel_max: float = 230.0
    board_coverage_min: float = 0.35


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


def config_for_source(source: str) -> DetectorConfig:
    """Return the ``DetectorConfig`` tuned for a given source.

    Sijbrands and Springer share the blue-style classifier (matches
    99.87% per-square on Sijbrands' 65 annotated diagrams).  Roozenburg
    uses the B&W style — white pieces on white squares carry no mean-
    brightness signal, so the classifier looks at inner-vs-ring
    contrast instead.
    """
    if source.upper() == "ROOZENBURG":
        return DetectorConfig(style="bw")
    return DetectorConfig()


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


def _trim_outer_padding(arr: np.ndarray, max_intensity: float = 245.0) -> np.ndarray:
    """Trim pure-white outer rows/columns from a board crop.

    For the B&W detector path, where the operator's bbox already
    centres the board: only thin all-bright margins (border whitespace)
    get cut, the actual playing field stays intact even when half its
    rows are mostly white squares.
    """
    rows_bright = (arr >= max_intensity).all(axis=1)
    cols_bright = (arr >= max_intensity).all(axis=0)
    y0 = int(np.argmax(~rows_bright))
    y1 = arr.shape[0] - int(np.argmax(~rows_bright[::-1]))
    x0 = int(np.argmax(~cols_bright))
    x1 = arr.shape[1] - int(np.argmax(~cols_bright[::-1]))
    if y1 <= y0 or x1 <= x0:
        return arr
    return arr[y0:y1, x0:x1]


def _patch_mean(arr: np.ndarray, y0: int, y1: int, x0: int, x1: int) -> float:
    """Mean grayscale intensity in a region.  ``arr`` is HxW grayscale."""
    return float(arr[y0:y1, x0:x1].mean())


def _detect_bw_board_bounds(arr: np.ndarray) -> tuple[int, int, int, int] | None:
    """Locate the inner board inside a B&W crop via its dark border line.

    Roozenburg diagrams have a thin solid black rectangle around the
    10×10 grid.  When the operator's bbox includes whitespace or
    marginal text (move numbers in the gutter), the grid 10×10 ends up
    aligned to the crop's edge instead of the actual board, shifting
    every cell sample.  This function finds the longest dark horizontal
    line (the top border) and the longest dark vertical line (the left
    border), and assumes the board is square — that fixes ~all crops
    where the operator was slightly generous with the bbox.

    Returns ``(y0, y1, x0, x1)`` of the playable area, or ``None`` if
    no clear borders are found (caller should fall back to the
    pure-white trim).
    """
    very_dark = arr < 80
    h, w = very_dark.shape
    # Per-row longest run of consecutive dark pixels — peaks at border rows.
    def longest_run_per_row(mask: np.ndarray) -> np.ndarray:
        out = np.zeros(mask.shape[0], dtype=np.int32)
        for i in range(mask.shape[0]):
            row = mask[i]
            diffs = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
            starts = np.where(diffs == 1)[0]
            ends = np.where(diffs == -1)[0]
            if len(starts):
                out[i] = int((ends - starts).max())
        return out

    row_runs = longest_run_per_row(very_dark)
    col_runs = longest_run_per_row(very_dark.T)
    # Border = row/col with the longest run AND that run covers most of
    # the eventual board's width.  Threshold: run >= half the smaller
    # crop dimension — rules out short dark blobs (text, pieces).
    min_border_len = min(h, w) // 2
    valid_rows = np.where(row_runs >= min_border_len)[0]
    valid_cols = np.where(col_runs >= min_border_len)[0]
    if len(valid_rows) < 1 or len(valid_cols) < 1:
        return None
    y_top = int(valid_rows[0])
    y_bot = int(valid_rows[-1])
    x_left = int(valid_cols[0])
    x_right = int(valid_cols[-1])
    # Single-border cases: the operator's bbox sometimes cuts the board
    # tight against the bottom or right edge.  Estimate the missing
    # bound from the detected border's run length — the board is
    # square, so the perpendicular side equals the horizontal run.
    side_from_top = int(row_runs[y_top])
    side_from_left = int(col_runs[x_left])
    if y_bot - y_top < min_border_len:
        y_bot = min(y_top + side_from_top, h)
    if x_right - x_left < min_border_len:
        x_right = min(x_left + side_from_left, w)
    return y_top, y_bot, x_left, x_right



    """Mean grayscale intensity in a region.  ``arr`` is HxW grayscale."""
    return float(arr[y0:y1, x0:x1].mean())


def _inner_and_ring(
    arr: np.ndarray, y_mid: float, x_mid: float, cell_h: float, cell_w: float
) -> tuple[float, float]:
    """Return ``(inner_mean, ring_mean)`` for a cell — the B&W detector's
    main classification feature.

    Inner: tight central patch (~30% of the cell side).
    Ring: 4 small patches at ~64% of the cell radius, in the cardinal
    directions — places where the piece's outline would sit if a piece
    is present, and where the background sits if the cell is empty.
    """
    i_h = cell_h * 0.15
    i_w = cell_w * 0.15
    inner = _patch_mean(
        arr,
        int(y_mid - i_h),
        int(y_mid + i_h),
        int(x_mid - i_w),
        int(x_mid + i_w),
    )
    samples: list[float] = []
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        ry = y_mid + dy * cell_h * 0.32
        rx = x_mid + dx * cell_w * 0.32
        y0 = int(ry - i_h)
        y1 = int(ry + i_h)
        x0 = int(rx - i_w)
        x1 = int(rx + i_w)
        if y0 < 0 or y1 > arr.shape[0] or x0 < 0 or x1 > arr.shape[1]:
            continue
        samples.append(_patch_mean(arr, y0, y1, x0, x1))
    ring = float(np.mean(samples)) if samples else inner
    return inner, ring



def detect_fen(image: Path | Image.Image, *, config: DetectorConfig | None = None) -> str:
    """Return ``W:W...:B...`` FEN string predicted from the crop.

    Always assumes white to move (``W:`` prefix) — printed diagrams
    don't encode the side to move and the manual annotator defaults
    to white anyway.

    Accepts a file path *or* an in-memory ``PIL.Image`` — the latter
    lets the bbox-manifest path crop a page-image on the fly without
    a round-trip through the filesystem.
    """
    cfg = config or DetectorConfig()
    img = (image if isinstance(image, Image.Image) else Image.open(image)).convert("L")
    full = np.asarray(img, dtype=np.float32)
    if cfg.style == "bw":
        # B&W crops come from the manual crop tool — the operator
        # picks two corners that may include some white margin or
        # adjacent text.  Try to locate the actual board via its
        # dark rectangular border first; fall back to pure-white
        # trim if no border is detected (e.g. very tight crops).
        bounds = _detect_bw_board_bounds(full)
        if bounds is not None:
            y0, y1, x0, x1 = bounds
            arr = full[y0:y1, x0:x1]
        else:
            arr = _trim_outer_padding(full)
    else:
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

            if cfg.style == "bw":
                # B&W boards (Roozenburg): empty white squares are as
                # bright as white pieces, so absolute brightness alone
                # mis-classifies. Compare the cell's central inner patch
                # to a ring just outside it — a piece creates a strong
                # delta (its colour vs. the surrounding ring crossing
                # the outline), an empty cell stays flat.
                inner_mean, ring_mean = _inner_and_ring(
                    arr, y_mid, x_mid, cell_h, cell_w
                )
                delta = inner_mean - ring_mean
                if inner_mean <= cfg.bw_dark_max and delta <= -cfg.bw_dark_delta:
                    blacks.append(str(square))
                elif inner_mean >= cfg.bw_light_min and delta >= cfg.bw_light_delta:
                    whites.append(str(square))
                # else: empty — skip
                # NOTE: king detection deferred for B&W — needs more
                # samples to calibrate; today every B&W piece is a man.
                continue

            white_min = cfg.top_row_white_min if row == 0 else cfg.white_piece_min
            black_max = cfg.top_row_black_max if row == 0 else cfg.black_piece_max

            if piece_mean >= white_min:
                # Likely white piece.  Probe for king marker by comparing
                # the inner patch (king dot) against the surrounding ring.
                king = _is_king(arr, y_mid, x_mid, cell_h, cell_w, cfg, "white")
                whites.append(f"K{square}" if king else str(square))
            elif piece_mean <= black_max:
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
