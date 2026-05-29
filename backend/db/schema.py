from __future__ import annotations
import json
import logging as _log
import aiosqlite

from .config import DB_PATH


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                white_player TEXT DEFAULT 'Joueur',
                black_player TEXT DEFAULT 'IA',
                result TEXT,
                pdn TEXT,
                fen_positions TEXT,
                move_count INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                initial_fen TEXT NOT NULL,
                solution_moves TEXT NOT NULL,
                difficulty INTEGER DEFAULT 1,
                category TEXT DEFAULT 'general',
                hint TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_id INTEGER NOT NULL,
                attempts INTEGER DEFAULT 0,
                solved INTEGER DEFAULT 0,
                date_solved TEXT,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_exercise_solved (
                user_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                solved_at TEXT NOT NULL,
                PRIMARY KEY (user_id, exercise_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_lesson_read (
                user_id INTEGER NOT NULL,
                chapter INTEGER NOT NULL,
                read_at TEXT NOT NULL,
                PRIMARY KEY (user_id, chapter),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS active_games (
                id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        # Expert games corpus (NNUE training)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expert_games (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                source        TEXT NOT NULL,
                source_id     TEXT,
                date          TEXT,
                white_name    TEXT,
                black_name    TEXT,
                white_rating  INTEGER,
                black_rating  INTEGER,
                result        TEXT NOT NULL,
                num_plies     INTEGER,
                event         TEXT,
                variant       TEXT NOT NULL DEFAULT 'standard',
                pdn           TEXT NOT NULL,
                ingested_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (source, source_id)
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_eg_date ON expert_games(date)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_eg_variant ON expert_games(variant)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_eg_min_rating ON expert_games("
            "CASE WHEN white_rating IS NULL THEN black_rating "
            "     WHEN black_rating IS NULL THEN white_rating "
            "     WHEN white_rating < black_rating THEN white_rating "
            "     ELSE black_rating END)"
        )

        # Pedagogy tables (PR 7)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS move_verdicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                move_number INTEGER NOT NULL,
                side TEXT NOT NULL,
                fen_before TEXT NOT NULL,
                fen_after TEXT NOT NULL,
                move_notation TEXT NOT NULL,
                score_before REAL NOT NULL,
                score_after REAL NOT NULL,
                delta_winchance REAL NOT NULL,
                verdict TEXT NOT NULL,
                is_forced INTEGER NOT NULL,
                phase TEXT NOT NULL,
                motifs_json TEXT NOT NULL,
                features_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
                UNIQUE (game_id, move_number)
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_move_verdicts_game ON move_verdicts(game_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_move_verdicts_verdict ON move_verdicts(verdict)"
        )
        # JSON-extract index on motifs_json for profile aggregation queries
        # that filter by motif name (spec §10).
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_move_verdicts_motifs "
            "ON move_verdicts(json_extract(motifs_json, '$'))"
        )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pedagogy_explanations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                move_verdict_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                lang TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (move_verdict_id) REFERENCES move_verdicts(id) ON DELETE CASCADE,
                UNIQUE (move_verdict_id, mode, lang)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exercise_tags (
                exercise_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (exercise_id, tag),
                FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_exercise_tags_tag ON exercise_tags(tag)"
        )
        # Live PvP — challenge queue. One row per challenge sent.
        # status moves pending → accepted (game_id set) | declined | expired
        # | cancelled (challenger reverted before the opponent answered).
        await db.execute("""
            CREATE TABLE IF NOT EXISTS live_challenges (
                id TEXT PRIMARY KEY,
                challenger_id INTEGER NOT NULL,
                opponent_id INTEGER NOT NULL,
                preferred_color TEXT NOT NULL DEFAULT 'random',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,
                game_id TEXT,
                FOREIGN KEY (challenger_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (opponent_id)   REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (game_id)       REFERENCES games(id) ON DELETE SET NULL
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_live_challenges_opponent_status "
            "ON live_challenges(opponent_id, status)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_live_challenges_challenger_status "
            "ON live_challenges(challenger_id, status)"
        )
        await db.commit()

        # Migrations: add columns to existing tables if they don't exist yet
        for col_ddl in [
            "ALTER TABLE games ADD COLUMN user_id INTEGER",
            "ALTER TABLE games ADD COLUMN annotations_json TEXT",
            "ALTER TABLE exercises ADD COLUMN book_id TEXT DEFAULT 'dubois_combinaisons'",
            "ALTER TABLE games ADD COLUMN user_side TEXT",
            "ALTER TABLE games ADD COLUMN opening_name TEXT",
            "ALTER TABLE games ADD COLUMN status TEXT DEFAULT 'finished'",
            "ALTER TABLE games ADD COLUMN source TEXT",
            "ALTER TABLE games ADD COLUMN source_id TEXT",
            "ALTER TABLE users ADD COLUMN lidraughts_username TEXT",
            # Display username used by the live PvP lobby + future
            # leaderboards. NULL on legacy rows; auto-populated from
            # the email local-part on first call to GET /api/auth/me
            # (see backend/main.py). The unique-on-LOWER index below
            # is what enforces case-insensitive uniqueness on the
            # column itself.
            "ALTER TABLE users ADD COLUMN username TEXT",
            "ALTER TABLE move_verdicts ADD COLUMN features_after_json TEXT",
            # Live PvP — extend games with the two-player + turn fields
            # so a live game can be persisted in the same table as imports.
            # kind='live' separates them from imported PDNs.
            "ALTER TABLE games ADD COLUMN kind TEXT DEFAULT 'imported'",
            "ALTER TABLE games ADD COLUMN white_user_id INTEGER",
            "ALTER TABLE games ADD COLUMN black_user_id INTEGER",
            "ALTER TABLE games ADD COLUMN turn TEXT DEFAULT 'white'",
        ]:
            try:
                await db.execute(col_ddl)
                await db.commit()
            except Exception:
                pass  # column already exists

        # Prevent duplicate imports of the same lidraughts game per user.
        try:
            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_games_user_source "
                "ON games(user_id, source, source_id) "
                "WHERE source IS NOT NULL AND source_id IS NOT NULL"
            )
            await db.commit()
        except Exception:
            pass

        # Case-insensitive uniqueness on users.username — SQLite doesn't
        # support `UNIQUE COLLATE NOCASE` on an ALTER ADD COLUMN, so we
        # express the same invariant through an expression index on
        # LOWER(username), partial so NULL rows don't collide.
        try:
            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_nocase "
                "ON users(LOWER(username)) WHERE username IS NOT NULL"
            )
            await db.commit()
        except Exception:
            pass

        # Seed exercises from the preprocessed manuels (see
        # backend/manuels/ and dilf/docs/MANUELS_PIPELINE.md). IDs are
        # stable across redeploys: the manuel Débutant occupies
        # DEBUTANT_ID_OFFSET + 1 ... + N.
        try:
            from manuels.loader import (
                DEBUTANT_ID_OFFSET,
                MANUEL_DEBUTANT_BOOK_ID,
                all_debutant_exercises,
            )
        except Exception as e:
            _log.error(f"init_db: failed to import manuels.loader: {e}")
        else:
            batch_size = 50
            for idx, ex in enumerate(all_debutant_exercises(), start=DEBUTANT_ID_OFFSET + 1):
                try:
                    await db.execute(
                        """
                        INSERT INTO exercises (id, name, description, initial_fen, solution_moves, difficulty, category, hint, book_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            name=excluded.name,
                            description=excluded.description,
                            initial_fen=excluded.initial_fen,
                            solution_moves=excluded.solution_moves,
                            difficulty=excluded.difficulty,
                            category=excluded.category,
                            hint=excluded.hint,
                            book_id=excluded.book_id
                        """,
                        (
                            idx,
                            ex["name"],
                            ex["description"],
                            ex["initial_fen"],
                            json.dumps(ex["solution_moves"]),
                            ex["difficulty"],
                            ex["category"],
                            ex["hint"],
                            ex["book_id"],
                        ),
                    )
                except Exception as e:
                    _log.error(f"init_db: failed to upsert manuel_debutant exercise {idx}: {e}")
                if (idx - DEBUTANT_ID_OFFSET) % batch_size == 0:
                    await db.commit()
            await db.commit()

            # Drop legacy rows from the previous static seed (IDs 1..572).
            # Idempotent: harmless on fresh DBs.
            try:
                await db.execute(
                    "DELETE FROM exercises WHERE id <= ?", (DEBUTANT_ID_OFFSET,)
                )
                await db.commit()
            except Exception as e:
                _log.error(f"init_db: failed to drop legacy exercises: {e}")

        # Seed verified 'play and win' combinations mined from the scanned
        # strategy manuals (see backend/strategy/generate_exercises.py). IDs
        # occupy STRATEGY_ID_OFFSET + 1 ... + N, clear of manuel_debutant.
        try:
            from strategy.exercises_loader import (
                STRATEGY_ID_OFFSET,
                all_strategy_exercises,
            )
        except Exception as e:
            _log.error(f"init_db: failed to import strategy.exercises_loader: {e}")
        else:
            for idx, ex in enumerate(
                all_strategy_exercises(), start=STRATEGY_ID_OFFSET + 1
            ):
                try:
                    await db.execute(
                        """
                        INSERT INTO exercises (id, name, description, initial_fen, solution_moves, difficulty, category, hint, book_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            name=excluded.name,
                            description=excluded.description,
                            initial_fen=excluded.initial_fen,
                            solution_moves=excluded.solution_moves,
                            difficulty=excluded.difficulty,
                            category=excluded.category,
                            hint=excluded.hint,
                            book_id=excluded.book_id
                        """,
                        (
                            idx,
                            ex["name"],
                            ex["description"],
                            ex["initial_fen"],
                            json.dumps(ex["solution_moves"]),
                            ex["difficulty"],
                            ex["category"],
                            ex["hint"],
                            ex["book_id"],
                        ),
                    )
                except Exception as e:
                    _log.error(f"init_db: failed to upsert strategy exercise {idx}: {e}")
            await db.commit()
