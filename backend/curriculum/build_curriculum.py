"""Validate the curriculum spine and resolve every lesson's `attach` rules
against the real content, materializing a flat index for the API.

`curriculum.json` is the hand-authored map (levels -> modules -> lessons).
This script:

1. **Validates** the spine — unique ids, prerequisites resolve and form a
   DAG (no cycles), referenced levels exist, every lesson resolves to at
   least one content item.
2. **Resolves** each lesson's `attach` rules into concrete content
   references (exercise DB ids, strategy diagram ids, tip ids), reusing the
   exact same id assignment the DB seed uses so the API can deep-link.
3. **Materializes** `curriculum_resolved.json` — the spine plus, per lesson,
   the resolved item ids and counts. Re-runnable and deterministic; a
   freshness test guards it.

Run from `backend/`::

    python -m curriculum.build_curriculum            # validate + write
    python -m curriculum.build_curriculum --check    # validate only (CI)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent
_SPINE_PATH = _DIR / "curriculum.json"
_OUT_PATH = _DIR / "curriculum_resolved.json"


# ── content resolvers ──────────────────────────────────────────────────────
#
# Each returns the list of content items matching a lesson's `attach` block.
# Items are dicts with a stable `ref` the frontend can deep-link to.


def _debutant_exercise_rows() -> list[dict[str, Any]]:
    """manuel_debutant exercises with the DB id the seed will assign.

    Mirrors db/schema.py: sequential ids from DEBUTANT_ID_OFFSET + 1 in the
    loader's deterministic (lexicographic) order.
    """
    from manuels.loader import DEBUTANT_ID_OFFSET, all_debutant_exercises

    rows = []
    for i, ex in enumerate(all_debutant_exercises(), start=DEBUTANT_ID_OFFSET + 1):
        rows.append({**ex, "_db_id": i})
    return rows


def _strategy_exercise_rows() -> list[dict[str, Any]]:
    """Strategy exercises with the DB id the seed will assign."""
    from strategy.exercises_loader import (
        STRATEGY_ID_OFFSET,
        all_strategy_exercises,
    )

    rows = []
    for i, ex in enumerate(all_strategy_exercises(), start=STRATEGY_ID_OFFSET + 1):
        rows.append({**ex, "_db_id": i})
    return rows


def _resolve_exercises(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve an ``attach.exercises`` block to exercise references.

    Supported filters: ``book_id`` (required), ``categories`` (list),
    ``difficulty`` (int or list), ``min_difficulty``/``max_difficulty``.
    """
    book = spec["book_id"]
    if book == "manuel_debutant":
        rows = _debutant_exercise_rows()
    elif book.startswith("manuel_") or book == "strategy":
        rows = [r for r in _strategy_exercise_rows()]
    else:
        raise ValueError(f"unknown book_id in attach.exercises: {book!r}")

    cats = set(spec.get("categories") or [])
    diff = spec.get("difficulty")
    diffs = {diff} if isinstance(diff, int) else set(diff or [])
    dmin = spec.get("min_difficulty")
    dmax = spec.get("max_difficulty")

    out = []
    for r in rows:
        if book != "manuel_debutant" and r.get("book_id") != book:
            continue
        if cats and r.get("category") not in cats:
            continue
        if diffs and r.get("difficulty") not in diffs:
            continue
        if dmin is not None and r.get("difficulty", 0) < dmin:
            continue
        if dmax is not None and r.get("difficulty", 99) > dmax:
            continue
        out.append({
            "kind": "exercise",
            "ref": r["_db_id"],
            "name": r["name"],
            "difficulty": r.get("difficulty"),
            "category": r.get("category"),
        })
    return out


def _resolve_positions(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve an ``attach.positions`` block to strategy position refs.

    Filters: ``source`` (str or list), ``themes`` (list), ``has_capture``
    (bool), ``min_pieces``/``max_pieces`` (total men on board).
    """
    from strategy import position_library as lib

    srcs = spec.get("source")
    srcs = {srcs} if isinstance(srcs, str) else set(srcs or [])
    themes = set(spec.get("themes") or [])
    has_cap = spec.get("has_capture")
    pmin = spec.get("min_pieces")
    pmax = spec.get("max_pieces")

    out = []
    for p in lib.valid_positions():
        if srcs and p["source"] not in srcs:
            continue
        if themes and p.get("theme") not in themes:
            continue
        if has_cap is not None and bool(p.get("has_capture")) != has_cap:
            continue
        total = p.get("n_white", 0) + p.get("n_black", 0)
        if pmin is not None and total < pmin:
            continue
        if pmax is not None and total > pmax:
            continue
        out.append({
            "kind": "position",
            "ref": p["id"],
            "fen": p["fen"],
            "theme": p.get("theme"),
        })
    return out


def _resolve_tips(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve an ``attach.tips`` block to knowledge-base tip refs.

    Filters: ``ids`` (list of tip ids), ``phase`` (str).
    """
    kb = json.loads((Path(__file__).resolve().parent.parent / "knowledge_base.json").read_text())
    ids = set(spec.get("ids") or [])
    phase = spec.get("phase")
    out = []
    for t in kb["tips"]:
        if ids and t["id"] not in ids:
            continue
        if phase and phase not in t.get("phase", []):
            continue
        out.append({
            "kind": "tip",
            "ref": t["id"],
            "concept": t.get("fr", {}).get("concept", t["id"]),
        })
    return out


def _debutant_chapter_ids() -> set[int]:
    """Chapter numbers that have manual prose (lessons may link to them)."""
    from manuels.prose_loader import load_debutant_chapters

    return {int(k) for k in load_debutant_chapters().keys()}


def _resolve_lesson(lesson: dict[str, Any]) -> list[dict[str, Any]]:
    attach = lesson.get("attach", {})
    items: list[dict[str, Any]] = []
    if "exercises" in attach:
        items += _resolve_exercises(attach["exercises"])
    if "positions" in attach:
        items += _resolve_positions(attach["positions"])
    if "tips" in attach:
        items += _resolve_tips(attach["tips"])
    return items


# ── validation ─────────────────────────────────────────────────────────────


class CurriculumError(ValueError):
    pass


def _validate_and_resolve(spine: dict[str, Any]) -> dict[str, Any]:
    level_ids = {lvl["id"] for lvl in spine["levels"]}
    module_ids: set[str] = set()
    lesson_ids: set[str] = set()
    errors: list[str] = []

    resolved_modules: list[dict[str, Any]] = []
    for m in spine["modules"]:
        if m["id"] in module_ids:
            errors.append(f"duplicate module id: {m['id']}")
        module_ids.add(m["id"])
        if m["level"] not in level_ids:
            errors.append(f"module {m['id']} references unknown level {m['level']!r}")

        resolved_lessons = []
        for les in m.get("lessons", []):
            if les["id"] in lesson_ids:
                errors.append(f"duplicate lesson id: {les['id']}")
            lesson_ids.add(les["id"])
            if "chapter" in les and les["chapter"] not in _debutant_chapter_ids():
                errors.append(
                    f"lesson {les['id']} references unknown debutant chapter {les['chapter']}"
                )
            items = _resolve_lesson(les)
            if not items:
                errors.append(f"lesson {les['id']} resolves to 0 content items")
            resolved_lessons.append({
                **{k: v for k, v in les.items() if k != "attach"},
                "items": items,
                "n_items": len(items),
            })
        resolved_modules.append({**m, "lessons": resolved_lessons,
                                 "n_items": sum(l["n_items"] for l in resolved_lessons)})

    # prerequisites resolve + acyclic
    for m in spine["modules"]:
        for pre in m.get("prerequisites", []):
            if pre not in module_ids:
                errors.append(f"module {m['id']} has unknown prerequisite {pre!r}")
    _check_acyclic(spine["modules"], errors)

    if errors:
        raise CurriculumError("curriculum validation failed:\n  - " + "\n  - ".join(errors))

    return {
        "$comment": "Generated by curriculum/build_curriculum.py — do not edit by hand.",
        "version": spine.get("version", 1),
        "levels": spine["levels"],
        "modules": resolved_modules,
    }


def _check_acyclic(modules: list[dict[str, Any]], errors: list[str]) -> None:
    graph = {m["id"]: list(m.get("prerequisites", [])) for m in modules}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}

    def visit(n: str, stack: list[str]) -> None:
        color[n] = GRAY
        for dep in graph.get(n, []):
            if dep not in color:
                continue
            if color[dep] == GRAY:
                errors.append(f"prerequisite cycle: {' -> '.join(stack + [dep])}")
                return
            if color[dep] == WHITE:
                visit(dep, stack + [dep])
        color[n] = BLACK

    for n in graph:
        if color[n] == WHITE:
            visit(n, [n])


# ── entrypoint ─────────────────────────────────────────────────────────────


def build() -> dict[str, Any]:
    spine = json.loads(_SPINE_PATH.read_text())
    return _validate_and_resolve(spine)


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    resolved = build()
    n_mod = len(resolved["modules"])
    n_les = sum(len(m["lessons"]) for m in resolved["modules"])
    n_items = sum(m["n_items"] for m in resolved["modules"])
    if check_only:
        print(f"[ok] curriculum valid: {n_mod} modules, {n_les} lessons, {n_items} items")
        return 0
    _OUT_PATH.write_text(json.dumps(resolved, indent=2, ensure_ascii=False) + "\n")
    print(f"[ok] {n_mod} modules, {n_les} lessons, {n_items} items → {_OUT_PATH}")
    for m in resolved["modules"]:
        print(f"     [{m['level']}] {m['order']}. {m['title']:42s} "
              f"{len(m['lessons'])} leçons, {m['n_items']:3d} items")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
