# AI-Draught — Entraînement au jeu de dames international

Application web d'entraînement au jeu de dames international (100 cases, règles FMJD) avec IA minimax et analyse par Claude.

## Fonctionnalités

- Plateau 10x10 interactif avec règles FMJD complètes (prise obligatoire, prise maximale)
- IA minimax avec élagage alpha-bêta (profondeur configurable 1-8)
- Analyse de position par Claude (claude-sonnet-4-6)
- 13 exercices tactiques et stratégiques
- Historique des parties avec relecture
- Interface en français

## Prérequis

- Python 3.11+
- Node.js 18+
- Clé API Anthropic

## Installation

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# Éditez .env et ajoutez votre ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

L'application sera accessible sur http://localhost:5173

## Structure du projet

```
Ai-draught/
├── backend/
│   ├── game_engine.py      # Moteur de jeu (règles FMJD)
│   ├── ai_engine.py        # IA minimax avec alpha-bêta
│   ├── claude_advisor.py   # Intégration Claude API
│   ├── database.py         # Base SQLite + exercices
│   ├── models.py           # Schémas Pydantic
│   ├── main.py             # API FastAPI
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/     # Composants React
│       ├── api/            # Client API
│       ├── types.ts        # Types TypeScript
│       └── App.tsx         # Application principale
└── .env.example
```

## Règles implémentées

- Prise obligatoire
- Prise maximale (FMJD)
- Dames se déplaçant sur toute la diagonale
- Pièces capturées restant sur le plateau jusqu'à fin de séquence
- Promotion aux rangées 1-5 (blancs) et 46-50 (noirs)
