# Draught Master — Entraîneur au Jeu de Dames International

Application web complète d'entraînement au **jeu de dames international** (10×10, règles FMJD) combinant un moteur IA natif (Scan), une analyse tactique par **Claude** (Anthropic) et un système de progression pédagogique.

---

## Fonctionnalités

### Jouer contre l'IA
- Plateau 10×10 interactif avec règles FMJD complètes
- Prise obligatoire et prise maximale (règle du soufflage)
- Moteur **Scan** (réseau de neurones, niveau club à expert selon la profondeur)
- Niveaux 1 à 8 (de débutant à maître)
- Choix de la couleur : Blancs, Noirs, ou Aléatoire
- Damier inversé automatiquement quand on joue les Noirs
- Annulation du dernier coup
- Abandon de partie

### Analyse coup par coup
- Après chaque partie, analyse automatique de tous les coups
- Verdict par coup : **Parfait ✓**, **Imprécision ?!**, **Erreur ?**, **Gaffe ??**
- Score en unités-pion (1.0 ≈ un pion d'avantage) et variation de probabilité de victoire
- Détection des coups forcés (capture unique obligatoire)
- Cache intelligent : les positions déjà analysées sont servies instantanément

### Analyse par Claude (IA)
- Analyse de position en langage naturel (français/anglais)
- Revue de partie complète : ouverture, milieu de jeu, fin de partie
- Explication concise du meilleur coup
- Identification des menaces, sacrifices et combinaisons tactiques

### Explorateur d'ouvertures
- Flèches sur le plateau indiquant les coups du livre d'ouvertures
- Continuations les plus jouées avec fréquence de jeu
- Paramétrable (nombre max de coups, activation/désactivation)

### Exercices tactiques
- Bibliothèque de puzzles classés par thème et difficulté
- Source : **manuels pédagogiques préprocessés** par Claude via [dilf](https://github.com/jfrancoiscollin/dilf), un manuel par niveau (Débutant, Intermédiaire, Avancé, Expert)
- Affichage de l'indice et de la solution
- Suivi de progression par utilisateur
- *Voir la section [Manuels pédagogiques](#manuels-pédagogiques) plus bas.*

### Leçons interactives
- Cours structurés avec positions clés et explications
- Navigation coup par coup dans les variantes

### Apprendre de ses erreurs
- Revue des erreurs des parties précédentes
- Proposition d'exercices ciblés sur les faiblesses détectées

### Import de parties PDN
- Coller un PDN pour analyser n'importe quelle partie
- Compatible avec les parties Lidraughts et autres sources

### Base d'ouvertures
- Construction automatique d'une base d'évaluation depuis des parties réelles
- Import de parties depuis **Lidraughts** par joueur, équipe ou tournoi
- Précomputation des scores pour des réponses instantanées

### Statistiques et profil
- Nombre de parties jouées, gagnées, perdues
- Exercices résolus
- Score moyen de pertes par coup
- Historique des gaffes et erreurs

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                    │
│  Board · GameControls · AnalysisPanel · ExercisePanel   │
│  ImportGame · OpeningExplorer · LessonPanel · Stats     │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTP / REST
┌───────────────────▼─────────────────────────────────────┐
│                  Backend (FastAPI / Python)               │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │game_engine│  │scan_engine│  │    scan_advisor      │  │
│  │ Règles   │  │  Moteur  │  │   API Anthropic       │  │
│  │  FMJD   │  │  Scan NN │  │   claude-opus-4-7     │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │   db/ (config · schema · games · exercises ·     │   │
│  │        users · exercises_data) + opening_book_db │   │
│  │           SQLite (parties · exercices · book)    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Stack technique

| Composant | Technologie |
|-----------|-------------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | Python 3.11 + FastAPI + Uvicorn |
| Base de données | SQLite (WAL mode) |
| Moteur de jeu | Scan (réseau de neurones, Hub v2) |
| IA d'analyse | Claude API (claude-opus-4-7) |
| Déploiement | Railway (Docker) |

---

## Installation locale

### Prérequis
- Python 3.11+
- Node.js 18+
- Clé API Anthropic (`ANTHROPIC_API_KEY`)
- Binaire Scan (optionnel — l'IA minimax Python est disponible en fallback)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt

# Configurer les variables d'environnement
cp ../.env.example .env
# Éditer .env : ANTHROPIC_API_KEY, SECRET_KEY, DATABASE_URL

uvicorn main:app --reload --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `ANTHROPIC_API_KEY` | Clé API Anthropic | obligatoire |
| `SECRET_KEY` | Clé JWT pour l'auth | obligatoire en production |
| `DB_DIR` | Répertoire des bases SQLite | répertoire `backend/` |
| `SCAN_PATH` | Chemin du binaire Scan | `/usr/local/bin/scan` |
| `OPENING_BOOK_DB` | Chemin de la base d'ouvertures | `./opening_book.db` |
| `SENTRY_DSN` | DSN Sentry (monitoring erreurs) | désactivé si vide |

---

## Structure du projet

```
draught-master/
│
├── backend/
│   ├── main.py                 # API FastAPI — tous les endpoints REST
│   ├── game_engine.py          # Moteur de règles FMJD 10×10
│   ├── ai_engine.py            # IA minimax alpha-bêta (fallback)
│   ├── scan_engine.py          # Interface avec le moteur Scan (Hub v2)
│   ├── scan_advisor.py         # Analyse de partie et détection d'erreurs
│   ├── database.py             # Shim de compatibilité → db/
│   ├── db/                     # Package base de données
│   │   ├── config.py           # DB_PATH
│   │   ├── schema.py           # init_db() — création tables + migrations
│   │   ├── games.py            # CRUD parties et jeux actifs
│   │   ├── exercises.py        # CRUD exercices et progression
│   │   ├── users.py            # CRUD utilisateurs, auth, leçons
│   │   └── exercises_data.py   # Données initiales (exercices)
│   ├── models.py               # Schémas Pydantic (requêtes/réponses)
│   ├── opening_book_db.py      # Base d'ouvertures (lookup + stockage)
│   ├── opening_eval_db.py      # Cache d'évaluations de positions
│   ├── cache_builder.py        # Construction de la base d'ouvertures
│   ├── lidraughts_fetcher.py   # Import de parties depuis Lidraughts
│   ├── manuels/                # Fixtures Python des manuels pédagogiques
│   │   └── fixtures_debutant.py
│   ├── scripts/
│   │   └── smoke_test_manuel_debutant.py  # Validation chargement + légalité
│   ├── tests/
│   │   └── test_game_engine.py # 51 tests unitaires règles FMJD
│   ├── requirements.txt
│   └── requirements-dev.txt    # pytest (développement uniquement)
│
├── frontend/
│   └── src/
│       ├── App.tsx                     # Composant racine + routage
│       ├── types.ts                    # Types TypeScript partagés
│       ├── api/
│       │   └── client.ts               # Client HTTP (axios)
│       ├── components/
│       │   ├── Board.tsx               # Plateau interactif 10×10
│       │   ├── GameControls.tsx        # Contrôles de partie
│       │   ├── AnalysisPanel.tsx       # Panneau d'analyse Claude
│       │   ├── EvalBar.tsx             # Barre d'évaluation moteur
│       │   ├── ExercisePanel.tsx       # Solveur d'exercices
│       │   ├── ExerciseLibraryPage.tsx # Bibliothèque de puzzles
│       │   ├── LessonPanel.tsx         # Leçons interactives
│       │   ├── LearnFromMistakes.tsx   # Revue d'erreurs
│       │   ├── GameHistory.tsx         # Historique des parties
│       │   ├── ImportGamePanel.tsx     # Import PDN
│       │   ├── OpeningCacheBuilder.tsx # Interface base d'ouvertures
│       │   ├── UserStatsCard.tsx       # Statistiques utilisateur
│       │   └── MoveList.tsx            # Liste des coups en notation PDN
│       ├── lib/
│       │   ├── gameAnnotations.ts      # Détection d'erreurs (winChance, verdicts)
│       │   └── scanEngine.ts           # Interface WASM Scan (client)
│       └── i18n/
│           ├── translations.ts         # Traductions FR/EN
│           └── LanguageContext.tsx     # Contexte React i18n
│
├── docs/
│   ├── parties/                # Parties PDN de référence
│   ├── livres/                 # Livres de dames (PDF — archive, voir Manuels pédagogiques)
│   └── manuels/                # Manuels pédagogiques préprocessés (prose)
│       └── debutant/manuel_debutant.md
│
├── Dockerfile
├── railway.json
└── .env.example
```

---

## Modules backend détaillés

### `game_engine.py` — Moteur de règles

Implémente les règles FMJD du jeu de dames international 10×10 :

- **Numérotation des cases** : cases 1–50 (cases sombres uniquement, de haut-gauche à bas-droite)
- **Prise obligatoire** : si une prise est disponible, elle doit être jouée
- **Prise maximale** : parmi les prises possibles, la plus longue doit être choisie
- **Dames** : se déplacent sur toute la longueur d'une diagonale libre
- **Promotion** : un pion atteignant la dernière rangée adverse devient dame

Structures de données clés :
```python
@dataclass
class GameState:
    board: dict[int, int]   # case → type de pièce (0=vide, 1=pion blanc, ...)
    turn: str               # 'white' | 'black'
    half_move_clock: int    # compteur pour la règle des 50 coups
    move_history: list      # historique pour détection de répétition

@dataclass
class Move:
    path: list[int]         # séquence de cases traversées
    captures: list[int]     # cases des pièces capturées
```

### `scan_engine.py` — Interface moteur Scan

Scan est un moteur de jeu de dames basé sur un réseau de neurones (fichier `data/eval`). Il communique via le **protocole Hub v2** (stdio, commandes texte).

> **Deux livres d'ouvertures distincts coexistent dans le projet :**
> - Le **livre interne de Scan** (`set-param name=book value=true/false`) : base théorique embarquée dans le binaire Scan. Quand il est actif, Scan court-circuite la recherche et retourne `score=0` pour les positions du livre.
> - **Notre base custom** (`opening_book_db.py`) : positions extraites de vraies parties Lidraughts avec scores Scan pré-calculés, utilisée comme cache dans `scan_advisor.py`.

Deux instances du processus Scan sont maintenues en parallèle, car le livre interne ne peut pas être activé/désactivé à chaud après `init` :

| Instance | Livre interne Scan | Rôle |
|----------|--------------------|------|
| `_engine` | **activé** | Coups de l'IA en partie (joue la théorie d'ouverture) |
| `_eval_engine` | **désactivé** | Évaluation de positions pour l'analyse — le livre renverrait `score=0`, ce qui casse la détection des gaffes |

Notre base Lidraughts est elle utilisée **en amont** dans `scan_advisor.py` : si la position est déjà dans le cache SQLite, `_eval_engine` n'est pas appelé du tout.

Le livre interne est chargé à l'initialisation (`init`) et **ne peut pas être déchargé** à chaud — c'est pourquoi deux processus séparés sont nécessaires.

Protocole Hub v2 (échanges avec le processus Scan) :
```
→ hub
← wait
→ set-param name=book value=false
→ set-param name=bb-size value=0
→ init
← ready
→ pos pos=<51 chars>        # W/B + 50×(e/w/W/b/B)
→ level move-time=0.3
→ go think
← info depth=18 score=-1.22 pv="37-32 ..."
← done move=37-32
```

### `scan_advisor.py` — Analyse et détection d'erreurs

Orchestre l'analyse complète d'une partie :

1. **Évaluation position par position** — appelle `scan_engine.evaluate_pos()` pour chaque état
2. **Détection de coups forcés** — quand Scan retourne un coup sans score (une seule capture légale), le score est propagé depuis la position suivante via la relation negamax : `score(P) = -score(P_suivante)`
3. **Calcul du verdict** — utilise une sigmoïde calibrée sur les unités Scan (1.0 ≈ un pion) :

```python
def winChance(score):
    return 2 / (1 + exp(-2.0 * score)) - 1

delta = winChance(score_avant) + winChance(score_après)
# delta ≥ 0.30 → Gaffe
# delta ≥ 0.15 → Erreur
# delta ≥ 0.075 → Imprécision
```

4. **Cache** — les scores non-nuls sont sauvegardés dans `opening_book_db` pour être réutilisés immédiatement lors d'analyses futures

### `db/` — Package base de données

Le fichier monolithique `database.py` (4 170 lignes) a été découpé en modules séparés :

| Module | Contenu |
|--------|---------|
| `db/config.py` | `DB_PATH` (lit `DB_DIR` depuis l'environnement) |
| `db/schema.py` | `init_db()` — création des tables, migrations, upsert des exercices |
| `db/games.py` | `save_game`, `get_game`, `get_games`, parties actives, annotations, stats |
| `db/exercises.py` | `get_exercises`, `get_exercise`, progression, exercices résolus |
| `db/users.py` | Comptes, JWT, tokens de réinitialisation, leçons lues |
| `db/exercises_data.py` | `INITIAL_EXERCISES` — données des puzzles initiaux |

`database.py` subsiste comme shim de compatibilité (`from db import …`) pour ne pas casser les imports existants.

### `opening_book_db.py` — Base d'ouvertures

- **Canonicalisation** : chaque position est stockée dans sa forme miroir lexicographiquement la plus petite, ce qui double la couverture (symétrie horizontale du damier)
- **Stockage** : FEN → {score (float), meilleur coup, coups vus, profondeur}
- **Lecture** : `lookup(fen)` retourne score + meilleur coup + continuations fréquentes

---

## Manuels pédagogiques

Le matériel pédagogique consommé par Draught Master ne vient **plus** directement des PDFs du corpus Dubois (`docs/livres/`). Il vient désormais de **manuels préprocessés par Claude** dans le repo [dilf](https://github.com/jfrancoiscollin/dilf), un manuel par niveau :

| Manuel | Statut | Fixtures |
|--------|--------|----------|
| Débutant | ✅ Livré | 166 positions, 16 chapitres |
| Intermédiaire | ⏳ À produire | — |
| Avancé | ⏳ À produire | — |
| Expert | ⏳ À produire | — |

### Pipeline

```
corpus PDF (dilf/docs/corpus/)
    ↓ scripts/extract_diagrams.py  (pixel-déterministe, $0)
positions extraites
    ↓ Claude + outillage dilf/docs/pre_process_corpus/
    ↓ (CADRAGE_MANUELS.md, generate_chapter.py, validate_final_moves.py)
manuel_<niveau>.md + fixtures_<niveau>.py
    ↓ copie dans draught-master
docs/manuels/<niveau>/ + backend/manuels/
```

Détails du pipeline : `dilf/docs/MANUELS_PIPELINE.md`.

### Structure côté draught-master

- `docs/manuels/<niveau>/manuel_<niveau>.md` — prose pédagogique lisible par l'utilisateur.
- `backend/manuels/fixtures_<niveau>.py` — module Python exposant les `BeginnerPosition` (ou équivalent), au-dessus du schéma `pedagogy.game.GameState` de dilf.
- `backend/scripts/smoke_test_manuel_<niveau>.py` — validation que les fixtures sont consommables par le backend (round-trip FEN + légalité des `final_move` via `game_engine.get_legal_moves`).

### Smoke test

```bash
cd backend && python -m scripts.smoke_test_manuel_debutant
```

Doit produire :

```
[1] Round-trip FEN dilf ↔ draught-master : 166/166
[2] final_move légal sous moteur draught-master : OK 135/135
SMOKE TEST OK — manuel Débutant intégralement consommable par draught-master.
```

### Suite

- Conversion des `BeginnerPosition` en `INITIAL_EXERCISES` (ou nouvelle table dédiée).
- API `/api/manuels/<niveau>` pour exposer les chapitres et fixtures au frontend.
- Page Manuel côté frontend (lecture de la prose + exercice interactif sur chaque position).
- Suppression progressive de `docs/livres/` une fois les 4 manuels livrés et intégrés.

---

## Analyse coup par coup — Flux détaillé

```
Frontend                          Backend
   │                                 │
   │── POST /api/pdn/annotate ──────►│
   │   {positions: [{fen, notation}]}│
   │                                 │
   │                         Pour chaque position :
   │                         1. opening_book_db.lookup(fen)
   │                            → cache hit si score ≠ 0
   │                         2. scan_engine.evaluate_pos(hub, t)
   │                            → go think → info score=X
   │                            → forced=True si pas de score
   │                         3. Post-traitement negamax
   │                            forced[i].score = -score[i+1]
   │                         4. Sauvegarde en cache (score ≠ 0)
   │                                 │
   │◄── {evaluations, cache_hits} ───│
   │                                 │
   │ buildAnnotations() [frontend]   │
   │   rawLoss = score_avant + score_après
   │   delta = winChance(avant) + winChance(après)
   │   verdict = classify(delta)
   │   lossCp = round(rawLoss * 100)
   └─────────────────────────────────┘
```

---

## Règles FMJD implémentées

| Règle | Détail |
|-------|--------|
| Prise obligatoire | Si une capture est disponible, elle doit être jouée |
| Prise maximale | La séquence de captures la plus longue est obligatoire |
| Prise de la dame | La dame peut traverser des cases vides avant et après la prise |
| Promotion | Pion atteignant la rangée 1–5 (blancs) ou 46–50 (noirs) |
| Règle des 50 coups | Partie nulle si aucune prise ni promotion en 50 coups |
| Pièces capturées | Restent sur le plateau jusqu'à la fin de la séquence de prise |

---

## Rate limiting

Les endpoints coûteux sont protégés par un limiteur glissant en mémoire (par IP) :

| Limite | Endpoints concernés |
|--------|---------------------|
| 5 req/min | `/api/game/{id}/analyze`, `/api/position/analyze` (Claude) |
| 20 req/min | `/api/game/{id}/ai-move`, `/api/position/best-move` (Scan) |
| 3 req/min | `/api/pdn/annotate`, `/api/opening-book/precompute` (batch) |

En cas de dépassement : `HTTP 429` avec message explicatif.

---

## Monitoring (Sentry)

Définir `SENTRY_DSN` dans les variables d'environnement pour activer Sentry. Sans cette variable l'application démarre normalement sans aucun SDK initialisé. Le `traces_sample_rate` est fixé à 10 % pour limiter les coûts.

---

## Tests unitaires

```bash
pip install -r requirements-dev.txt
pytest backend/tests/ -v
```

51 tests couvrent l'intégralité des règles FMJD : prise obligatoire, prise maximale, déplacements de dame, promotion, règle des 50 coups.

---

## Endpoints API principaux

### Partie
| Méthode | URL | Description |
|---------|-----|-------------|
| POST | `/api/game/new` | Créer une partie |
| GET | `/api/game/{id}` | État de la partie |
| POST | `/api/game/{id}/move` | Jouer un coup |
| GET | `/api/game/{id}/ai-move` | Coup suggéré par l'IA |
| POST | `/api/game/{id}/analyze` | Analyse Claude |
| POST | `/api/game/{id}/undo` | Annuler le dernier coup |
| POST | `/api/game/{id}/resign` | Abandonner |

### Analyse
| Méthode | URL | Description |
|---------|-----|-------------|
| POST | `/api/pdn/annotate` | Analyse coup par coup (batch Scan) |
| POST | `/api/pdn/import` | Importer un PDN |
| POST | `/api/position/analyze` | Analyser une position FEN (Claude) |
| POST | `/api/position/best-move` | Meilleur coup pour une position FEN (Scan) |

### Exercices
| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/exercises` | Liste des exercices |
| GET | `/api/exercise/{id}` | Détail d'un exercice |
| POST | `/api/exercise/{id}/check` | Vérifier une solution |

### Base d'ouvertures
| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/opening-book/continuations` | Coups du livre pour une position |
| POST | `/api/opening-book/build` | Lancer la construction de la base |
| GET | `/api/opening-book/players` | Chercher des joueurs sur Lidraughts |
| POST | `/api/opening-book/reeval` | Reprendre l'évaluation des positions non scorées |
| GET | `/api/opening-book/stats` | Statistiques de la base |

### Auth
| Méthode | URL | Description |
|---------|-----|-------------|
| POST | `/api/auth/register` | Créer un compte |
| POST | `/api/auth/login` | Connexion (retourne JWT) |
| GET | `/api/auth/me` | Profil utilisateur |
| GET | `/api/auth/me/stats` | Statistiques de jeu |

---

## Déploiement Railway

Le projet est configuré pour Railway via `railway.json` et `Dockerfile` :

```json
{
  "build": { "builder": "DOCKERFILE" },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/health"
  }
}
```

Le frontend est buildé (Vite) et servi statiquement par le backend FastAPI depuis `/frontend/dist`.

---

## Licence

Usage éducatif et personnel.
