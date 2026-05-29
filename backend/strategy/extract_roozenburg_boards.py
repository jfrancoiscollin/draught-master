"""Auto-extract Roozenburg diagrams from rendered page JPGs.

Roozenburg pages mix prose with 0-3 printed diagrams.  Every diagram
has a thin black rectangular border around the 10×10 grid (run length
~170 pixels at the bundle's resolution).  Two-pass scan:

1. For every row of the page, compute the longest run of dark pixels
   (intensity < 80).  Border rows show up as runs of 150-180 px;
   text and pieces produce much shorter runs.
2. Walk the border-row candidates sorted by ``y``; pair each one with
   another ~170 px below at the same ``x`` range.  Falls back to a
   square assumption (``bottom = top + run_length``) when only one
   border is visible (rare — happens when an inner border row blends
   with a piece's outline at the bottom of the board).

Sort the resulting bboxes in reading order (top-to-bottom, then
left-to-right) and number them 1, 2, 3... per page — matches the
convention JF used when seeding the first batch by hand.

Run from the repo root::

    python -m backend.strategy.extract_roozenburg_boards

Merges with the existing ``diagrams_manifest.json``: hand-curated bbox
entries always win on the same ``(page, number)`` key, so re-running
is safe.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

_PAGES_DIR = Path(__file__).parent / "pages" / "roozenburg"

# Board border characteristics observed on the bundled JPG resolution.
# ``min_run`` filters out anything that's not a board border.  The
# ``size_range`` lets the pairing step accept some slack in case the
# border is occluded by a piece on its edge.
_MIN_BORDER_RUN = 150
_BOARD_SIZE_RANGE = (150, 200)


def _longest_run_per_row(mask: np.ndarray) -> tuple[np.ndarray, list[int | None], list[int | None]]:
    n = mask.shape[0]
    runs = np.zeros(n, dtype=np.int32)
    starts_out: list[int | None] = [None] * n
    ends_out: list[int | None] = [None] * n
    for i in range(n):
        row = mask[i]
        diffs = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts = np.where(diffs == 1)[0]
        ends = np.where(diffs == -1)[0]
        if len(starts):
            r = ends - starts
            b = int(np.argmax(r))
            runs[i] = int(r[b])
            starts_out[i] = int(starts[b])
            ends_out[i] = int(ends[b])
    return runs, starts_out, ends_out


def detect_boards_on_page(arr: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Return ``[(x0, y0, x1, y1), ...]`` of every board on the page.

    Sorted by reading order (top to bottom, left to right).
    """
    very_dark = arr < 80
    row_runs, row_starts, row_ends = _longest_run_per_row(very_dark)
    candidates = [
        (y, row_runs[y], row_starts[y], row_ends[y])
        for y in range(arr.shape[0])
        if row_runs[y] >= _MIN_BORDER_RUN
    ]
    used: set[int] = set()
    boards: list[tuple[int, int, int, int]] = []
    for i, (y, r, s, e) in enumerate(candidates):
        if i in used:
            continue
        matched = False
        # Look for a bottom border within the expected board height.  Track
        # ``matched`` explicitly rather than relying on a ``for/else`` —
        # the "we've gone past the max" early-break would otherwise skip
        # the fallback and leave the top border orphaned.
        for j in range(i + 1, len(candidates)):
            if j in used:
                continue
            y2, r2, s2, e2 = candidates[j]
            if not (_BOARD_SIZE_RANGE[0] <= (y2 - y) <= _BOARD_SIZE_RANGE[1]):
                if y2 - y > _BOARD_SIZE_RANGE[1]:
                    break
                continue
            if s2 is None or e2 is None:
                continue
            if abs(s - s2) <= 15 and abs(e - e2) <= 15:
                boards.append((s, y, e, y2))
                used.add(i)
                used.add(j)
                matched = True
                break
        if not matched:
            # Bottom border occluded or out of range — assume square.
            boards.append((s, y, e, y + r))
            used.add(i)
    # Filter out false positives — text regions occasionally show a long
    # dark run that looks like a top border.  A real board has the
    # checkered grey/white pattern *below* that border; text is mostly
    # white.  Reject any candidate whose interior averages too bright.
    real_boards: list[tuple[int, int, int, int]] = []
    for x0, y0, x1, y1 in boards:
        if y1 > arr.shape[0]:
            y1 = arr.shape[0]
        if x1 > arr.shape[1]:
            x1 = arr.shape[1]
        interior = arr[y0 + 5:y1 - 5, x0 + 5:x1 - 5]
        if interior.size == 0:
            continue
        # Boards average ~190-210 (lots of grey squares); text ~245.
        if interior.mean() <= 230:
            real_boards.append((x0, y0, x1, y1))
    boards = real_boards

    # Sort and de-duplicate: two candidates may converge onto the same
    # diagram if the top and bottom borders bleed into adjacent rows
    # (anti-aliasing, JPEG noise).  Drop any board that overlaps >=50%
    # with one we've already kept.
    boards.sort(key=lambda b: (b[1], b[0]))
    deduped: list[tuple[int, int, int, int]] = []
    for b in boards:
        keep = True
        for k in deduped:
            ix0, iy0 = max(b[0], k[0]), max(b[1], k[1])
            ix1, iy1 = min(b[2], k[2]), min(b[3], k[3])
            if ix1 <= ix0 or iy1 <= iy0:
                continue
            inter = (ix1 - ix0) * (iy1 - iy0)
            area_b = (b[2] - b[0]) * (b[3] - b[1])
            if inter / area_b >= 0.5:
                keep = False
                break
        if keep:
            deduped.append(b)
    return deduped


def main() -> int:
    pages = sorted(_PAGES_DIR.glob("page_*.jpg"))
    print(f"Scanning {len(pages)} pages…")
    new_entries: list[dict] = []
    for page_path in pages:
        page = int(page_path.stem.split("_")[1])
        arr = np.asarray(Image.open(page_path).convert("L"), dtype=np.float32)
        for i, bbox in enumerate(detect_boards_on_page(arr), start=1):
            new_entries.append({
                "page": page,
                "number": i,
                "bbox": [int(v) for v in bbox],
            })
    print(f"Detected {len(new_entries)} boards.")

    # Merge with existing manifest — JF's hand-picked bboxes win.  An
    # auto-detected board that overlaps an existing entry is treated as
    # the same diagram (operator's chosen number kept, bbox kept), even
    # if my sequential numbering would have assigned a different one.
    # That preserves the link between ``diagrams_fens.json`` (keyed by
    # the operator's numbers) and the underlying bboxes.
    manifest_path = _PAGES_DIR / "diagrams_manifest.json"
    existing_by_page: dict[int, list[dict]] = {}
    if manifest_path.is_file():
        # Re-validate every existing bbox via the same interior-brightness
        # check used to filter detector output.  Previous extractor runs
        # produced false positives (text regions misread as boards); any
        # such entry that still sits in the manifest gets dropped here so
        # the new detector's correct bbox can take its place.
        for e in json.loads(manifest_path.read_text()).get("entries", []):
            page = e["page"]
            page_path = _PAGES_DIR / f"page_{page:04d}.jpg"
            if not page_path.is_file():
                existing_by_page.setdefault(page, []).append(e)
                continue
            arr = np.asarray(Image.open(page_path).convert("L"), dtype=np.float32)
            x0, y0, x1, y1 = e["bbox"]
            x1 = min(x1, arr.shape[1])
            y1 = min(y1, arr.shape[0])
            interior = arr[y0 + 5:y1 - 5, x0 + 5:x1 - 5]
            if interior.size > 0 and interior.mean() > 230:
                print(f"  drop stale entry p.{page} #{e['number']} bbox={e['bbox']} (interior too bright)")
                continue
            existing_by_page.setdefault(page, []).append(e)

    def bbox_overlap(a: list[int], b: list[int]) -> float:
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        ix0, iy0 = max(ax0, bx0), max(ay0, by0)
        ix1, iy1 = min(ax1, bx1), min(ay1, by1)
        if ix1 <= ix0 or iy1 <= iy0:
            return 0.0
        inter = (ix1 - ix0) * (iy1 - iy0)
        area_a = (ax1 - ax0) * (ay1 - ay0)
        area_b = (bx1 - bx0) * (by1 - by0)
        return inter / min(area_a, area_b)

    merged: list[dict] = []
    added = 0
    used_existing: set[tuple[int, int]] = set()
    for entry in new_entries:
        page = entry["page"]
        for existing in existing_by_page.get(page, []):
            if bbox_overlap(entry["bbox"], existing["bbox"]) >= 0.5:
                # Same diagram — keep the human's entry.
                break
        else:
            merged.append(entry)
            added += 1
    # Append all existing entries we haven't already merged above.
    for entries in existing_by_page.values():
        for e in entries:
            merged.append(e)
    merged.sort(key=lambda e: (e["page"], e["number"]))
    # Drop any duplicate (page, number) keys preferring entries from the
    # existing manifest (those have ``_keep`` semantics).
    dedup: dict[tuple[int, int], dict] = {}
    for e in merged:
        key = (e["page"], e["number"])
        dedup[key] = e
    out_entries = sorted(dedup.values(), key=lambda e: (e["page"], e["number"]))
    manifest_path.write_text(
        json.dumps({"source": "ROOZENBURG", "entries": out_entries}, indent=2) + "\n",
    )
    print(
        f"Manifest: {len(out_entries)} entries "
        f"({added} new from detector, "
        f"{sum(len(v) for v in existing_by_page.values())} pre-existing)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
