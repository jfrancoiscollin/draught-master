from __future__ import annotations
import json
import logging as _log
import aiosqlite

from .config import DB_PATH
from .exercises_data import INITIAL_EXERCISES
from .sens_du_jeu_exercises import SENS_DU_JEU_EXERCISES

_SENS_DU_JEU_ID_OFFSET = 500  # IDs 501-509 for sens_du_jeu exercises


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
        await db.commit()

        # Migrations: add columns to existing tables if they don't exist yet
        for col_ddl in [
            "ALTER TABLE games ADD COLUMN user_id INTEGER",
            "ALTER TABLE games ADD COLUMN annotations_json TEXT",
            "ALTER TABLE exercises ADD COLUMN book_id TEXT DEFAULT 'dubois_combinaisons'",
            "ALTER TABLE games ADD COLUMN user_side TEXT",
            "ALTER TABLE games ADD COLUMN opening_name TEXT",
            "ALTER TABLE games ADD COLUMN status TEXT DEFAULT 'finished'",
        ]:
            try:
                await db.execute(col_ddl)
                await db.commit()
            except Exception:
                pass  # column already exists

        # Always upsert exercises with fixed IDs so Railway's persistent DB
        # picks up corrected FEN/solution data on each redeploy.
        batch_size = 50
        for idx, ex in enumerate(INITIAL_EXERCISES, start=1):
            try:
                await db.execute(
                    """
                    INSERT INTO exercises (id, name, description, initial_fen, solution_moves, difficulty, category, hint, book_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'dubois_combinaisons')
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        description=excluded.description,
                        initial_fen=excluded.initial_fen,
                        solution_moves=excluded.solution_moves,
                        difficulty=excluded.difficulty,
                        category=excluded.category,
                        hint=excluded.hint,
                        book_id='dubois_combinaisons'
                    """,
                    (
                        idx,
                        ex.get("name", ""),
                        ex.get("description"),
                        ex.get("initial_fen", ""),
                        json.dumps(ex.get("solution_moves", [])),
                        ex.get("difficulty", 1),
                        ex.get("category", "general"),
                        ex.get("hint"),
                    ),
                )
            except Exception as e:
                _log.error(f"init_db: failed to upsert combinaisons exercise {idx}: {e}")
            if idx % batch_size == 0:
                await db.commit()
        await db.commit()

        # Upsert "Apprendre le sens du jeu" exercises (IDs 501+)
        for idx, ex in enumerate(SENS_DU_JEU_EXERCISES, start=_SENS_DU_JEU_ID_OFFSET + 1):
            try:
                await db.execute(
                    """
                    INSERT INTO exercises (id, name, description, initial_fen, solution_moves, difficulty, category, hint, book_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'dubois_sens_du_jeu')
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        description=excluded.description,
                        initial_fen=excluded.initial_fen,
                        solution_moves=excluded.solution_moves,
                        difficulty=excluded.difficulty,
                        category=excluded.category,
                        hint=excluded.hint,
                        book_id='dubois_sens_du_jeu'
                    """,
                    (
                        idx,
                        ex.get("name", ""),
                        ex.get("description"),
                        ex.get("initial_fen", ""),
                        json.dumps(ex.get("solution_moves", [])),
                        ex.get("difficulty", 1),
                        ex.get("category", "general"),
                        ex.get("hint"),
                    ),
                )
            except Exception as e:
                _log.error(f"init_db: failed to upsert sens_du_jeu exercise {idx}: {e}")
        await db.commit()
