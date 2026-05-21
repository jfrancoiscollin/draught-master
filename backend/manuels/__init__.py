"""Manuels pédagogiques préprocessés par Claude via dilf.

Voir `docs/manuels/<niveau>/manuel_<niveau>.md` pour la prose et le
README dilf `docs/pre_process_corpus/` pour le pipeline de production.

dilf est la source de vérité ; les copies locales (manuel markdown +
fixtures Python) sont versionnées via `CORPUS_MANIFEST.json`. À utiliser
au démarrage backend pour journaliser le SHA dilf actif, et par
`scripts/sync_dilf_corpus.py` pour resynchroniser tout en préservant les
annotations `<!-- pedagogy-* -->` locales du markdown.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_MANIFEST_PATH = Path(__file__).resolve().parent / "CORPUS_MANIFEST.json"


def load_corpus_manifest() -> Dict[str, Any]:
    """Return the local corpus manifest. Missing file → empty dict so
    a half-initialised checkout doesn't crash the backend."""
    if not _MANIFEST_PATH.exists():
        return {}
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def corpus_version_string() -> str:
    """One-line summary suitable for startup logs.

    Example: ``corpus dilf=cc99f7b synced=2026-05-21``. The SHA is
    truncated to 7 chars (git short form) — keep it greppable but
    don't drown the logs.
    """
    m = load_corpus_manifest()
    sha = m.get("dilf_commit_sha", "?")
    short = sha[:7] if sha and sha != "?" else "?"
    synced = m.get("synced_at", "?")
    return f"corpus dilf={short} synced={synced}"
