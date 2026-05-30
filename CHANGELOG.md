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

- **Stratégie — base de connaissances depuis les diagrammes scannés**
  (PR #118, #119). Les positions extraites des quatre manuels
  (Sijbrands, Springer, Roozenburg, Keller) alimentent un pipeline en
  quatre couches : (1) une **bibliothèque consolidée** de 1369 positions
  validées par le moteur (1308 valides) — `build_position_library.py` +
  `position_library.json` ; (2) une **base de connaissances thématique**
  (66 thèmes de leçon → positions, endpoints `/api/strategy/kb-themes` et
  `/kb-theme`) plus 68/79 tips enrichis de positions-exemples des manuels,
  affichées en jeu sous l'analyse (`TipExamples.tsx`) ; (3) **108
  exercices vérifiés** (61 finales + 45 gains de matériel + 2 annihilations
  forcées), chaque solution rejouée pour prouver légalité et gain, seedés
  via `generate_exercises.py` / `exercises_loader.py` (IDs 5001+) ; (4)
  **prose interactive** — Sijbrands rejoint les sources *trusted-auto* et
  un flag `valid` évite tout plateau cassé. Garde de légalité : un pion
  sur sa rangée de promotion est rejeté. Voir
  [`docs/STRATEGIE_KNOWLEDGE_BASE.md`](docs/STRATEGIE_KNOWLEDGE_BASE.md).
- **Live PvP — J6 (global ChallengeToast + polish)**. v1 complete.
  New `<ChallengeToast>` mounted at the App level so a
  `challenge_received` push surfaces on any tab — single-slot
  replace-on-new policy keeps layout simple, accept / decline inline,
  the accept button also routes the user to the live tab. Same
  surface handles `challenge_cancelled` (replaces a matching open
  toast with "X a annulé son défi") and `kicked_by_other_session`
  ("Connexion reprise sur un autre onglet ou appareil"). Info-style
  toasts auto-dismiss after 4 s; action toasts stay until the user
  responds. README updated to reflect feature is shipped (no longer
  "en cours"). 6 new vitest tests; 16 frontend tests total.
- **Live PvP — J5 (lobby UI + active-game screen + WS hook)**.
  Frontend now consumes the J1-J4 backend end-to-end. New
  `<LivePlayPanel>` lobby with a challenge form, live-updated
  received/sent challenge lists, and bootstrap fetch on mount. New
  `<LiveGameScreen>` wrapping the existing `<Board>` for an active
  live game — "À toi de jouer" banner, disconnect-grace countdown,
  Abandon button, post-game "🎓 Analyser cette partie" CTA piping
  into the existing import-game pedagogy flow. New `useLiveWS` hook
  exposes a module-level singleton WebSocket: auto-reconnect with
  exponential backoff, 25-second ping/pong heartbeat, drop on
  auth_error (a bad token won't fix itself), per-message-type
  subscriptions via refs so inline closures don't leak. New `'live'`
  tab in App.tsx, gated behind auth. Backend tweak:
  `LiveGameSession.to_dict` now also ships the FEN so the frontend
  renders the board immediately without replaying the pdn through a
  JS engine.
- **Live PvP — J4 (disconnect grace + reconnect path)**. When a
  player drops their WebSocket mid-game, the partner now receives
  `opponent_disconnected` (with `grace_seconds` for a local countdown)
  and a server-side `asyncio.Task` schedules an auto-forfeit. A
  reconnect within the window cancels the timer, ships a `game_state`
  bootstrap frame to the returning player, and pushes
  `opponent_reconnected` to the partner. Past the window, the timer
  fires `_forfeit_after_grace` → marks `abandoned_<color>`,
  broadcasts `game_ended` with `by_forfeit=true`. Per-user task
  tracking lives in `LiveGameManager` (`schedule_forfeit` /
  `cancel_forfeit` / `clear_forfeit`); only one timer per user can
  be alive at a time. The FastAPI `startup` hook stamps every
  still-`in_progress` live game as `abandoned_server` so a redeploy
  doesn't leave zombie sessions in the lobby. 6 new tests (mostly
  unit-level — the cross-session reconnect pattern hangs in
  Starlette's TestClient, the E2E coverage is limited to the
  `opponent_disconnected` push).
- **Live PvP — J3 (game state machine + move broadcast)**. Challenge
  acceptance now also spawns a `kind='live'` row in `games`, assigns
  colors per the challenger's `preferred_color` (random falls back to
  a CSPRNG draw), and broadcasts `game_started` to both players on the
  WebSocket. `backend/live/game_session.py` exports a
  `LiveGameManager` singleton holding the in-process engine state and
  a reverse `user_id → game_id` index so incoming WS frames route in
  O(1). Two new client→server WS message types: `move` (validates
  against `game_engine.get_legal_moves`, broadcasts `move_played` to
  both, auto-detects mate/blockage and chains `game_ended`) and
  `resign` (marks `abandoned_<color>`, broadcasts `game_ended`).
  Every move atomically persists `pdn` + `turn` + `status` to the
  games row, so a finished live game flows through the existing
  `/analyze-game` pipeline without conversion. Stable error taxonomy
  on the WS `error` frame: `not_in_game` / `game_over` /
  `not_your_turn` / `unknown_move`. 9 new tests; 134 backend total.
- **Live PvP — J2 (WebSocket transport + push notifications)**.
  Single endpoint `WS /api/live/ws` with a first-frame
  `{type:'auth', token}` handshake (same JWT as the REST surface,
  10-second timeout, explicit `auth_error` frames on every failure
  path). In-memory `Dict[user_id, WebSocket]` lives in
  `backend/live/presence.py` as the `manager` singleton; second
  connection from the same user kicks the first with
  `kicked_by_other_session`. `ping`/`pong` for heartbeat; unknown
  message types receive an `error` frame but keep the connection
  open (forward-compat with future J3+ message types). The three
  REST challenge endpoints now push `challenge_received` /
  `challenge_resolved` / `challenge_cancelled` to the relevant
  party when online — best-effort, the pending list still backfills
  on next connect. 11 new backend tests; ROADMAP Tier 4 J2 ticked.
- **Live PvP — J1 (challenge queue)**. New `backend/live/` module
  shipping the REST surface for the upcoming friend-vs-friend mode:
  `POST /api/live/challenge`, `GET /api/live/challenges/pending`,
  `POST /api/live/challenge/{id}/respond`,
  `POST /api/live/challenge/{id}/cancel`. New `live_challenges` table
  + four columns on `games` (`kind`, `white_user_id`, `black_user_id`,
  `turn`) wired through idempotent startup migrations. 12 backend
  tests cover happy paths + the 404/409/422 surfaces. Full cadrage and
  the J2-J6 plan in [`docs/PVP_LIVE.md`](./docs/PVP_LIVE.md); roadmap
  entry under Tier 4.
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
