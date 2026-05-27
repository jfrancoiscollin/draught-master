"""Extract isolated diagram crops from sijbrandscourse.pdf.

Sprint 3 / Lane B of ``docs/STRATEGIE_DIAGRAMS_PLAN.md``.

Pipeline
--------
1. Render each page referenced by a Sijbrands passage at 150 DPI.
2. Detect boards via **texture variance** — a 30 px sliding window's
   standard deviation is high inside the alternating gray/light board
   (σ > 30) and ≈ 0 on blank paper. Sijbrands boards have no drawn
   border so line-based detectors don't see them.
3. Filter blobs by area, aspect ratio, and IoU dedupe.
4. Get caption positions from ``pdftotext -bbox-layout`` (XHTML output
   with per-word bboxes in PDF points).
5. Match each ``DIAGRAMME N`` caption to its nearest board with
   ``|Δy| + |Δx_center| < 150 px``.  Cross-references in prose are
   typically > 300 px away from any board.
6. Crop the matched board (+5 px padding), downscale to 500 px wide
   JPEG Q82, save under ``pages/sijbrands/diagrams/`` and write a flat
   manifest indexed by ``(page, number)``.

Run from the repo root::

    python -m backend.strategy.extract_sijbrands_diagrams

Reproducibility note: this script intentionally hard-codes paths
(``docs/corpus/sijbrandscourse.pdf`` from the dilf checkout, output
under this package).  Adjust if those move.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

DILF_ROOT = Path(__file__).resolve().parents[3] / "dilf"
PDF = DILF_ROOT / "docs" / "corpus" / "sijbrandscourse.pdf"
OUT_BASE = Path(__file__).resolve().parent / "pages" / "sijbrands"
RENDER_DIR = OUT_BASE / ".render_cache"
CROP_DIR = OUT_BASE / "diagrams"

SCALE = 150 / 72  # PDF points → pixels at 150 DPI
MAX_DIST_PX = 150
TEXTURE_THRESHOLD = 30
MIN_BOARD_PX = 200


def _iou(a: tuple, b: tuple) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    union = (
        (a[2] - a[0]) * (a[3] - a[1])
        + (b[2] - b[0]) * (b[3] - b[1])
        - inter
    )
    return inter / union


def detect_boards(image_path: Path) -> list[tuple[int, int, int, int]]:
    arr = np.array(Image.open(image_path).convert("L")).astype(np.float32)
    mean = ndimage.uniform_filter(arr, size=30)
    sq_mean = ndimage.uniform_filter(arr ** 2, size=30)
    std = np.sqrt(np.maximum(sq_mean - mean ** 2, 0))
    mask = std > TEXTURE_THRESHOLD
    mask = ndimage.binary_closing(mask, iterations=5)
    mask = ndimage.binary_opening(mask, iterations=2)
    labeled, _ = ndimage.label(mask)
    raw = []
    for sl in ndimage.find_objects(labeled):
        if sl is None:
            continue
        top, bottom = sl[0].start, sl[0].stop
        left, right = sl[1].start, sl[1].stop
        h, w = bottom - top, right - left
        if w < MIN_BOARD_PX or h < MIN_BOARD_PX:
            continue
        if not (0.75 <= w / h <= 1.30):
            continue
        # Each real board often produces TWO connected components: a clean
        # 1:1 blob and a slightly bigger one extended upward to include the
        # "DIAGRAMME N" caption row. We dedupe by IoU and keep the blob
        # whose aspect is closest to 1.0 — that's the actual board without
        # the caption above (and crucially without the missing 26 px on the
        # left+bottom edges that the elongated blob suffers from).
        aspect_score = abs(w / h - 1.0)
        raw.append((left, top, right, bottom, aspect_score))
    raw.sort(key=lambda r: r[-1])
    kept = []
    for b in raw:
        if not any(_iou(b[:4], k[:4]) > 0.3 for k in kept):
            kept.append(b)
    return [k[:4] for k in kept]


def caption_positions(pdf: Path, page: int) -> list[tuple[int, tuple[float, float, float, float]]]:
    out = subprocess.run(
        [
            "pdftotext", "-bbox-layout",
            "-f", str(page), "-l", str(page),
            str(pdf), "-",
        ],
        capture_output=True, text=True, check=True,
    )
    root = ET.fromstring(out.stdout)
    words = list(root.iter())
    captions = []
    for i, w in enumerate(words):
        tag = w.tag.split("}")[-1]
        if tag == "word" and w.text and re.match(r"^DIAGRAMME$", w.text.strip(), re.IGNORECASE):
            if i + 1 < len(words) and words[i + 1].text:
                m = re.match(r"^(\d+)$", words[i + 1].text.strip())
                if m:
                    xmin = float(w.get("xMin"))
                    ymin = float(w.get("yMin"))
                    xmax = float(words[i + 1].get("xMax"))
                    ymax = float(words[i + 1].get("yMax"))
                    captions.append((int(m.group(1)), (xmin, ymin, xmax, ymax)))
    return captions


def render_page(page: int) -> Path:
    out = RENDER_DIR / f"p{page:04d}.png"
    if out.exists():
        return out
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "pdftoppm", "-r", "150",
            "-f", str(page), "-l", str(page),
            "-png", str(PDF), f"{RENDER_DIR}/p{page:04d}_",
        ],
        check=True, capture_output=True,
    )
    next(RENDER_DIR.glob(f"p{page:04d}_*.png")).rename(out)
    return out


def main() -> int:
    sys.path.insert(0, str(DILF_ROOT))
    from pedagogy.prose.fixtures.prose_passages_sijbrands_course import (  # type: ignore[import-not-found]
        ALL_PASSAGES,
    )

    CROP_DIR.mkdir(parents=True, exist_ok=True)
    pages = sorted({p.page for p in ALL_PASSAGES})
    print(f"Processing {len(pages)} Sijbrands pages...")

    entries: list[dict] = []
    for idx, page in enumerate(pages, start=1):
        img_path = render_page(page)
        boards = detect_boards(img_path)
        captions = caption_positions(PDF, page)
        if not boards or not captions:
            continue
        page_img = Image.open(img_path)
        for cap_num, (cx1, cy1, _cx2, _cy2) in captions:
            c_y_px = cy1 * SCALE
            c_x_px = cx1 * SCALE
            best = min(
                boards,
                key=lambda b: abs(b[1] - c_y_px) + abs((b[0] + b[2]) / 2 - c_x_px),
            )
            dist = abs(best[1] - c_y_px) + abs((best[0] + best[2]) / 2 - c_x_px)
            if dist >= MAX_DIST_PX:
                continue
            crop_box = (
                max(best[0] - 12, 0),
                max(best[1] - 12, 0),
                min(best[2] + 12, page_img.width),
                min(best[3] + 12, page_img.height),
            )
            crop = page_img.crop(crop_box).convert("RGB")
            if crop.width > 500:
                crop = crop.resize(
                    (500, int(crop.height * 500 / crop.width)),
                    Image.LANCZOS,
                )
            crop_name = f"diagram_{cap_num:03d}_p{page:04d}.jpg"
            crop.save(CROP_DIR / crop_name, "JPEG", quality=82, optimize=True)
            entries.append({"page": page, "number": cap_num, "crop": crop_name})
        if idx % 30 == 0:
            print(f"  ...{idx}/{len(pages)} pages, {len(entries)} crops matched")

    manifest = {"source": "SIJBRANDS", "entries": entries}
    (OUT_BASE / "diagrams_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )
    print(f"Done: {len(entries)} crops, {len({(e['page'], e['number']) for e in entries})} unique (page,number)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
