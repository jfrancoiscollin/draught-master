# Base de connaissances stratégique — pipeline diagrammes

> Documentation de référence du pipeline qui transforme les **positions
> extraites des diagrammes** des quatre manuels scannés (Sijbrands,
> Springer, Roozenburg, Keller) en fixtures et base de connaissances
> exploitables : bibliothèque de positions, base de connaissances
> thématique, exercices vérifiés, et prose interactive.
>
> Livré par les PR #118 et #119. Pour l'historique des décisions
> d'extraction (page-JPEG, crop, annotation FEN), voir
> [`STRATEGIE_DIAGRAMS_PLAN.md`](./STRATEGIE_DIAGRAMS_PLAN.md).

---

## 1. Vue d'ensemble

Les manuels scannés fournissent, par source, sous
`backend/strategy/pages/<source>/` :

| Fichier | Contenu | Produit par |
|---|---|---|
| `diagrams_manifest.json` | liste des diagrammes détectés `(page, number)` + crop/bbox | extracteurs de crops |
| `diagrams_fens.json` | FEN **vérifiées à la main** (source de vérité) | annotation manuelle |
| `diagrams_fens_auto.json` | FEN **auto-détectées** sur chaque crop (`_auto`) | `generate_auto_fens.py` |
| `diagram_sections.json` | métadonnées de chapitre par page (`Leçon N` + titre) | `extract_strategy_sections.py` |

À partir de ces sources, le pipeline construit quatre couches, chacune
bâtie sur la précédente :

```
diagrams_*.json (par source)
        │
        ▼
[1] position_library.json ........ socle : 1369 positions consolidées,
        │                          validées par le moteur (1308 valides)
        ├──────────────┬───────────────┐
        ▼              ▼               ▼
[2] strategic_kb   [3] generate_   [4] /diagram-fen (prose)
    66 thèmes          exercises       flag `valid` → pas de
    + tips enrichis    108 exercices   plateau cassé dans la prose
```

Tout le code vit dans **draught-master** (`backend/strategy/`). dilf
n'est pas modifié, mais son corpus prose (passages « Diagramme N ») est
le point d'ancrage côté frontend — voir §6.

---

## 2. Socle — bibliothèque de positions

**Module** : `backend/strategy/build_position_library.py` (offline) +
`backend/strategy/position_library.py` (accès runtime).
**Artefact** : `backend/strategy/position_library.json`.

`build_position_library.py` fusionne, par source, le manifeste + les FEN
(humaines prioritaires sur auto) + les sections, puis pour chaque
diagramme :

- passe la FEN dans `game_engine` pour enregistrer les **faits de
  légalité** : nombre de pièces/dames par camp, trait, nombre de coups
  légaux, prise disponible ;
- résout un **thème propre** par page (cf. §3) ;
- **flague invalide** toute position douteuse — voir la table ci-dessous.

### Critères d'invalidité

Une position est `valid: false` (et exclue des couches suivantes) si :

- plateau vide ou non parsable ;
- plus de 20 pièces d'un camp (artefact de sur-détection) ;
- aucun coup légal pour le trait ;
- **pion sur sa propre rangée de promotion** (pion blanc sur 1-5 ou pion
  noir sur 46-50 — il serait déjà dame : erreur sûre du détecteur). Champ
  `illegal_men` ; garde testée par `tests/test_fen_legality.py`.

### Bilan (généré le 2026-05-29)

| Source | Total | Valides | Humaines | Auto | Thématisées |
|---|---|---|---|---|---|
| SIJBRANDS | 513 | 487 | 62 | 451 | 508 |
| SPRINGER | 668 | 638 | 3 | 665 | 170 |
| ROOZENBURG | 73 | 70 | 15 | 58 | 59 |
| KELLER | 115 | 113 | 15 | 100 | 0 |
| **Total** | **1369** | **1308** | **95** | **1274** | **737** |

### Régénération

```bash
cd backend
python -m strategy.build_position_library            # toutes les sources
python -m strategy.build_position_library SIJBRANDS  # une seule
```

Déterministe et re-générable. `tests/test_position_library.py` contient
un **test de fraîcheur** : le JSON commité doit être identique à un
rebuild — un artefact périmé fait échouer la CI.

### Accès runtime

`position_library.py` charge le JSON une fois (`lru_cache`) et expose des
vues filtrées — `valid_positions(source, kind, with_capture)`,
`get_position(...)`, `themes(...)` — pour que les autres couches ne
retouchent jamais le format de fichier.

---

## 3. Taxonomie des thèmes

`diagram_sections.json` donne, par page, un `heading` (« Leçon 24 »,
« Thème 6 ») et un `title`. Le heading numéroté est fiable ; le `title`
dérive parfois vers une légende (« DIAGRAMME 1 »), une ligne de table des
matières ou une phrase tronquée.

`build_position_library._resolve_theme_titles` nettoie cela :

1. ne garde que les headings de type leçon/thème/chapitre numéroté ;
2. pour chaque heading, choisit le **titre propre le plus fréquent**
   (rejette les légendes `DIAGRAMME/Exercice`, les lignes TdM avec points
   de conduite, et les numéros de section nus type « 1.1 ») ;
3. les pages sans titre propre conservent leur position dans la
   bibliothèque mais sans thème.

Résultat : **66 thèmes propres** (Sijbrands ~49, Springer ~10,
Roozenburg ~8 ; Keller 0 — sa table des matières est mal extraite, ses
positions restent dans la bibliothèque sans thème).

---

## 4. Base de connaissances stratégique

### 4a. KB thématique

**Module** : `backend/strategy/strategic_kb.py`. C'est une vue pure sur
la bibliothèque (pas d'artefact à maintenir) qui regroupe les positions
valides par thème de leçon.

**Endpoints** (`backend/strategy/api.py`) :

- `GET /api/strategy/kb-themes[?source=…]` — une carte par thème :
  sources, leçons, nombre de positions, et 3 positions-exemples
  représentatives (humaines d'abord, dédupliquées par FEN).
- `GET /api/strategy/kb-theme?theme=…[&source=…][&limit=…]` — toutes les
  positions d'un thème (404 si thème inconnu).

### 4b. Tips enrichis de positions-exemples

**Module** : `backend/strategy/enrich_tips.py`.
**Artefact** : `backend/knowledge_base.json` (champ `example_positions`
ajouté aux tips).

Pour chaque tip de la base de connaissances, on attache les positions des
manuels qui **exhibent réellement son motif**, en réutilisant l'extracteur
de features de production (`scan_advisor._board_features`) et ses règles
(`phase` + `conditions` + `require_all`). Un exemple n'est attaché que si
la position déclencherait le tip en partie — **aucun matching textuel**.

Bilan : **68/79 tips enrichis**, 340 positions-exemples (humaines
d'abord, dédupliquées, plafonné à 5 par tip). Le contenu des tips est
inchangé par ailleurs.

**Affichage en jeu** : `scan_advisor._select_book_tip` remonte les
`example_positions` (plafonné à 3) ; `analyze_position` renvoie un
`book_tip` structuré ; le composant frontend partagé `TipExamples.tsx`
les rend en petits plateaux statiques, à la fois dans le panneau
d'analyse replié (`AnalysisPanel`) et dans la vue d'analyse complète
(`App.tsx`, mode *expanded*).

```bash
cd backend
python -m strategy.enrich_tips --dry-run   # rapport
python -m strategy.enrich_tips             # écrit knowledge_base.json
```

Idempotent ; `tests/test_enrich_tips.py` vérifie que chaque exemple
attaché matche son tip + un test de fraîcheur.

---

## 5. Exercices vérifiés

**Module** : `backend/strategy/generate_exercises.py` (mineur offline) +
`backend/strategy/exercises_loader.py` (lignes seedables).
**Artefact** : `backend/strategy/strategy_exercises.json`.

Les diagrammes sont majoritairement **positionnels** — fabriquer une
solution pour chacun enseignerait de mauvais coups. On n'émet donc un
exercice que lorsque le moteur trouve une issue **prouvée**, reconstruite
coup par coup et vérifiée par rejeu :

| `outcome` | Critère | Recherche |
|---|---|---|
| `win` | gain forcé par annihilation (toutes les pièces adverses prises) | depth 6 |
| `material` | le trait gagne ≥ 2 pions via un enchaînement de prises forcées et reste nettement devant | depth 6 + quiescence des prises |
| `endgame` | finale (≤ 18 pièces) gagnée par la technique : la ligne se termine par un gain pour le trait | depth 12, horizon 16 demi-coups |

Bilan : **108 exercices** (61 finales + 45 matériel + 2 annihilation),
sur Sijbrands (88) / Springer (19) / Keller (1). Chacun porte sa
provenance (`source`, `page`, `number`, `diagram_id`), son `outcome` et
son `material_gain`.

**Seed** : `exercises_loader.all_strategy_exercises()` produit des lignes
prêtes pour la table `exercises` (IDs 5001+, hors plage manuel_debutant
2001+, `book_id = manuel_<source>`). `db/schema.py` les upserte à l'init,
à côté des exercices du manuel Débutant.

```bash
cd backend
python -m strategy.generate_exercises            # toutes les sources (lent : plusieurs min)
python -m strategy.generate_exercises SIJBRANDS  # une seule
```

`tests/test_strategy_exercises.py` **rejoue chaque ligne** pour prouver
qu'elle est légale et qu'elle gagne (ou gagne le matériel annoncé).

---

## 6. Prose interactive

Le panneau « Apprendre » (`frontend/src/components/StrategyManualPage.tsx`)
affiche les passages du corpus **prose de dilf**. Quand un passage cite
« Diagramme N », le frontend résout la FEN via :

- `GET /api/strategy/diagram-fen?source=…&page=…&number=N` — renvoie
  `{fen, kind, valid}`. Les FEN humaines priment ; pour les sources
  *trusted-auto* (désormais les quatre), les FEN auto sont servies en
  `kind:"human"` (badge « non validé » retiré). Le détecteur Sijbrands
  atteint 99,86 % de précision par case.
- Le flag **`valid`** (issu de la bibliothèque) permet au frontend de
  **ne pas rendre** de plateau pour les ~3 % de FEN auto erronées —
  pas de damier cassé à côté du texte.

> Lien d'interop : les passages prose et leurs ancres « Diagramme N »
> viennent de dilf (`pedagogy/prose/fixtures/`). La résolution FEN et le
> rendu sont entièrement côté draught-master. dilf n'est pas modifié.

---

## 7. Régénérer toute la chaîne

Après toute mise à jour d'un `diagrams_fens*.json` :

```bash
cd backend
python -m strategy.build_position_library   # 1. socle (+ thèmes, légalité)
python -m strategy.enrich_tips              # 2. ré-enrichit knowledge_base.json
python -m strategy.generate_exercises       # 3. ré-mine les exercices (lent)
pytest tests/test_position_library.py \
       tests/test_fen_legality.py \
       tests/test_strategic_kb.py \
       tests/test_enrich_tips.py \
       tests/test_strategy_exercises.py -q
```

Les tests de fraîcheur garantissent que les artefacts commités
correspondent à un rebuild — sinon la CI échoue.

---

## 8. Fichiers de référence

| Rôle | Chemin |
|---|---|
| Builder socle | `backend/strategy/build_position_library.py` |
| Accès runtime | `backend/strategy/position_library.py` |
| Artefact socle | `backend/strategy/position_library.json` |
| KB thématique | `backend/strategy/strategic_kb.py` |
| Enrichissement tips | `backend/strategy/enrich_tips.py` |
| Mineur d'exercices | `backend/strategy/generate_exercises.py` |
| Loader d'exercices | `backend/strategy/exercises_loader.py` |
| Endpoints API | `backend/strategy/api.py` |
| Tip en jeu (backend) | `backend/scan_advisor.py` |
| Exemples (frontend) | `frontend/src/components/TipExamples.tsx` |
| Tests | `backend/tests/test_{position_library,fen_legality,strategic_kb,enrich_tips,strategy_exercises}.py` |
