# draught-master <-> dilf interop contract

This file mirrors `INTEROP.md` at the root of
[`jfrancoiscollin/dilf`](https://github.com/jfrancoiscollin/dilf). If
they diverge, **dilf is the source of truth**.

## Pin

`backend/requirements.txt` pins dilf via a specific commit SHA tarball:

```text
https://github.com/jfrancoiscollin/dilf/archive/<sha>.tar.gz
```

Current pin: `9fccc1f1a906c75876ce8c4099c053b38ef17d1b` (on dilf
`develop`). Pinning to a SHA — rather than to a branch tarball
(`refs/heads/main.tar.gz`) — is deliberate: it makes every dilf bump
an explicit commit in this repo, and the bump only happens when we
choose to consume new upstream work. dilf changes only reach
production when `backend/requirements.txt` is updated and merged.

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

When dilf needs an API-breaking change:

1. **First** — open a PR on this repo that:
   - Updates the consumer code to the new dilf API.
   - Updates the SHA in `backend/requirements.txt` to the dilf PR's
     head commit.
   - Stays draft until the dilf PR is ready.
2. **Second** — once the dilf PR merges, push a commit on this PR
   updating the SHA to the actual merge commit. Mark ready-for-review
   and merge here.

Until step 2 lands, dilf's downstream-compat CI will go red on the
dilf side — that's the loud signal that prevents an out-of-coordination
merge on dilf.

## Capture-aware tagging — historical gap, now closed

For a window after the initial integration, `tag_existing_exercises.py`
could only tag non-capture moves: dilf hadn't shipped a
notation-aware parser yet, and the fallback (`_parse_move_fallback`)
returned `Move(captures=())`. Capture-based detectors silently
skipped every exercise.

This is fixed now:

- `pedagogy.notation.dubois.parse_move_notation` (dilf,
  2026-05-15) reconstructs the full capture path from short or full
  notation against the position. The script imports it directly
  (`tag_existing_exercises.py:66`) and the `_parse_move_fallback`
  branch is now dead-on-paper safety only.
- `engine.apply_move(state, move)` resolves via
  `GameEngineAdapter`, which validates the move against the engine's
  legal-moves list before applying.

End-to-end coverage lives in
`backend/tests/test_tag_existing_exercises_real.py` — passing real
Dubois fixtures through `_detect_tags` and asserting the expected
capture-based motifs fire.

## Motif descriptions

The 18 dilf detectors (6 P1 + 4 P2 + 4 P3 + 4 generic combinaisons)
each emit a `MotifMatch` with a `motif` slug. The slugs are surfaced
in the UI as clickable badges in `PedagogyPanel`; clicking opens a
drill page that hits `/api/pedagogy/motifs/{slug}` and reads from
`backend/pedagogy/motif_descriptions.py`.

**`motif_descriptions.MOTIFS` covers all 18 slugs dilf emits**:

- All 6 P1 motifs.
- All 4 P2 motifs.
- All 4 P3 motifs (`coup_napoleon`, `coup_manoury`, `coup_enfilade`,
  `coup_du_bruleur`).
- The 4 generic combinaisons (`combinaison_2/3/4/5_temps`).

Each entry has `name_fr`, `name_en`, `description_fr`,
`description_en`. The `/api/pedagogy/motifs/{slug}` endpoint resolves
for every slug, no more 404 from clicking a badge in PedagogyPanel.

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
