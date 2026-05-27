"""Extract isolated diagram crops from a strategy-corpus PDF.

Sprint 3-4 / Lane B of ``docs/STRATEGIE_DIAGRAMS_PLAN.md``.

Generalised from the Sijbrands-only proof-of-concept (PR #78-79) to
accept any source code that has both:

1. A dilf fixture module under ``pedagogy.prose.fixtures.prose_passages_*``
   exposing ``ALL_PASSAGES`` (used to enumerate referenced pages).
2. A "DIAGRAMME N" caption pattern in its prose (the only anchor we
   know how to use today — Roozenburg has no captions and Keller has
   non-numbered ones, both are left for future iterations).

Pipeline
--------
1. Render each referenced page at 150 DPI.
2. Detect boards via **texture variance** — a 30 px sliding window's
   standard deviation is high inside the alternating gray/light board
   (σ > threshold) and ≈ 0 on blank paper.
3. Filter blobs by area, aspect ratio, and IoU dedupe (preferring blobs
   closest to square, since caption-included blobs skew aspect).
4. Get caption positions from ``pdftotext -bbox-layout`` and match each
   ``DIAGRAMME N`` token to its nearest board within ``MAX_DIST_PX``.
5. Crop the matched board (+pad), downscale to ``MAX_WIDTH`` JPEG Q82,
   save under ``pages/<source>/diagrams/`` with manifest indexed by
   ``(page, number)``.

Run from the repo root::

    python -m backend.strategy.extract_diagrams --source sijbrands
    python -m backend.strategy.extract_diagrams --source springer

The script auto-resolves the PDF path and fixture module name from the
source code via ``SOURCE_CONFIG``. Tune thresholds per-source there.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

DILF_ROOT = Path(__file__).resolve().parents[3] / "dilf"
PAGES_BASE = Path(__file__).resolve().parent / "pages"

SCALE = 150 / 72  # PDF points → pixels at 150 DPI


@dataclass(frozen=True)
class SourceConfig:
    """Per-source extraction parameters. Tune when adding a new corpus."""

    slug: str  # subdir name under pages/
    pdf_basename: str  # in dilf/docs/corpus/
    fixture_module: str
    texture_threshold: float = 30.0
    min_board_px: int = 200
    max_dist_px: int = 150  # caption-to-board pixel distance
    crop_pad_px: int = 12
    crop_max_width: int = 500


SOURCE_CONFIG: dict[str, SourceConfig] = {
    "sijbrands": SourceConfig(
        slug="sijbrands",
        pdf_basename="sijbrandscourse.pdf",
        fixture_module="prose_passages_sijbrands_course",
    ),
    "springer": SourceConfig(
        slug="springer",
        pdf_basename="springercourse.pdf",
        fixture_module="prose_passages_springer_course",
    ),
}


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


def detect_boards(
    image_path: Path, *, texture_threshold: float, min_board_px: int
) -> list[tuple[int, int, int, int]]:
    arr = np.array(Image.open(image_path).convert("L")).astype(np.float32)
    mean = ndimage.uniform_filter(arr, size=30)
    sq_mean = ndimage.uniform_filter(arr ** 2, size=30)
    std = np.sqrt(np.maximum(sq_mean - mean ** 2, 0))
    mask = std > texture_threshold
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
        if w < min_board_px or h < min_board_px:
            continue
        if not (0.75 <= w / h <= 1.30):
            continue
        # Each real board often produces two connected components: a clean
        # 1:1 blob and a slightly bigger one extended upward to include the
        # "DIAGRAMME N" caption row. Keep the blob closest to square so
        # the crop edges line up with the actual board boundary.
        aspect_score = abs(w / h - 1.0)
        raw.append((left, top, right, bottom, aspect_score))
    raw.sort(key=lambda r: r[-1])
    kept = []
    for b in raw:
        if not any(_iou(b[:4], k[:4]) > 0.3 for k in kept):
            kept.append(b)
    return [k[:4] for k in kept]


def caption_positions(
    pdf: Path, page: int
) -> list[tuple[int, tuple[float, float, float, float]]]:
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


def render_page(pdf: Path, page: int, render_dir: Path) -> Path:
    out = render_dir / f"p{page:04d}.png"
    if out.exists():
        return out
    render_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "pdftoppm", "-r", "150",
            "-f", str(page), "-l", str(page),
            "-png", str(pdf), f"{render_dir}/p{page:04d}_",
        ],
        check=True, capture_output=True,
    )
    next(render_dir.glob(f"p{page:04d}_*.png")).rename(out)
    return out


def extract(cfg: SourceConfig) -> int:
    sys.path.insert(0, str(DILF_ROOT))
    mod = __import__(
        f"pedagogy.prose.fixtures.{cfg.fixture_module}",
        fromlist=["ALL_PASSAGES"],
    )

    pdf = DILF_ROOT / "docs" / "corpus" / cfg.pdf_basename
    out_base = PAGES_BASE / cfg.slug
    render_dir = out_base / ".render_cache"
    crop_dir = out_base / "diagrams"
    crop_dir.mkdir(parents=True, exist_ok=True)

    pages = sorted({p.page for p in mod.ALL_PASSAGES})
    print(f"[{cfg.slug}] processing {len(pages)} pages...")

    entries: list[dict] = []
    for idx, page in enumerate(pages, start=1):
        img_path = render_page(pdf, page, render_dir)
        boards = detect_boards(
            img_path,
            texture_threshold=cfg.texture_threshold,
            min_board_px=cfg.min_board_px,
        )
        captions = caption_positions(pdf, page)
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
            if dist >= cfg.max_dist_px:
                continue
            pad = cfg.crop_pad_px
            crop_box = (
                max(best[0] - pad, 0),
                max(best[1] - pad, 0),
                min(best[2] + pad, page_img.width),
                min(best[3] + pad, page_img.height),
            )
            crop = page_img.crop(crop_box).convert("RGB")
            if crop.width > cfg.crop_max_width:
                crop = crop.resize(
                    (cfg.crop_max_width, int(crop.height * cfg.crop_max_width / crop.width)),
                    Image.LANCZOS,
                )
            crop_name = f"diagram_{cap_num:03d}_p{page:04d}.jpg"
            crop.save(crop_dir / crop_name, "JPEG", quality=82, optimize=True)
            entries.append({"page": page, "number": cap_num, "crop": crop_name})
        if idx % 30 == 0:
            print(f"  ...{idx}/{len(pages)} pages, {len(entries)} crops matched")

    manifest = {"source": cfg.slug.upper(), "entries": entries}
    (out_base / "diagrams_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )
    unique_pairs = len({(e["page"], e["number"]) for e in entries})
    print(
        f"[{cfg.slug}] done: {len(entries)} crops, "
        f"{unique_pairs} unique (page,number)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source",
        required=True,
        choices=sorted(SOURCE_CONFIG.keys()),
        help="source slug — matches subdir under pages/",
    )
    args = parser.parse_args()
    return extract(SOURCE_CONFIG[args.source])


if __name__ == "__main__":
    raise SystemExit(main())
