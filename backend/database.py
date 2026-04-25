from __future__ import annotations
import json
import aiosqlite
from typing import Optional, List, Dict, Any
from pathlib import Path

DB_PATH = Path(__file__).parent / "draught.db"

INITIAL_EXERCISES = [
    {
        "name": "Prise simple obligatoire",
        "description": "Les blancs doivent effectuer la prise obligatoire. Trouvez le coup unique.",
        # Black piece at 29 (between 33 and landing square 24)
        "initial_fen": "W:W32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50:B1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,29",
        "solution_moves": ["33x24"],
        "difficulty": 1,
        "category": "captures",
        "hint": "Cherchez le pion noir isolé en avant du front blanc.",
    },
    {
        "name": "Double prise en chaîne",
        "description": "Les blancs peuvent effectuer une double prise. Trouvez la séquence complète.",
        # Black at 29 (between 33→24) and 20 (between 24→15)
        "initial_fen": "W:W33,40,41,42,43,44,45,46,47,48,49,50:B20,29",
        "solution_moves": ["33x24x15"],
        "difficulty": 2,
        "category": "captures",
        "hint": "Regardez s'il est possible de prendre deux pièces en un seul coup.",
    },
    {
        "name": "Promotion forcée",
        "description": "Les blancs peuvent forcer la promotion d'un pion en dame. Trouvez le meilleur plan.",
        "initial_fen": "W:W6,47,48,49,50:B15,16,17,18",
        "solution_moves": ["6-1"],
        "difficulty": 2,
        "category": "promotion",
        "hint": "Quel pion blanc peut atteindre la rangée de promotion rapidement ?",
    },
    {
        "name": "Finale dame contre pions",
        "description": "Les blancs ont une dame et doivent gagner contre les pions noirs. Trouvez le plan gagnant.",
        # King at 28, black at 43 and 45 (not on any diagonal from 28)
        "initial_fen": "W:WK28:B43,45",
        "solution_moves": ["28-22"],
        "difficulty": 3,
        "category": "endgame",
        "hint": "La dame doit dominer les pions adverses en coupant leur avance.",
    },
    {
        "name": "Piège d'ouverture classique",
        "description": "Les blancs peuvent tendre un piège tactique. Identifiez le coup qui force une prise avantageuse.",
        "initial_fen": "W:W32,33,34,35,36,37,38,39,40,41,43,44,45,47,48,49,50:B1,2,3,4,5,6,7,8,9,10,11,12,13,20,22",
        "solution_moves": ["32-28"],
        "difficulty": 3,
        "category": "opening",
        "hint": "Développez votre pièce vers le centre pour créer des menaces.",
    },
    {
        "name": "Triple prise spectaculaire",
        "description": "Les blancs peuvent éliminer trois pions en un seul coup ! Trouvez la séquence.",
        # 31x22x13x4: captures at 27 (between 31→22), 18 (between 22→13), 9 (between 13→4)
        "initial_fen": "W:W31,40,41,42,43,44,45,46,47,48,49,50:B9,18,27",
        "solution_moves": ["31x22x13x4"],
        "difficulty": 3,
        "category": "captures",
        "hint": "Cherchez le chemin qui permet de capturer le maximum de pièces.",
    },
    {
        "name": "Blocage stratégique",
        "description": "Les blancs doivent bloquer l'avance des pions noirs. Trouvez le coup défensif optimal.",
        # Removed black pawn at 25 so 30-25 is a legal move
        "initial_fen": "W:W30,37,38,40,41,43,46,47,48,49,50:B1,2,3,4,5,6,7,14,19",
        "solution_moves": ["30-25"],
        "difficulty": 2,
        "category": "strategy",
        "hint": "Occupez la case clé pour stopper l'avance adverse.",
    },
    {
        "name": "Combat de dames",
        "description": "Les deux camps ont des dames. Les blancs doivent trouver le coup gagnant.",
        # Black king at 35 (not on any diagonal from 22), sol without K prefix
        "initial_fen": "W:WK22,47:BK35",
        "solution_moves": ["22-17"],
        "difficulty": 4,
        "category": "endgame",
        "hint": "Positionnez votre dame pour dominer les diagonales importantes.",
    },
    {
        "name": "Prise de flanc",
        "description": "Les blancs peuvent exploiter la faiblesse du flanc noir. Trouvez la combinaison tactique.",
        "initial_fen": "W:W33,34,38,39,43,44,46,47,48,50:B8,9,13,14,19,22,23",
        "solution_moves": ["34-30"],
        "difficulty": 3,
        "category": "tactics",
        "hint": "Attaquez le flanc adverse avec précision.",
    },
    {
        "name": "Finale deux contre un",
        "description": "Les blancs ont deux pions contre un pion noir avancé. Comment gagner ?",
        # White at 28 and 34, black at 21 — 28-22 is a legal non-capture move
        "initial_fen": "W:W28,34:B21",
        "solution_moves": ["28-22"],
        "difficulty": 3,
        "category": "endgame",
        "hint": "Coordonnez vos pions pour bloquer et dépasser le pion adverse.",
    },
    {
        "name": "Attaque centrale",
        "description": "Occupez le centre du plateau pour dominer la position. Quel est le meilleur coup ?",
        "initial_fen": "W:W31,32,33,34,35,36,37,38,39,41,42,43,44,45,46,47,48,49,50:B1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20",
        "solution_moves": ["33-28"],
        "difficulty": 1,
        "category": "opening",
        "hint": "Les cases centrales 23, 24, 27, 28 sont les plus importantes.",
    },
    {
        "name": "Schème de la turque",
        "description": "Exercice sur le schème de la turque, une combinaison classique du jeu de dames.",
        "initial_fen": "W:W25,30,34,35,36,41,42,43,44,45,46,47,48,49,50:B6,11,17,18,19,21,22",
        "solution_moves": ["25-20"],
        "difficulty": 4,
        "category": "tactics",
        "hint": "Cherchez une combinaison en plusieurs coups impliquant des prises multiples.",
    },
    {
        "name": "Finale roi d'opposition",
        "description": "Les blancs avec une dame doivent forcer la victoire. Utilisez l'opposition.",
        "initial_fen": "W:WK1:B46,47",
        "solution_moves": ["1-6"],
        "difficulty": 5,
        "category": "endgame",
        "hint": "La dame doit couper les pions de leur chemin vers la promotion.",
    },
]


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
        await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM exercises")
        row = await cursor.fetchone()
        if row and row[0] == 0:
            for ex in INITIAL_EXERCISES:
                await db.execute(
                    """
                    INSERT INTO exercises (name, description, initial_fen, solution_moves, difficulty, category, hint)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ex["name"],
                        ex["description"],
                        ex["initial_fen"],
                        json.dumps(ex["solution_moves"]),
                        ex["difficulty"],
                        ex["category"],
                        ex["hint"],
                    ),
                )
            await db.commit()


async def save_game(
    game_id: str,
    date: str,
    white_player: str,
    black_player: str,
    result: Optional[str],
    pdn: str,
    fen_positions: List[str],
    move_count: int,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO games
            (id, date, white_player, black_player, result, pdn, fen_positions, move_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (game_id, date, white_player, black_player, result, pdn, json.dumps(fen_positions), move_count),
        )
        await db.commit()


async def get_games(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM games ORDER BY date DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_game(game_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            data["fen_positions"] = json.loads(data["fen_positions"])
            return data
        return None


async def get_exercises(
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM exercises WHERE 1=1"
        params: List[Any] = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if difficulty is not None:
            query += " AND difficulty = ?"
            params.append(difficulty)
        query += " ORDER BY difficulty ASC, id ASC"
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["solution_moves"] = json.loads(data["solution_moves"])
            result.append(data)
        return result


async def get_exercise(exercise_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,))
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            data["solution_moves"] = json.loads(data["solution_moves"])
            return data
        return None


async def save_exercise(exercise: Dict[str, Any]) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO exercises (name, description, initial_fen, solution_moves, difficulty, category, hint)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exercise["name"],
                exercise.get("description", ""),
                exercise["initial_fen"],
                json.dumps(exercise.get("solution_moves", [])),
                exercise.get("difficulty", 1),
                exercise.get("category", "general"),
                exercise.get("hint", ""),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def record_progress(exercise_id: int, solved: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, attempts, solved FROM user_progress WHERE exercise_id = ?",
            (exercise_id,),
        )
        row = await cursor.fetchone()
        if row:
            new_solved = 1 if (row[2] or solved) else 0
            from datetime import datetime
            date_solved = datetime.utcnow().isoformat() if solved and not row[2] else None
            await db.execute(
                "UPDATE user_progress SET attempts = attempts + 1, solved = ?, date_solved = COALESCE(date_solved, ?) WHERE id = ?",
                (new_solved, date_solved, row[0]),
            )
        else:
            from datetime import datetime
            date_solved = datetime.utcnow().isoformat() if solved else None
            await db.execute(
                "INSERT INTO user_progress (exercise_id, attempts, solved, date_solved) VALUES (?, 1, ?, ?)",
                (exercise_id, 1 if solved else 0, date_solved),
            )
        await db.commit()
