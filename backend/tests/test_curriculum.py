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
    # Every lesson is either a reading lesson (links a prose chapter) or
    # resolves to at least one content item (exercise/position/manual).
    for m in resolved["modules"]:
        assert m["lessons"]
        for les in m["lessons"]:
            assert les["n_items"] >= 1 or "chapter" in les, les["id"]


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
        if m["level"] != "debutant":
            continue  # debutant modules attach manuel_debutant exercises
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

    # Complete the first root module -> it becomes done and unlocks its
    # dependents. An exercise module completes by solving its exercises; a
    # reading module (Débutant Dubois track) by reading its chapters.
    root = roots[0]
    refs = loader.module_exercise_refs(root["id"])
    read = [les["chapter"] for les in (loader.get_module(root["id"]) or {}).get("lessons", [])
            if "chapter" in les]
    after = progress_payload(refs, read)
    by_id = {s["id"]: s for s in after["modules"]}
    assert by_id[root["id"]]["state"] == "done"
    dependents = [m for m in loader.modules() if root["id"] in m.get("prerequisites", [])]
    for d in dependents:
        assert by_id[d["id"]]["state"] != "locked"


def test_unlock_all_env_opens_every_module(monkeypatch):
    """With CURRICULUM_UNLOCK_ALL set, no module is ``locked`` even with
    unsolved prerequisites — the staging free-test escape hatch."""
    from curriculum import api as cur_api

    # Sanity: without the flag, a module with prerequisites is locked when
    # nothing is solved.
    monkeypatch.delenv("CURRICULUM_UNLOCK_ALL", raising=False)
    gated = cur_api.progress_payload([])
    assert any(s["state"] == "locked" for s in gated["modules"])
    assert cur_api.get_curriculum()["unlock_all"] is False

    monkeypatch.setenv("CURRICULUM_UNLOCK_ALL", "1")
    opened = cur_api.progress_payload([])
    assert all(s["state"] != "locked" for s in opened["modules"])
    assert cur_api.get_curriculum()["unlock_all"] is True


def test_debutant_level_reads_the_dubois_combinations_book():
    """The Débutant level is a reading track over the Dubois 'Apprentissage
    des combinaisons' book: every lesson links a real combinaisons chapter
    (ids 201-241), in book order, and all 41 chapters are covered."""
    from combinaisons_loader import combinaisons_chapters

    chapter_ids = {int(k) for k in combinaisons_chapters()}
    resolved = cur.build()
    linked = [
        les["chapter"]
        for m in resolved["modules"]
        if m["level"] == "debutant"
        for les in m["lessons"]
    ]
    assert linked, "no débutant reading lessons"
    assert all(c in chapter_ids for c in linked), linked
    # The whole book is exposed, in ascending order.
    assert set(linked) == chapter_ids
    assert linked == sorted(linked)


def test_intermediate_attaches_strategy_exercises_by_theme():
    """Intermediate lessons attach playable strategy exercises by theme
    (the exercise `hint`), and the resolved refs equal the DB ids the seed
    assigns so they deep-link into the solver."""
    from strategy.exercises_loader import (
        STRATEGY_ID_OFFSET,
        all_strategy_exercises,
    )

    expected = {
        STRATEGY_ID_OFFSET + 1 + i: ex["hint"]
        for i, ex in enumerate(all_strategy_exercises())
    }
    resolved = cur.build()
    # strategy concept modules only (the Dubois combination and sens-du-jeu
    # modules attach different corpora, covered by their own tests)
    inter = [
        m for m in resolved["modules"]
        if m["level"] == "intermediaire"
        and not m["id"].startswith(("int_comb_", "int_sdj_"))
    ]
    assert inter, "no intermediate strategy modules"
    seen = 0
    for m in inter:
        for les in m["lessons"]:
            for item in les["items"]:
                if item["kind"] != "exercise":
                    continue  # lessons also carry illustrative positions
                assert item["ref"] in expected, item["ref"]
                # the item's theme is the source exercise's hint
                assert item.get("theme") == expected[item["ref"]]
                seen += 1
    assert seen >= 100  # ~101 curated strategy exercises


def test_dubois_combinations_resolve_to_seed_ids():
    """The Dubois 'Apprendre les combinaisons' modules attach playable
    exercises whose refs equal the seed DB ids (offset 7000), so they
    deep-link into the solver."""
    from combinaisons_loader import (
        COMBINAISONS_ID_OFFSET,
        all_combinaisons_exercises,
    )

    expected = {
        COMBINAISONS_ID_OFFSET + 1 + i: ex["category"]
        for i, ex in enumerate(all_combinaisons_exercises())
    }
    resolved = cur.build()
    comb_modules = [
        m for m in resolved["modules"] if m["id"].startswith("int_comb_")
    ]
    assert len(comb_modules) == 4
    seen = 0
    for m in comb_modules:
        for les in m["lessons"]:
            for item in les["items"]:
                assert item["kind"] == "exercise"
                assert item["ref"] in expected, item["ref"]
                assert expected[item["ref"]] == item["category"]
                seen += 1
    assert seen == 408  # the whole Dubois corpus is curated in


def test_sens_du_jeu_resolves_to_seed_ids_with_prose():
    """The Dubois 'sens du jeu' modules attach exercises whose refs equal the
    seed DB ids (offset 8000) and every lesson links to a real prose chapter
    so 'Read the lesson' works."""
    from sens_du_jeu_loader import (
        SENS_DU_JEU_ID_OFFSET,
        all_sens_du_jeu_exercises,
        sens_du_jeu_chapters,
    )

    expected = {
        SENS_DU_JEU_ID_OFFSET + 1 + i: ex["category"]
        for i, ex in enumerate(all_sens_du_jeu_exercises())
    }
    chapters = set(int(k) for k in sens_du_jeu_chapters())
    resolved = cur.build()
    sdj = [m for m in resolved["modules"] if m["id"].startswith("int_sdj_")]
    assert len(sdj) == 4
    seen = 0
    for m in sdj:
        for les in m["lessons"]:
            assert les.get("chapter") in chapters, les["id"]
            for item in les["items"]:
                assert item["kind"] == "exercise"
                assert item["ref"] in expected, item["ref"]
                assert expected[item["ref"]] == item["category"]
                seen += 1
    assert seen == 72  # the whole sens du jeu corpus is curated in


def test_intermediate_lessons_carry_illustrative_positions():
    """Strategy concepts have no manual prose, so each intermediate lesson
    shows illustrative positions (capped) with a renderable FEN."""
    resolved = cur.build()
    inter = [m for m in resolved["modules"] if m["level"] == "intermediaire"]
    lessons_with_positions = 0
    for m in inter:
        for les in m["lessons"]:
            positions = [it for it in les["items"] if it["kind"] == "position"]
            assert len(positions) <= 6, (les["id"], len(positions))
            for p in positions:
                assert p.get("fen", "").startswith(("W:", "B:")), p
            if positions:
                lessons_with_positions += 1
    assert lessons_with_positions >= 10  # most concepts are illustrated


def test_lesson_chapter_refs_are_valid():
    """Every lesson that links to a manual chapter links to one that exists,
    so the 'Read the lesson' button always resolves to real prose (Dubois
    combinaisons 201-241, Dubois 'sens du jeu' 101-135, legacy débutant 1-16)."""
    from combinaisons_loader import combinaisons_chapters
    from manuels.prose_loader import load_debutant_chapters
    from sens_du_jeu_loader import sens_du_jeu_chapters

    valid = {int(k) for k in load_debutant_chapters().keys()}
    valid |= {int(k) for k in sens_du_jeu_chapters().keys()}
    valid |= {int(k) for k in combinaisons_chapters().keys()}
    resolved = cur.build()
    for m in resolved["modules"]:
        for les in m["lessons"]:
            if "chapter" in les:
                assert les["chapter"] in valid, (les["id"], les["chapter"])


def test_strategy_reading_module_links_every_manual():
    """The 'grands manuels stratégiques' module turns each exploited corpus
    into a prose reading lesson: one ``manual`` item per source, whose ref is
    a real strategy source so the learning path deep-links into the manual
    view."""
    from curriculum.build_curriculum import _strategy_sources

    known = _strategy_sources()
    resolved = cur.build()
    mod = next(
        (m for m in resolved["modules"] if m["id"] == "int_manuels_strategiques"),
        None,
    )
    assert mod is not None, "strategy reading module missing"
    assert mod["n_manuals"] == len(mod["lessons"]) >= 4
    seen_sources = set()
    for les in mod["lessons"]:
        manuals = [it for it in les["items"] if it["kind"] == "manual"]
        assert len(manuals) == 1, les["id"]
        src = manuals[0]["source"]
        assert src in known, src
        assert manuals[0]["ref"] == src
        seen_sources.add(src)
    # The prose-rich system manuals are surfaced as reading lessons. Goedemoed
    # / Goedemoed3 are exercise collections (too little prose) and deliberately
    # excluded from the reading track.
    assert seen_sources == {"SIJBRANDS", "ROOZENBURG", "KELLER", "SPRINGER"}


def test_unknown_manual_source_is_rejected():
    spine = {
        "version": 1,
        "levels": [{"id": "x", "title": "X", "order": 1}],
        "modules": [{
            "id": "a", "level": "x", "order": 1, "prerequisites": [],
            "lessons": [{
                "id": "a_l1", "title": "L",
                "attach": {"manual": {"source": "NOT_A_SOURCE"}},
            }],
        }],
    }
    # Resolution-time guard (like an unknown exercises book_id): raises a
    # plain ValueError with a clear message rather than the aggregated
    # CurriculumError used for spine-level validation.
    with pytest.raises(ValueError, match="unknown source in attach.manual"):
        cur._validate_and_resolve(spine)


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
    with pytest.raises(cur.CurriculumError, match="unknown manual chapter"):
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
