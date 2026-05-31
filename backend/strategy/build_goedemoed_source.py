"""Build the Goedemoed 'A Course in Draughts' strategy source.

One-off build script (run locally; not imported at runtime). Renders the
diagram pages of a Goedemoed volume, detects the gray-checkerboard boards
with the proven dilf detector, crops each, and writes the strategy-source
files the app already understands:

    backend/strategy/pages/goedemoed/
        diagrams/diagram_NNNN_pPPPP.jpg   tight board crops
        diagrams_manifest.json            {"entries": [{crop, number, page}]}
        diagrams_fens_auto.json           {"source", "entries": [{page, number, fen, _auto}]}

The auto-FEN comes from strategy.fen_detector.detect_fen with the GOEDEMOED
('grey' style) config — the same in-app detector that pre-fills the
annotation editor. Operators then correct a sample into diagrams_fens.json
and the GOEDEMOED config is tuned to >99% per-square.

Usage (from backend/):
    python -m strategy.build_goedemoed_source --pdf /home/user/dilf/docs/corpus/Exercise_2.pdf \
        --pages 2-203 [--cache /tmp/goed_scan] [--dpi 300]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_DILF = Path("/home/user/dilf")
sys.path.insert(0, str(_DILF))

import numpy as np
from PIL import Image

from strategy.fen_detector import config_for_source, detect_fen

_PAGES = Path(__file__).resolve().parent / "pages"
MIN_BOARD_AREA = 100_000
CROP_PX = 440


def _detect_boards(png: Path):
    import scripts.extract_diagrams as E
    E.MIN_BOARD_AREA = MIN_BOARD_AREA
    return E._detect_boards(png)


def _render(pdf: Path, page: int, dpi: int, cache: Path) -> Path:
    import scripts.extract_diagrams as E
    cache.mkdir(parents=True, exist_ok=True)
    png = cache / f"p{page:03d}.png"
    if not png.exists():
        E._render_page_png(pdf, page, dpi, png)
    return png


def _column_major(boards):
    """Order boards as printed: down the left column (1..k), then the right.

    Split by page-x midpoint into columns, sort each top-to-bottom.
    """
    if not boards:
        return []
    xs = [(b[0] + b[2]) / 2 for b in boards]
    mid = (min(xs) + max(xs)) / 2
    left = sorted([b for b in boards if (b[0] + b[2]) / 2 <= mid], key=lambda b: b[1])
    right = sorted([b for b in boards if (b[0] + b[2]) / 2 > mid], key=lambda b: b[1])
    return left + right


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True, help="e.g. 2-203")
    ap.add_argument("--source", default="GOEDEMOED",
                    help="library source key; output dir is pages/<source.lower()>")
    ap.add_argument("--cache", default="/tmp/goed_scan/pages")
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args(argv)

    source = args.source.upper()
    out = _PAGES / source.lower()
    pdf = Path(args.pdf)
    lo, hi = (int(x) for x in args.pages.split("-"))
    cache = Path(args.cache)
    crops_dir = out / "diagrams"
    crops_dir.mkdir(parents=True, exist_ok=True)

    cfg = config_for_source(source)
    manifest_entries = []
    auto_entries = []
    seq = 0
    for page in range(lo, hi + 1):
        png = _render(pdf, page, args.dpi, cache)
        boards = _column_major(_detect_boards(png))
        if not boards:
            continue
        full = Image.open(png).convert("L")
        for number, bbox in enumerate(boards, start=1):
            seq += 1
            crop_name = f"diagram_{seq:04d}_p{page:04d}.jpg"
            crop = full.crop((bbox[0], bbox[1], bbox[2], bbox[3])).convert("L")
            # Store a moderate-resolution crop (keeps repo lean; detection
            # verified identical to full-res down to 440 px). Compute the
            # auto-FEN on the SAME stored image so suggest-fen matches.
            crop = crop.resize((CROP_PX, CROP_PX))
            crop.save(crops_dir / crop_name, format="JPEG", quality=80)
            fen = detect_fen(crop, config=cfg)
            manifest_entries.append({"crop": crop_name, "number": number, "page": page})
            auto_entries.append({"page": page, "number": number, "fen": fen, "_auto": True})
        print(f"page {page}: {len(boards)} diagrams")

    (out / "diagrams_manifest.json").write_text(
        json.dumps({"entries": manifest_entries}, indent=2, ensure_ascii=False))
    (out / "diagrams_fens_auto.json").write_text(
        json.dumps({"source": source, "entries": auto_entries}, indent=2, ensure_ascii=False))
    print(f"\n{seq} diagrams across {len({e['page'] for e in manifest_entries})} pages -> {out}")


if __name__ == "__main__":
    main()
