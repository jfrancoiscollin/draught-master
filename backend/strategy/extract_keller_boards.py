"""Auto-extract Keller diagrams from rendered page JPGs.

Keller's diagrams have a *hatched* fill in the dark squares (small
dotted lines, no solid border around the board), so the long-dark-
run trick used for Roozenburg doesn't work.  Texture-variance does:
the dense alternation of hatched / blank squares produces a much
higher local std than the surrounding text or whitespace.

Pipeline
--------
1. 10-pixel uniform filter on intensity² gives a per-pixel std map.
2. Threshold at 30 → mask of "board-textured" pixels.
3. Morphological closing/opening cleans isolated speckles, fills small
   gaps inside the board.
4. Connected components → bounding boxes.  Filter by minimum size and
   aspect ratio (boards are square within ±25%).
5. Dedupe by IoU >=50% to drop multi-detection of the same board.

Output schema mirrors the Roozenburg manifest: bbox-style entries
served on the fly via ``/diagram``.  The FEN detector run on these
crops produces noisy output (Keller's hatched cells have weak mean-
intensity contrast vs. white pieces), so the operator validates each
board via the in-app editor before the result becomes ``kind: human``.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

_PAGES_DIR = Path(__file__).parent / "pages" / "keller"

_TEXTURE_WINDOW = 10
_TEXTURE_THRESHOLD = 30.0
_MIN_BOARD_PX = 140
_ASPECT_RANGE = (0.75, 1.30)


def detect_boards_on_page(arr: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Return ``[(x0, y0, x1, y1), ...]`` of every board on the page.

    Sorted by reading order (top to bottom, left to right).
    """
    mean = ndimage.uniform_filter(arr, size=_TEXTURE_WINDOW)
    sq_mean = ndimage.uniform_filter(arr ** 2, size=_TEXTURE_WINDOW)
    std = np.sqrt(np.maximum(sq_mean - mean ** 2, 0))
    mask = std > _TEXTURE_THRESHOLD
    mask = ndimage.binary_closing(mask, iterations=3)
    mask = ndimage.binary_opening(mask, iterations=2)
    labeled, _ = ndimage.label(mask)
    raw: list[tuple[int, int, int, int]] = []
    for sl in ndimage.find_objects(labeled):
        if sl is None:
            continue
        top, bottom = sl[0].start, sl[0].stop
        left, right = sl[1].start, sl[1].stop
        h_box, w_box = bottom - top, right - left
        if w_box < _MIN_BOARD_PX or h_box < _MIN_BOARD_PX:
            continue
        if not (_ASPECT_RANGE[0] <= w_box / h_box <= _ASPECT_RANGE[1]):
            continue
        # Drop wildly oversized bboxes — happens when texture variance
        # bleeds across the page into adjacent text.  Real Keller boards
        # are ~160 px; cap at 200 to filter merged-with-text artefacts.
        if w_box > 200 or h_box > 200:
            continue
        raw.append((left, top, right, bottom))
    raw.sort(key=lambda b: (b[1], b[0]))
    # Dedupe by IoU.
    deduped: list[tuple[int, int, int, int]] = []
    for b in raw:
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

    manifest_path = _PAGES_DIR / "diagrams_manifest.json"
    existing_by_page: dict[int, list[dict]] = {}
    if manifest_path.is_file():
        for e in json.loads(manifest_path.read_text()).get("entries", []):
            existing_by_page.setdefault(e["page"], []).append(e)

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
    for entry in new_entries:
        page = entry["page"]
        if any(
            bbox_overlap(entry["bbox"], existing["bbox"]) >= 0.5
            for existing in existing_by_page.get(page, [])
        ):
            continue
        merged.append(entry)
        added += 1
    for entries in existing_by_page.values():
        merged.extend(entries)
    dedup: dict[tuple[int, int], dict] = {}
    for e in merged:
        dedup[(e["page"], e["number"])] = e
    out_entries = sorted(dedup.values(), key=lambda e: (e["page"], e["number"]))
    manifest_path.write_text(
        json.dumps({"source": "KELLER", "entries": out_entries}, indent=2) + "\n",
    )
    print(
        f"Manifest: {len(out_entries)} entries "
        f"({added} new from detector, "
        f"{sum(len(v) for v in existing_by_page.values())} pre-existing)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
