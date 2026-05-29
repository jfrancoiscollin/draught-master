"""Offline batch detector — run ``fen_detector.detect_fen`` on every crop
of a source's manifest and write the predictions to
``pages/<source>/diagrams_fens_auto.json``.

Run from the repo root::

    python -m backend.strategy.generate_auto_fens SIJBRANDS

Output schema mirrors ``diagrams_fens.json`` but with an ``_auto: true``
flag on every entry so the frontend (and the operator scanning the JSON)
can tell apart automated predictions from human-verified annotations.
The two files coexist — the API merges them with human taking precedence.

Designed to be re-runnable.  Each rerun overwrites the auto file with
the current detector's output; the human file is never touched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .fen_detector import detect_fen

_PAGES_DIR = Path(__file__).parent / "pages"


def generate(source: str) -> tuple[int, int]:
    """Predict every (page, number) in the source's manifest.

    Returns ``(processed, skipped)``.  ``skipped`` counts manifest
    entries whose crop file is missing from disk — bookkeeping issue
    upstream in the extractor.
    """
    src_dir = _PAGES_DIR / source.lower()
    manifest_path = src_dir / "diagrams_manifest.json"
    if not manifest_path.is_file():
        print(f"[skip] {source}: no diagrams_manifest.json")
        return 0, 0
    manifest = json.loads(manifest_path.read_text())["entries"]
    crops_dir = src_dir / "diagrams"
    out_entries: list[dict] = []
    skipped = 0
    for i, entry in enumerate(manifest, start=1):
        crop_path = crops_dir / entry["crop"]
        if not crop_path.is_file():
            skipped += 1
            continue
        fen = detect_fen(crop_path)
        out_entries.append({
            "page": entry["page"],
            "number": entry["number"],
            "fen": fen,
            "_auto": True,
        })
        if i % 50 == 0:
            print(f"  ... {i}/{len(manifest)}")
    out_path = src_dir / "diagrams_fens_auto.json"
    out_path.write_text(
        json.dumps({"source": source, "entries": out_entries}, indent=2, ensure_ascii=False) + "\n",
    )
    print(f"[ok] {source}: {len(out_entries)} entries → {out_path}")
    if skipped:
        print(f"     ({skipped} manifest entries skipped — crop file missing)")
    return len(out_entries), skipped


def main(argv: list[str]) -> int:
    sources = argv[1:] if len(argv) > 1 else ["SIJBRANDS"]
    for src in sources:
        generate(src)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
