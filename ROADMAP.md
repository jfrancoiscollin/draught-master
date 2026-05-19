# draught-master roadmap

Living document of what's shipped, what's next, and what's deferred.
Update when an item lands or when priorities shift.

Companion roadmap lives in
[`jfrancoiscollin/dilf` ROADMAP.md](https://github.com/jfrancoiscollin/dilf/blob/develop/ROADMAP.md);
work on the pedagogy detection layer happens there.

## Where we are today

- **Backend on `develop` @ `6005ac5`** — FastAPI + Scan + opening book
  duo + dilf-consumed pedagogy layer. SQLite with idempotent startup
  migrations. dilf pinned at `9fccc1f` (commit on dilf `develop` —
  see CHANGELOG.md).
- **Frontend on `develop` @ `6005ac5`** — React + Tailwind + Vite.
  Tabs: Home, Play, Apprendre (exercise library + motifs catalog),
  Profil, Mes parties, Analyser (Import PDN + Play both sides),
  OpeningExplorer, Coup-par-coup.
- **Pedagogy live in production** — bulk Lidraughts import,
  per-game analyse-game via dilf, post-game PedagogyPanel with
  verdict per half-move, motif drill pages, weakness tracking with
  threshold-based surfacing, motifs catalog.
- **One pedagogical manual shipped** (Débutant — 152 Dubois positions
  + 14 invented; ExerciseLibraryPage). Three placeholders (Intermédiaire,
  Avancé, Expert) marked "Bientôt".

## Tier 1 — Consolidate what just shipped

Two production-grade features landed on 2026-05-17: the FMJD
prise-max relaxation in dilf's combinaison detectors and the
PedagogyPanel ↔ board two-way binding. Both need light validation
before we move on.

- [ ] **Combinaison detectors — real-game validation**. Add a pytest
      fixture under `backend/tests/` with 5–10 Lidraughts PDNs that
      contain prise-max ambiguities. Run analyse-game end-to-end with
      the real Scan engine and assert that `combinaison_N_temps`
      motifs appear on the expected half-moves. Risk: false positives
      from the relaxed `_opp_is_forced` heuristic. Owner: TBD. (S)
- [ ] **PedagogyPanel — minimal UI tests**. The repo has no
      Jest/Vitest setup. Bootstrap Vitest (already available via
      Vite), add three tests on `PedagogyPanel.tsx`: (1) row click
      calls `onJumpTo` with the right half-move, (2) `currentHalfMove`
      prop highlights the matching row, (3) chevron click stops
      propagation. Owner: TBD. (S)
- [ ] **"Verdict not yet computed" 404 path**. `api.py:416` and `:483`
      raise a `404` when `/explain-move` is called before analyse-game
      ran. The path is untested and produces a generic browser-side
      error. Add a backend test + a Toast on the frontend with copy
      "Analyse la partie d'abord". (S)
- [x] **Surface the 4 P3 motifs in `motif_descriptions.py`** —
      `coup_napoleon`, `coup_manoury`, `coup_enfilade`, `coup_du_bruleur`
      now have FR/EN descriptions in the dict. MOTIFS covers the full
      18 slugs dilf emits, no more 404 on P3 badges.

## Tier 2 — closed, formerly the dilf contract gap

Resolved as documentation drift: `pedagogy.notation.dubois.parse_move_notation`
already ships in dilf (since 2026-05-15) and `engine.apply_move`
resolves through `GameEngineAdapter`. The tagging script has been
working end-to-end; the INTEROP / ROADMAP docs were describing a gap
that no longer existed.

End-to-end coverage added in
`backend/tests/test_tag_existing_exercises_real.py` — real Dubois
fixtures with capture-based motifs assert the script's
`_detect_tags` actually fires the right slugs.

- [x] Pin verification — capture-based detectors fire on real
      exercises (test passes).
- [x] INTEROP.md "Currently-missing helpers" section rewritten as
      historical context.

## Tier 3 — Next pedagogical manual

Manuel Débutant is in production. Intermédiaire / Avancé / Expert are
greyed out in ExerciseLibraryPage.tsx. Shipping Intermédiaire requires
work in **both** repos.

- [ ] **dilf-side: cadrer le manuel Intermédiaire**. Define chapter
      structure (likely 14–16 chapters, ~200–250 positions) following
      the Débutant template (see dilf `docs/pre_process_corpus/`).
      Identify source PDFs in `docs/corpus/`. (curation work, ~1–2 days)
- [ ] **dilf-side: run extraction pipeline** on the chosen PDFs.
      Blocking dependencies: dilf P1 (extract 8 other Dubois PDFs with
      V4 thresholds) likely fine; dilf P2 (king detector) needed if
      the manual covers endgame chapters.
- [ ] **draught-master-side: produce `fixtures_intermediaire.py` +
      `manuel_intermediaire.md`**, mirror of `fixtures_debutant.py`.
- [ ] **draught-master-side: flip `hasExercises: true`** in
      `ExerciseLibraryPage.tsx:18-55`, add the migration in
      `db/schema.py` to upsert the new exercise set on startup.

## Tier 4 — Live PvP entre amis

Ship a real-time "challenge a named friend" mode so users can play a
game inside Draught Master without bouncing through lidraughts —
keeping the pedagogy stack (dilf + heatmap + Gantt) one click away
once the game ends. Full cadrage in
[`docs/PVP_LIVE.md`](./docs/PVP_LIVE.md).

Hard scope cuts for v1: no matchmaking, no clock, no Elo, no
spectators, no chat. The goal is the smallest surface that exercises
the WebSocket + game-state plumbing end-to-end, not a lidraughts
clone.

- [x] **J1 — schema + REST challenge queue**. `live_challenges` table,
      `games.kind`/`white_user_id`/`black_user_id`/`turn` columns,
      `POST /challenge` + `GET /challenges/pending` +
      `POST /challenge/{id}/respond` + `POST /challenge/{id}/cancel`,
      with 12 backend tests covering happy paths + the 404/409/422
      error surfaces. Module at `backend/live/`.
- [x] **J2 — WebSocket transport**. Single endpoint `WS /api/live/ws`
      with first-frame `{type:'auth', token}` handshake, in-memory
      `Dict[user_id, WebSocket]` (the `manager` singleton at
      `backend/live/presence.py`), `ping`/`pong` heartbeat,
      single-connection-per-user enforcement (second tab connecting
      receives `auth_ok`, the first receives `kicked_by_other_session`
      and is closed). The REST challenge endpoints now push
      `challenge_received` / `challenge_resolved` /
      `challenge_cancelled` notifications to the relevant party when
      they're online — best-effort, the pending list is still
      refetched on next connect if they were offline. 11 backend
      tests covering the handshake (4 paths), ping/pong, unknown
      frame tolerance, kick, and the three REST-driven push hooks.
- [ ] **J3 — game state machine**. Spawn a `kind='live'` game on
      challenge acceptance, validate moves through `game_engine`,
      broadcast `move_played` to both clients, persist incrementally to
      the `games.pdn` column.
- [ ] **J4 — fin de partie & déconnexions**. Auto-detect mate /
      blockage, wire the 2-min disconnect grace period, expose
      `resign` over WS, mark `status='finished'` or
      `status='abandoned_<color>'`.
- [ ] **J5 — UI lobby + live game screen**. `<LivePlayPanel>` (lobby
      with challenge form + received/sent lists), `<LiveGameScreen>`
      (adapted from `ImportGamePanel`: active board, "À toi de jouer"
      banner, abandon button, post-game "Analyser cette partie" CTA).
- [ ] **J6 — `<ChallengeToast>` global + polish**. Toast on
      `challenge_received` from any screen of the app, integration
      tests across the WS lifecycle, doc pass.

Hard risks documented in `docs/PVP_LIVE.md` §Risques: in-memory state
loss on redeploy (mitigation = clear user message, future = Redis),
no anti-cheat (mitigation = trust between friends, future = move
timing analysis), WS battery drain on mobile (mitigation = 30s
ping interval).

## Tier 5 — Deferred / opportunistic

Items we've identified but with no commitment on timing.

- [ ] **NNUE corpus auto-discovery loop**. Today
      `OpeningCacheBuilder.tsx` requires manual seed input. Add a
      pipeline: fetch top-N players from Lidraughts, expand to their
      opponents, prune by ELO range, fetch games in priority order.
      Probably gated by Lidraughts API rate limits. (M)
- [ ] **`frontend/CLAUDE.md`**. Document the tab model
      (`App.tsx:168`), main components & props, API client
      (`src/api/client.ts`), `LanguageContext`, auth flow. Helps next
      contributor onboard. (S)
- [ ] **"Bientôt" tooltips**. The disabled manual cards in
      `ExerciseLibraryPage.tsx` say "Bientôt" with no context. Add
      a tooltip linking to this ROADMAP. (S)
- [ ] **Sentry context** on pedagogy spans — game_id, user_id, motif
      slug — for production debugging.
- [ ] **dilf as a published PyPI package** instead of a git-URL pin.
      Simplifies `backend/requirements.txt` and removes the
      tarball-of-SHA pattern.

## Out of scope

- Replacing dilf's deterministic detectors with a learned model
  (auditability is the point).
- Real-time analysis during play (architecture is built around
  post-game analysis).
- Multi-engine support beyond Scan. dilf is engine-agnostic via
  `EngineProtocol`; we wire Scan only.

## How this document moves

When an item ships, check the box and add an entry to `CHANGELOG.md`.
When priorities shift, edit the relevant tier and add a date stamp.
The "Where we are today" section at the top must always reflect what's
actually on `develop`.
