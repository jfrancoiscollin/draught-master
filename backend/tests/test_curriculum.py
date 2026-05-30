"""Tests for the curriculum spine: validity, attachment resolution, and a
freshness check that the committed resolved file matches a rebuild.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from curriculum import build_curriculum as cur


def test_spine_validates_and_resolves():
    resolved = cur.build()
    assert resolved["modules"]
    # Every lesson resolves to at least one content item (else build raises).
    for m in resolved["modules"]:
        assert m["lessons"]
        for les in m["lessons"]:
            assert les["n_items"] >= 1, les["id"]


def test_ids_unique_and_prerequisites_resolve():
    spine = json.loads(cur._SPINE_PATH.read_text())
    mod_ids = [m["id"] for m in spine["modules"]]
    assert len(mod_ids) == len(set(mod_ids))
    level_ids = {l["id"] for l in spine["levels"]}
    for m in spine["modules"]:
        assert m["level"] in level_ids
        for pre in m.get("prerequisites", []):
            assert pre in set(mod_ids), f"{m['id']} -> {pre}"


def test_prerequisites_are_acyclic():
    # A deliberately cyclic spine must be rejected.
    spine = {
        "version": 1,
        "levels": [{"id": "x", "title": "X", "order": 1}],
        "modules": [
            {"id": "a", "level": "x", "order": 1, "prerequisites": ["b"], "lessons": []},
            {"id": "b", "level": "x", "order": 2, "prerequisites": ["a"], "lessons": []},
        ],
    }
    with pytest.raises(cur.CurriculumError, match="cycle"):
        cur._validate_and_resolve(spine)


def test_attached_exercise_ids_match_db_seed():
    """Resolved exercise refs must equal the DB ids the seed assigns, so the
    frontend can deep-link a curriculum item straight to its exercise row."""
    from manuels.loader import DEBUTANT_ID_OFFSET, all_debutant_exercises

    expected = {
        DEBUTANT_ID_OFFSET + 1 + i: ex["category"]
        for i, ex in enumerate(all_debutant_exercises())
    }
    resolved = cur.build()
    for m in resolved["modules"]:
        for les in m["lessons"]:
            for item in les["items"]:
                if item["kind"] != "exercise":
                    continue
                assert item["ref"] in expected, item["ref"]
                assert expected[item["ref"]] == item["category"]


def test_api_tree_and_module_detail():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from curriculum.api import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    r = client.get("/api/curriculum")
    assert r.status_code == 200
    body = r.json()
    assert body["levels"] and body["modules"]
    first = body["modules"][0]
    assert first["goal"] and first["title"]

    mid = first["id"]
    r2 = client.get(f"/api/curriculum/module/{mid}")
    assert r2.status_code == 200
    assert r2.json()["lessons"]

    assert client.get("/api/curriculum/module/nope").status_code == 404


def test_progress_unlocks_in_order():
    from curriculum import loader
    from curriculum.api import progress_payload

    # Nothing solved: first module available, rest with prereqs locked.
    empty = progress_payload([])
    by_id = {s["id"]: s for s in empty["modules"]}
    roots = [m for m in loader.modules() if not m.get("prerequisites")]
    for m in roots:
        assert by_id[m["id"]]["state"] in ("available", "in_progress")
    assert empty["next_module"] is not None

    # Solve every exercise of the first root module -> it becomes done and
    # unlocks its dependents.
    root = roots[0]
    refs = loader.module_exercise_refs(root["id"])
    after = progress_payload(refs)
    by_id = {s["id"]: s for s in after["modules"]}
    assert by_id[root["id"]]["state"] == "done"
    dependents = [m for m in loader.modules() if root["id"] in m.get("prerequisites", [])]
    for d in dependents:
        assert by_id[d["id"]]["state"] != "locked"


def test_lesson_chapter_refs_are_valid():
    """Every lesson that links to a manual chapter links to one that exists,
    so the 'Read the lesson' button always resolves to real prose."""
    from manuels.prose_loader import load_debutant_chapters

    valid = {int(k) for k in load_debutant_chapters().keys()}
    resolved = cur.build()
    for m in resolved["modules"]:
        for les in m["lessons"]:
            if "chapter" in les:
                assert les["chapter"] in valid, (les["id"], les["chapter"])


def test_unknown_chapter_is_rejected():
    spine = {
        "version": 1,
        "levels": [{"id": "x", "title": "X", "order": 1}],
        "modules": [{
            "id": "a", "level": "x", "order": 1, "prerequisites": [],
            "lessons": [{
                "id": "a_l1", "title": "L", "chapter": 999,
                "attach": {"exercises": {"book_id": "manuel_debutant",
                                          "categories": ["regle_capture"]}},
            }],
        }],
    }
    with pytest.raises(cur.CurriculumError, match="unknown debutant chapter"):
        cur._validate_and_resolve(spine)


def test_committed_resolved_is_fresh():
    if not cur._OUT_PATH.is_file():
        pytest.skip("curriculum_resolved.json not built yet")
    rebuilt = cur.build()
    committed = json.loads(cur._OUT_PATH.read_text())
    assert rebuilt["modules"] == committed["modules"], (
        "curriculum_resolved.json is stale — re-run "
        "`python -m curriculum.build_curriculum`"
    )
