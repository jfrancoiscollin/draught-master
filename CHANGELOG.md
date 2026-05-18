# Changelog

All notable user-visible and contract-affecting changes to
draught-master. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); draught-master
does not yet publish numbered versions, so entries are grouped by date
and reference the commit / PR that landed them. dilf changes consumed
through `backend/requirements.txt` are noted under "dilf bump"; for the
upstream changelog see
[`jfrancoiscollin/dilf` CHANGELOG.md](https://github.com/jfrancoiscollin/dilf/blob/develop/CHANGELOG.md).

## Unreleased

### Added

- **PedagogyPanel ↔ board two-way binding** (commit `6005ac5`).
  Verdict rows in the post-game analysis are now clickable to jump the
  board to that half-move. Conversely, navigating the board with the
  under-board arrows highlights the matching verdict row (amber
  background, bold notation) and scrolls it into view via
  `scrollIntoView({ block: 'nearest' })`. The expand chevron is a
  separate small button — clicking it only toggles the explanation,
  it doesn't move the board.
- **`combinaison_2/3/4/5_temps` motif entries** in
  `backend/pedagogy/motif_descriptions.py` (commit `f3438dd`). 15
  motifs total — the four generic-combinaison slugs now resolve at
  `/api/pedagogy/motifs/{slug}` instead of 404'ing, so clicking the
  badge in PedagogyPanel opens the drill page.

### Changed

- **dilf bump** `635d3c1` → `9fccc1f` (commit `f3438dd`,
  `backend/requirements.txt`). Brings the FMJD prise-max relaxation
  in `_walk_forced_chain` — combinations now fire on real games where
  the defender has multiple tied max-length captures.

## 2026-05-16 — Lidraughts import + bulk analysis + dilf pin moves

### Added

- **Bulk dilf analyse with cache invalidation** (PR #70). Motifs and
  Weakness panels refresh after a bulk analyse run.
- **dilf analysis lookback ordering by `date`** (PR #71). Replaces
  rowid-based ordering so re-imported games surface in the right slot.
- **`/analyze-game` PV extraction + persist failure traceback** (PR #68,
  commit `ef00447`). The Scan PV is threaded through to
  `assemble_verdict` (which feeds the dilf detectors). Persistence
  failures now log the full traceback so silent verdict drops don't go
  unnoticed.
- **Default-open "Détail diagnostic"** on the Profil tab (PR #69) +
  instrumentation of analyze-game motif counts in logs.

### Changed

- dilf pin rolled back to `191f69a` then re-pinned to `635d3c1` to
  re-enable the four `combinaison_N_temps` detectors after the
  intermediate rollback (PRs #54, #55, #72).

## 2026-05-15 — Brand pass + product polish

### Added

- **New cream/black logo and harmonized accent palette** (PR #57),
  canonical Draught Master SVG wordmark (PR #59), unified header
  wordmark (PR #62), home-icon illustrations (PR #63), home tile
  reorganisation with Profil first (PR #64), Analyser submenu split
  (PR #65), home-screen wordmark clickability (PR #66), login-page
  wordmark (PR #67).
- **Apprendre tab — "Motifs détectables" catalog** (PR #49) listing
  the detectable motifs alongside the Manuel Débutant.
- **Profil tab** — stats card, Lidraughts import, bulk dilf/Scan
  analyse buttons, accuracy badges (PR #27). "↺ Réinitialiser les
  analyses" button (PR #44).
- **`/api/pedagogy/profile/me/motif-debug`** diagnostic endpoint for
  empty "Points faibles" troubleshooting (PR #39).

### Fixed

- WeaknessPanel surfaces real error causes from FastAPI 422 detail
  arrays instead of generic empty states (PRs #35, #36).
- Route order fix on `/api/pedagogy/profile/me` (was 422'ing because
  `{user_id}` matched first) (PR #37).
- Edge/Chromium SVG rendering — unique `defs` IDs per piece (PR #28).
- `/analyze-game` fits under Railway's 30s proxy timeout (PR #43).

## 2026-05-14 — dilf integration baseline

### Added

- **dilf consumed via Python package pin** in `backend/requirements.txt`,
  installed during Railway deploy (PR #27, commit `a83d5f5`).
- **Pedagogy storage layer** — `move_verdicts`, `pedagogy_explanations`,
  `exercise_tags` tables in `backend/db/schema.py`; idempotent migration
  on startup.
- **Pedagogy API router** under `/api/pedagogy/*`: `analyze-game`,
  `move-verdict/{game}/{move}`, `explain-move`, `profile/{id}`,
  `profile/me`, `profile/me/recommendations`, `motifs/{slug}`,
  `import-lidraughts`.
- **`tag_existing_exercises.py`** — runs on app startup (async,
  non-blocking) to fill `exercise_tags` from dilf's `ALL_DETECTORS`.
  Idempotent.
- **PedagogyPanel** post-game UI — verdict per half-move + ACPL bars
  per side + motif badges + clickable motif → drill page (PR #50).
- **Interop contract documented** (`backend/pedagogy/INTEROP.md`) +
  CI smoke test `backend/tests/test_dilf_imports.py` (PR #29).

### Changed

- Backend tests capped at 5-min CI timeout to avoid 6h zombies
  (PR #3 / commit `3077328`).

## Out of scope

- Engine integration: Scan + opening book live here; dilf is engine-agnostic.
- Frontend testing infrastructure: no Jest/Vitest setup yet (next on
  the roadmap — see `ROADMAP.md`).
