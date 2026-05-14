# Feature : Suivi des erreurs récurrentes et révision ciblée

> **Statut** : en cours d'implémentation — branche `develop`
>
> Ce document est le contrat d'interface entre **dilf** (logique pédagogique)
> et **Draught Master** (persistence, API REST, interface utilisateur).
> Toute évolution de l'API dilf doit être documentée ici avant implémentation.

---

## 1. Objectif fonctionnel

Permettre au joueur de :

1. **Voir ses erreurs récurrentes** dans son profil (liste des motifs tactiques
   sur lesquels il perd régulièrement des points de chance de gain).
2. **Lancer une série d'exercices** ciblés sur un motif précis en un clic
   depuis le panneau d'analyse post-partie ou depuis son profil.
3. **Comprendre** ce qu'est le motif (explication textuelle + exemple).

---

## 2. Flux de données global

```
Partie analysée (POST /api/pedagogy/analyze-game)
  │
  ▼
dilf.assemble_verdict()  ──→  MoveVerdict.motifs : list[MotifMatch]
  │                                  ↑ role : "played" | "missed" | "suffered"
  │
  ▼
move_verdicts table  (game_id, move_number, motifs_json)
  │
  ▼
GET /api/pedagogy/profile/me
  │  ── storage.fetch_user_games_with_verdicts()
  │  ── dilf.aggregate_user_profile()
  ▼
UserProfileOut.weaknesses : list[{motif, missed, suffered, played, …}]
  │
  ▼
Frontend : WeaknessPanel  ──→  clic "Travailler →"
  │
  ▼
GET /api/pedagogy/motifs/{slug}
  │  ── motif_descriptions.MOTIFS[slug]
  │  ── storage.fetch_exercises_for_motif(slug)
  ▼
MotifDetailPage  (description + série d'exercices)
```

---

## 3. Ce que dilf fournit (ne pas réimplémenter côté Draught Master)

| Symbole | Module dilf | Rôle |
|---|---|---|
| `assemble_verdict()` | `pedagogy.verdicts.assembler` | Produit `MoveVerdict` avec motifs détectés |
| `ALL_DETECTORS` | `pedagogy.motifs` | 10 détecteurs, attribut de classe `name` |
| `aggregate_user_profile()` | `pedagogy.profile.aggregator` | Agrège `list[GameAnalysis]` → `UserProfile` |
| `compute_accuracy()` | `pedagogy.profile.aggregator` | Précision ``[0,1]`` sur une séquence de verdicts |
| `recommend_exercises()` | `pedagogy.profile.recommender` | Sélectionne exercices depuis un pool |
| `UserProfile` | `pedagogy.types` | Dataclass résultat du profil |

### Seuil de déclenchement des faiblesses (`dilf`)

```python
# pedagogy/profile/aggregator.py
_MOTIF_THRESHOLD = 3   # missed + suffered >= 3 pour figurer dans weaknesses
```

Un joueur n'aura de faiblesses visibles qu'après ~3 parties analysées.
Le panneau d'analyse post-partie permet toutefois de cliquer sur un motif
**immédiatement** (sans attendre le seuil).

### Motifs disponibles (10 au total)

| slug | Nom FR |
|---|---|
| `coup_royal` | Coup royal |
| `coup_turc` | Coup turc |
| `coup_de_talon` | Coup du talon |
| `envoi_a_dame` | Envoi à dame |
| `sacrifice` | Sacrifice |
| `prise_max_ratee` | Prise maximale ratée |
| `coup_philippe` | Coup Philippe |
| `coup_raphael` | Coup Raphaël |
| `coup_express` | Coup express |
| `coup_bonnard` | Coup Bonnard |

---

## 4. Ce que Draught Master implémente

### 4.1 Persistence (SQLite)

Tables existantes utilisées :

- **`move_verdicts`** — contient `motifs_json` par demi-coup
- **`exercise_tags`** — tags motif par exercice (rempli par le script de
  tagging automatique dilf)
- **`games`** — colonnes `user_id`, `user_side`, `status` ajoutées par migration

Aucune nouvelle table n'est nécessaire.

### 4.2 Tagging automatique des exercices

Script : `backend/pedagogy/scripts/tag_existing_exercises.py`

Exécuté au démarrage de l'application via `init_db()` (tâche asyncio
non-bloquante). Relance idempotente — ne modifie que les exercices dont
le tag set a changé.

### 4.3 Descriptions des motifs

Fichier : `backend/pedagogy/motif_descriptions.py`

Dict statique `MOTIFS[slug] → {name_fr, name_en, description_fr, description_en}`.
Maintenu côté Draught Master car il s'agit de contenu éditorial, pas de
logique de détection.

**À faire (dilf)** : si dilf veut exposer un `MOTIF_METADATA` officiel dans
`pedagogy.motifs.base`, Draught Master importera ce dict plutôt que d'en
maintenir un propre.

### 4.4 Endpoints REST

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/pedagogy/profile/me` | Profil de l'utilisateur connecté |
| `GET` | `/api/pedagogy/profile/{user_id}` | Profil d'un utilisateur (admin) |
| `GET` | `/api/pedagogy/profile/me/recommendations` | Exercices recommandés |
| `GET` | `/api/pedagogy/motifs/{slug}` | Infos motif + exercices associés |

#### `GET /api/pedagogy/motifs/{slug}` — réponse

```json
{
  "slug": "coup_de_talon",
  "name_fr": "Coup du talon",
  "name_en": "Heel shot",
  "description_fr": "...",
  "description_en": "...",
  "exercises": [
    {
      "id": 42,
      "name": "COMBINAISONS – D7",
      "initial_fen": "W:W...:B...",
      "solution_moves": ["32-28", "..."],
      "difficulty": 2
    }
  ]
}
```

#### `GET /api/pedagogy/profile/me` — réponse (via `UserProfileOut`)

```json
{
  "user_id": 1,
  "games_count": 5,
  "average_accuracy": 0.72,
  "strengths": [],
  "weaknesses": [
    {
      "motif": "coup_de_talon",
      "missed": 2.0,
      "suffered": 3.0,
      "played": 0.0,
      "threatened": 0.0,
      "total_severity": 4.2
    }
  ],
  "weakest_phase": "middlegame",
  "recommended_exercise_tags": ["coup_de_talon"]
}
```

### 4.5 Interface utilisateur

#### WeaknessPanel (dans le panneau profil latéral)

Affiche la liste des faiblesses avec fréquence et bouton "Travailler →"
qui ouvre `MotifDetailPage`.

#### MotifDetailPage (overlay plein écran)

1. En-tête : nom du motif + bouton retour
2. Description textuelle du motif
3. Liste des exercices taggés — "Commencer" → navigue vers l'exercice
   dans la bibliothèque existante

#### PedagogyPanel (extension)

Les motifs détectés dans un coup (indicateur `◆N`) sont cliquables → ouvre
`MotifDetailPage` pour ce motif.

---

## 5. Points d'extension futurs (non implémentés)

- **Suivi de progression par motif** : table `user_motif_progress` avec
  `(user_id, motif, exercises_done, last_seen)` — dilf pourrait exposer
  une fonction `update_motif_progress()`.
- **Exemples FEN** par motif : un `example_fen` dans `MOTIF_METADATA`
  dilf permettrait d'afficher un diagramme illustratif.
- **Difficulté adaptative** : `recommend_exercises()` dilf accepte déjà un
  pool pré-trié — Draught Master peut pré-trier par difficulté croissante
  et par taux de succès utilisateur.

---

## 6. Tâches restantes

- [ ] Peupler `exercise_tags` sur Railway (premier déploiement)
- [ ] Ajouter un `example_fen` par motif dans `motif_descriptions.py`
- [ ] Tests unitaires `aggregate_user_profile` avec fixtures SQLite
- [ ] **(dilf)** Exposer `MOTIF_METADATA` officiel dans `pedagogy.motifs`
- [ ] **(dilf)** Documenter le format `MotifMatch.role` dans `types.py`
