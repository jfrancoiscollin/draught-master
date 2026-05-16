# draught-master <-> dilf interop contract

This file mirrors `INTEROP.md` at the root of
[`jfrancoiscollin/dilf`](https://github.com/jfrancoiscollin/dilf). If
they diverge, **dilf is the source of truth**.

## Pin

`backend/requirements.txt` pins dilf via the main-branch tarball:

```text
https://github.com/jfrancoiscollin/dilf/archive/refs/heads/main.tar.gz
```

i.e. every dilf merge to `main` is picked up by the next
draught-master deploy. There is no version locking.

For a coordinated bump (during a breaking change), replace the URL
with a specific commit SHA:

```text
https://github.com/jfrancoiscollin/dilf/archive/<sha>.tar.gz
```

The CI workflow `.github/workflows/dilf-compat.yml` installs whatever
the pin resolves to and runs `backend/tests/test_dilf_imports.py` as
a smoke test.

## Symbols this repo imports from dilf

The full list lives in dilf's `INTEROP.md`. The smoke test
`backend/tests/test_dilf_imports.py` exercises every one of them; if
something disappears upstream, that test goes red **before** the
deploy.

A quick map of where dilf is consumed here:

| Local file | dilf symbols used |
|---|---|
| `backend/pedagogy/storage.py` | `pedagogy.types.{Features, GameAnalysis, MotifMatch, MoveVerdict, Phase, Verdict}` |
| `backend/pedagogy/api.py` | `pedagogy.explanations.explain_verdict`, `pedagogy.profile.aggregator.aggregate_user_profile`, `pedagogy.profile.recommender.recommend_exercises`, `pedagogy.types.{GameAnalysis, UserProfile}`, `pedagogy.verdicts.assembler.assemble_verdict` |
| `backend/pedagogy/engine_adapter.py` | `pedagogy.game.{GameState, Move}`, `pedagogy.protocols.EngineProtocol` |
| `backend/pedagogy/scripts/tag_existing_exercises.py` | `pedagogy.game.{parse_fen, Move}`, `pedagogy.motifs.ALL_DETECTORS` (+ optional `pedagogy.game.{apply_move, parse_move_notation}` via try/except — see below) |
| `backend/main.py` | `pedagogy.api.router`, `pedagogy.explanations.book_rag.BookRAG.from_directory`, `pedagogy.scripts.tag_existing_exercises._run` |

## Two-step dance for breaking changes

Because the pin tracks dilf `main`, **a breaking change in dilf will
break this repo's next deploy**. To coordinate cleanly:

1. **First** — open a draft PR here that:
   - Updates the consumer code to the new dilf API.
   - Replaces the `main` tarball in `backend/requirements.txt` with a
     specific dilf commit SHA (the SHA the dilf PR sits on).
2. **Second** — once the dilf PR merges, push a commit on this PR
   that flips the pin back to the `main` tarball (or to the actual
   merge SHA if you want to be extra paranoid). Mark
   ready-for-review and merge.

Until step 2 lands here, dilf's downstream-compat CI will go red on
the dilf side — that's the loud signal that prevents an
out-of-coordination merge on dilf.

## Currently-missing helpers (graceful fallback)

`backend/pedagogy/scripts/tag_existing_exercises.py` calls
`pedagogy.game.apply_move` and `pedagogy.game.parse_move_notation`
inside a `try/except ImportError`. Neither exists on dilf today, so
the fallback runs:

- `_parse_move_fallback` parses the move string but leaves
  `captures=()` empty.
- Capture-based detectors (`coup_royal`, `prise_max_ratee`,
  `coup_express`, …) therefore **never fire** on existing exercises.

Tracking: this gap is non-breaking from a typing perspective (the
imports are guarded). It will close when dilf ships those two helpers
(dilf ROADMAP.md Tier 4). When that happens, no draught-master change
is required — the next deploy auto-picks up the helpers and the
detectors start firing on the next `tag_existing_exercises` run.

## CI enforcement

Two workflows protect this contract:

- **draught-master** `.github/workflows/dilf-compat.yml` — on every
  push and PR, installs the dilf pin from `backend/requirements.txt`
  and runs `backend/tests/test_dilf_imports.py`. Failure blocks the
  PR.
- **dilf** `.github/workflows/downstream-compat.yml` — on every dilf
  push and PR, clones this repo's `develop` and runs
  `backend/tests/test_pedagogy_*.py` against the candidate dilf ref.
  Failure blocks the dilf PR.

Locally:

```bash
pytest backend/tests/test_dilf_imports.py     # validates the pin
pytest backend/tests/test_pedagogy_storage.py # validates the consumer code
```

## Where to find what

- This file: how this repo consumes dilf.
- dilf's `INTEROP.md` (root): the actual contract, source of truth.
- `backend/tests/test_dilf_imports.py`: machine-enforced smoke test
  for every dilf symbol this repo uses.
- `.github/workflows/dilf-compat.yml`: CI gate on every PR.
- `.claude/settings.json` SessionStart hook: reminds the dev about
  the contract and currently-installed dilf SHA at session start.
- `backend/pedagogy/README.md`: how to add a motif detector / template
  (touches both repos).
