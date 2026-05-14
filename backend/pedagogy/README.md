# `backend/pedagogy/`

Pedagogy layer for draught-master. Consumes the deterministic detectors
and explanation pipeline shipped in
[dilf](https://github.com/jfrancoiscollin/dilf) and exposes them through
SQLite persistence + a FastAPI router. Closes spec PRs 7, 8, 13.

## Layout

```
pedagogy/
├── api.py                 # /api/pedagogy/* router (PR 8)
├── engine_adapter.py      # game_engine ↔ pedagogy.game bridge
├── models.py              # Pydantic request/response schemas
├── motif_descriptions.py  # human-readable copy per motif (FR/EN)
├── storage.py             # async aiosqlite CRUD on the 3 pedagogy tables
└── scripts/
    └── tag_existing_exercises.py   # one-shot exercise tagger (PR 13)
```

DB schema lives in `backend/db/schema.py` (`init_db()`): tables
`move_verdicts`, `pedagogy_explanations`, `exercise_tags`, plus the
migrations that add `user_side` / `opening_name` / `status` to `games`.

## Adding a motif detector

Detectors live in dilf, not here. The flow is:

1. Implement the new detector in `pedagogy/motifs/<name>.py` in the dilf
   repo, register it in `pedagogy/motifs/__init__.py:ALL_DETECTORS`,
   ship a PR there.
2. Bump the dilf pin in `backend/requirements.txt` once the detector
   merges.
3. Add a French + English description in `motif_descriptions.py` here so
   `/api/pedagogy/motifs/{slug}` returns prose for it.
4. Re-run `python -m backend.pedagogy.scripts.tag_existing_exercises`
   in production to backfill `exercise_tags` rows.

## Adding an explanation template

Templates also live in dilf (`pedagogy/explanations/templates_fr.py`
and `templates_en.py`). Add the `(motif, role, verdict)` entry in both
modules, ship as a single PR in dilf, then bump the pin here. The
template mode of `/api/pedagogy/explain-move` will pick them up
automatically — no schema change.

## Running the tests

```bash
cd backend
pytest tests/test_pedagogy_storage.py tests/test_pedagogy_api.py \
       tests/test_tag_existing_exercises.py -v
```

## Known gaps

- `tag_existing_exercises.py` parses move notations through a thin
  fallback (`_parse_move_fallback`) that does **not** infer captured
  pieces. As a result, capture-based detectors (coup_royal,
  prise_max_ratee, …) won't fire on exercises today. Tracked
  separately; will be closed when dilf ships a full
  `parse_move_notation(state, notation)` helper.
- `/api/pedagogy/explain-move?mode=template` uses an in-memory rate
  limiter (60/min per IP) per the existing project pattern. For
  horizontal scale-out this needs to move to a shared cache.
