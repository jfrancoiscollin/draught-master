"""FastAPI router for /api/curriculum/*.

Serves the curated learning map (levels -> modules -> lessons) and, for an
authenticated user, a progress overlay derived from the existing
``user_exercise_solved`` tracking — no new tables. A module's state is
``locked`` (prerequisites unmet), ``available``, ``in_progress`` or
``done``, computed from the share of its attached exercises the user has
solved.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException

from . import loader

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])


def _unlock_all() -> bool:
    """Staging escape hatch: when ``CURRICULUM_UNLOCK_ALL`` is truthy, every
    module is reachable regardless of prerequisites, so the path can be tested
    freely in any order. Off by default — production keeps the progression
    gating. Set it only on the staging service."""
    return os.environ.get("CURRICULUM_UNLOCK_ALL", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


@router.get("")
def get_curriculum() -> dict[str, Any]:
    """The full map: levels + module summaries (no resolved item lists)."""
    mods = []
    for m in loader.modules():
        mods.append({
            "id": m["id"],
            "level": m["level"],
            "order": m["order"],
            "title": m["title"],
            "subtitle": m.get("subtitle"),
            "goal": m.get("goal"),
            "prerequisites": m.get("prerequisites", []),
            "n_lessons": len(m["lessons"]),
            "n_items": m.get("n_items", 0),
            "n_exercises": m.get("n_exercises", 0),
            "n_positions": m.get("n_positions", 0),
            "n_manuals": m.get("n_manuals", 0),
        })
    return {"levels": loader.levels(), "modules": mods, "unlock_all": _unlock_all()}


@router.get("/module/{module_id}")
def get_module(module_id: str) -> dict[str, Any]:
    """One module with its lessons and resolved content items."""
    m = loader.get_module(module_id)
    if not m:
        raise HTTPException(status_code=404, detail=f"unknown module {module_id!r}")
    return m


def _module_state(
    module: dict[str, Any],
    solved: set[int],
    done_modules: set[str],
) -> dict[str, Any]:
    refs = [
        item["ref"]
        for les in module["lessons"]
        for item in les["items"]
        if item["kind"] == "exercise"
    ]
    n_total = len(refs)
    n_solved = sum(1 for r in refs if r in solved)
    prereqs = module.get("prerequisites", [])
    unlocked = _unlock_all() or all(p in done_modules for p in prereqs)
    if not unlocked:
        state = "locked"
    elif n_total and n_solved >= n_total:
        state = "done"
    elif n_solved > 0:
        state = "in_progress"
    else:
        state = "available"
    return {
        "id": module["id"],
        "state": state,
        "n_solved": n_solved,
        "n_total": n_total,
    }


def progress_payload(solved_ids: list[int]) -> dict[str, Any]:
    """Pure function (testable without a DB): module states + next step.

    A module counts as ``done`` for unlocking purposes when all its
    attached exercises are solved. Iterates in declared order so a module's
    done-state is known before its dependents are evaluated.
    """
    solved = set(solved_ids)
    done_modules: set[str] = set()
    states: list[dict[str, Any]] = []
    for m in loader.modules():
        st = _module_state(m, solved, done_modules)
        if st["state"] == "done":
            done_modules.add(m["id"])
        states.append(st)

    next_module = next(
        (s["id"] for s in states if s["state"] in ("available", "in_progress")),
        None,
    )
    return {"modules": states, "next_module": next_module}
