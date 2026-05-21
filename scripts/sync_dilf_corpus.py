"""Resynchronise the local dilf corpus copies from a local dilf checkout.

dilf is the source of truth for the manuel markdown and the fixtures
Python module. Draught Master ships its own copies (so the FastAPI
backend can read them without a network dependency), and this script
keeps them aligned.

What it does
------------
1. Reads `docs/pre_process_corpus/manuel_debutant.md` and
   `docs/pre_process_corpus/fixtures_debutant.py` from the dilf checkout
   pointed at by ``--dilf <path>``.
2. Overwrites the local copies in draught-master with the dilf content.
3. Re-applies the pedagogy metadata comments (``<!-- pedagogy-motifs: ...
   -->`` and ``<!-- pedagogy-weaknesses: ... -->``) under each
   ``## Chapitre N`` header. These annotations are local-only — they
   drive the lesson↔motif↔weakness links in the frontend narrative cards
   and must survive a resync.
4. Reads the current dilf commit SHA via ``git -C <dilf> rev-parse HEAD``
   and writes it (plus today's date) into
   ``backend/manuels/CORPUS_MANIFEST.json``.

Usage
-----
    python scripts/sync_dilf_corpus.py --dilf /path/to/dilf

Add ``--dry-run`` to print the diff without writing anything. The script
is idempotent: re-running it without dilf changes is a no-op (or just a
manifest ``synced_at`` bump if forced).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple


# ── Pedagogy metadata mapping ──
# Slug-of-chapter → comment lines to insert just under the
# ``## Chapitre N — …`` header line. Keep the order
# (motifs before weaknesses) stable so diffs stay readable.
PEDAGOGY_BLOCKS: Dict[int, List[str]] = {
    2: ["<!-- pedagogy-motifs: prise_max_ratee -->"],
    4: ["<!-- pedagogy-motifs: envoi_a_dame, coup_turc -->"],
    5: ["<!-- pedagogy-motifs: envoi_a_dame -->"],
    6: ["<!-- pedagogy-weaknesses: isolated, backward -->"],
    7: [
        "<!-- pedagogy-motifs: sacrifice -->",
        "<!-- pedagogy-weaknesses: holes -->",
    ],
    8: [
        "<!-- pedagogy-motifs: sacrifice -->",
        "<!-- pedagogy-weaknesses: holes, outposts -->",
    ],
    9: ["<!-- pedagogy-motifs: coup_express -->"],
    13: ["<!-- pedagogy-motifs: coup_napoleon -->"],
    15: ["<!-- pedagogy-motifs: coup_de_talon -->"],
    16: ["<!-- pedagogy-motifs: coup_philippe -->"],
}

_CHAPTER_HEADER = re.compile(r"^## Chapitre (\d+)\s*[—–-]\s*(.+)$", re.MULTILINE)


def reapply_metadata(markdown: str) -> str:
    """Insert the per-chapter pedagogy comment blocks after each
    ``## Chapitre N — …`` header. Idempotent — if the comment lines
    are already present right under the header they are left intact
    (we never append duplicates)."""
    lines = markdown.split("\n")
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = _CHAPTER_HEADER.match(line)
        if m:
            chapter = int(m.group(1))
            wanted = PEDAGOGY_BLOCKS.get(chapter, [])
            # Skip past any existing pedagogy- comment lines so the
            # reinsertion replaces them rather than stacking.
            j = i + 1
            while j < len(lines) and lines[j].startswith("<!-- pedagogy-"):
                j += 1
            for tag in wanted:
                out.append(tag)
            i = j
            continue
        i += 1
    return "\n".join(out)


def git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def sync(dilf_root: Path, dm_root: Path, dry_run: bool) -> Tuple[bool, str]:
    md_src = dilf_root / "docs" / "pre_process_corpus" / "manuel_debutant.md"
    fx_src = dilf_root / "docs" / "pre_process_corpus" / "fixtures_debutant.py"
    md_dst = dm_root / "docs" / "manuels" / "debutant" / "manuel_debutant.md"
    fx_dst = dm_root / "backend" / "manuels" / "fixtures_debutant.py"
    manifest = dm_root / "backend" / "manuels" / "CORPUS_MANIFEST.json"

    for p in (md_src, fx_src):
        if not p.exists():
            return False, f"dilf source missing: {p}"

    md_new = reapply_metadata(md_src.read_text(encoding="utf-8"))
    fx_new = fx_src.read_text(encoding="utf-8")

    md_old = md_dst.read_text(encoding="utf-8") if md_dst.exists() else ""
    fx_old = fx_dst.read_text(encoding="utf-8") if fx_dst.exists() else ""

    md_changed = md_new != md_old
    fx_changed = fx_new != fx_old

    sha = git_head(dilf_root)
    today = date.today().isoformat()

    summary = (
        f"manuel: {'updated' if md_changed else 'unchanged'} | "
        f"fixtures: {'updated' if fx_changed else 'unchanged'} | "
        f"dilf={sha[:7]} synced={today}"
    )

    if dry_run:
        return True, "(dry-run) " + summary

    if md_changed:
        md_dst.write_text(md_new, encoding="utf-8")
    if fx_changed:
        fx_dst.write_text(fx_new, encoding="utf-8")

    manifest_data = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    manifest_data.update({
        "$comment": "Tracks which dilf revision the local corpus copy was synced from. Updated by scripts/sync_dilf_corpus.py. Read at backend startup to log the active corpus version. See backend/manuels/__init__.py.",
        "source": "https://github.com/jfrancoiscollin/dilf",
        "dilf_commit_sha": sha,
        "synced_at": today,
        "files": [
            {
                "local": "docs/manuels/debutant/manuel_debutant.md",
                "dilf": "docs/pre_process_corpus/manuel_debutant.md",
                "local_modifications": "pedagogy-motifs / pedagogy-weaknesses comment blocks under each chapter header (preserved on resync)",
            },
            {
                "local": "backend/manuels/fixtures_debutant.py",
                "dilf": "docs/pre_process_corpus/fixtures_debutant.py",
                "local_modifications": None,
            },
        ],
    })
    manifest.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return True, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dilf", required=True, type=Path, help="Path to a local dilf checkout")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dm_root = Path(__file__).resolve().parent.parent
    ok, message = sync(args.dilf.resolve(), dm_root, args.dry_run)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
