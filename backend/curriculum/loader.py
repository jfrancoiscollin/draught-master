"""Cached runtime accessor over ``curriculum_resolved.json``.

The resolved file is produced offline by ``build_curriculum.py``. This
module loads it once and exposes the tree plus per-module lookups, so the
API never touches the file layout.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

_RESOLVED_PATH = Path(__file__).resolve().parent / "curriculum_resolved.json"


@lru_cache(maxsize=1)
def _payload() -> dict[str, Any]:
    if not _RESOLVED_PATH.is_file():
        return {"levels": [], "modules": []}
    return json.loads(_RESOLVED_PATH.read_text())


def levels() -> list[dict[str, Any]]:
    return list(_payload().get("levels", []))


def modules() -> list[dict[str, Any]]:
    return list(_payload().get("modules", []))


def get_module(module_id: str) -> Optional[dict[str, Any]]:
    for m in _payload().get("modules", []):
        if m["id"] == module_id:
            return m
    return None


def all_exercise_refs() -> set[int]:
    """Every exercise DB id referenced anywhere in the curriculum.

    Used to compute progress: which attached exercises a user has solved.
    """
    refs: set[int] = set()
    for m in _payload().get("modules", []):
        for les in m["lessons"]:
            for item in les["items"]:
                if item["kind"] == "exercise":
                    refs.add(item["ref"])
    return refs


def module_exercise_refs(module_id: str) -> list[int]:
    m = get_module(module_id)
    if not m:
        return []
    refs: list[int] = []
    for les in m["lessons"]:
        for item in les["items"]:
            if item["kind"] == "exercise":
                refs.append(item["ref"])
    return refs
