# Stratégie — plan d'action diagrammes

> Plan vivant pour amener les passages du panel **Stratégie** au format
> « leçon » (diagramme rendu à côté du texte, idéalement interactif).
> Mis à jour après merge des PRs #75, #76, #77 + Sprint 3.

---

## 1. État actuel (livré)

| Source            | Page-image       | Crop diagramme isolé        |
|-------------------|------------------|------------------------------|
| **SIJBRANDS**     | ✅ 187 JPGs ~14 MB | ✅ 513 crops, ~70 % couverture |
| **SPRINGER**      | ✅ 391 JPGs ~32 MB | ✅ 668 crops, ~65 % couverture (Sprint 4) |
| **ROOZENBURG**    | ✅ 68 JPGs ~5 MB  | ❌ pas de captions « DIAGRAMME N » dans le PDF (texte d'ouvertures principalement) |
| **KELLER**        | ✅ 93 JPGs ~7 MB  | ❌ diagrammes inline sans numérotation explicite (sections A/B/C…) — anchor différent à concevoir |

**UI** : `StrategyPanel.tsx` détecte « Diagramme N » / « DIAGRAMME N » dans le
texte du passage. Pour les 4 sources de `PAGE_IMAGE_AVAILABLE`, un bouton
_Voir Diagramme N_ ouvre une modal centrée. Le `<img>` essaie d'abord
`GET /api/strategy/diagram?source=…&page=…&number=N` (crop isolé) et
**tombe automatiquement sur** `GET /api/strategy/page-image?…&page=…`
via `onError` quand le crop n'a pas pu être extrait.

**Limite admise** : la classification des pièces n'est pas encore faite,
donc pas de FEN, pas de plateau interactif (Lane C, à venir).

---

## 2. Décisions à prendre

Trois axes orthogonaux à arbitrer **avant** de coder :

| Axe | Question | Options |
|---|---|---|
| **A. Couverture** | Étendre l'approche page-JPEG aux 3 autres PDFs ? | A1 : oui, tout le monde a au moins l'image · A2 : seulement les PDFs prioritaires |
| **B. Granularité** | Crop par diagramme (montrer juste le damier, pas la page) ? | B1 : page entière (statu quo) · B2 : crop par diagramme via détecteur calibré |
| **C. Format leçon** | Aller jusqu'au FEN extrait + plateau interactif ? | C1 : non (statu quo image) · C2 : oui pour 1 PDF pilote · C3 : oui pour tous |

L'effort grandit en escalier : **A < B < C**, et chacun est utile sans le
suivant. Mon avis : A2 (Springer + Roozenburg seulement, Keller plus tard)
suivi de B pour Sijbrands est le meilleur rapport effort/valeur perçue.

---

## 3. Lane A — Étendre l'approche page-JPEG aux autres PDFs

**Effort estimé :** 1-2 h par PDF, dont 80 % de génération automatique.

### Recette

1. Lister les pages référencées par les passages de la source :
   ```python
   from pedagogy.prose.fixtures.prose_passages_<source> import ALL_PASSAGES
   pages = sorted({p.page for p in ALL_PASSAGES})
   ```
2. Rendre chaque page en JPEG 600 px, qualité 80, via `pdftoppm` + `Pillow`
   (script ré-utilisable, voir snippet en annexe).
3. Bundler sous `backend/strategy/pages/<source>/page_NNNN.jpg`.
4. Ajouter la source à `PAGE_IMAGE_AVAILABLE` dans
   `frontend/src/components/StrategyPanel.tsx`.
5. Tests : étendre `test_strategy_api.py::test_page_image_*` pour couvrir la
   nouvelle source.

### Poids attendu du bundle

Estimations basées sur 187 pages Sijbrands ~14 MB :

| Source       | Pages référencées (à compter) | Bundle estimé |
|--------------|-------------------------------|---------------|
| SPRINGER     | TBD (commande `python -c …`)  | ~10-15 MB     |
| ROOZENBURG   | TBD                           | ~5-8 MB       |
| KELLER       | TBD                           | ~8-12 MB      |

Si la somme dépasse ~50 MB total dans le repo, basculer sur git-lfs ou
héberger les pages hors repo (S3, blob storage).

### Risque

Négligeable. `pdftoppm` est déterministe, la modal frontend ne change pas.

---

## 4. Lane B — Crop par diagramme (au lieu de page entière)

**Effort estimé :** 4-8 h pour Sijbrands seul (debug détecteur), puis 2-4 h par
PDF supplémentaire.

### Diagnostic acquis pendant la session

- `scripts/extract_diagrams.py::_detect_boards` (dilf, Dubois-tuned) renvoie
  **0 damier** sur Sijbrands p.48 : il cherche des blobs très sombres
  (`DARK_THRESHOLD ≈ 50`) ; les damiers Sijbrands ont des cases gris-clair et
  des bordures gris-moyen, pas du vrai noir.
- Custom detector écrit en session : `threshold=220`, bordures horizontales
  de ~265 px à 150 DPI, paires top/bottom à 240-290 px d'écart. **Fonctionne**
  mais **sur-détecte** : 26 boards trouvés sur p.47 là où 4-5 sont attendus.
  Cause probable : runs de lignes décoratives + dédupe trop tolérante.
- `find_boards_border_lines` et `find_boards_dark_squares` de draught-master
  (book_extraction) trouvent 0 boards sur Sijbrands aussi — seuils Dubois.

### Plan technique

1. **Reproduire le custom detector dans un script versionné**
   (`backend/strategy/extract_sijbrands_crops.py` ou dans dilf, à arbitrer).
2. **Resserrer la dédupe** : grouper les bboxes candidats par cluster (DBSCAN
   sur le centre, ou simple seuil de chevauchement IoU ≥ 0.5). Objectif :
   exactement le nombre de bboxes que la regex « DIAGRAMME N » prédit pour
   la page.
3. **Cross-check caption ↔ board** : compter les `DIAGRAMME N` dans le texte
   de la page (cf. `_trait_aux_count` style), `assert` que `len(boards) ==
   n_captions`, sinon log WARNING + fallback page entière pour cette page.
4. **Génération du manifest** : produire un JSON
   `backend/strategy/pages/sijbrands/manifest.json` qui mappe
   `diagram_id → { page, bbox, crop_path }` pour servir les crops.
5. **Endpoint backend** : `GET /api/strategy/diagram?source=SIJBRANDS&id=6`
   qui renvoie le crop précis du Diagramme 6 (ou tombe sur page entière si
   pas dans le manifest).
6. **Front** : la modal préfère le crop si disponible, sinon page entière.

### Risque

Modéré. Le custom detector est fragile aux changements de mise en page entre
chapitres. Mitigation : tolérer un fallback page entière, et logger le diff
caption-vs-boards en CI pour suivre la dérive.

---

## 5. Lane C — Format leçon complet (FEN + plateau interactif)

**Effort estimé :** 2-4 jours par PDF, dont l'essentiel sur la classification
des pièces.

### Pipeline cible

```
PDF → pdftoppm → page PNG
         ↓
[1] détecteur de bbox damier (Lane B)
         ↓ bbox
[2] sampler 10×10 cases → 50 cases jouables (dark squares uniquement)
         ↓
[3] classifier {empty, white_pawn, black_pawn, white_king, black_king}
         ↓
[4] reconstruction FEN (notation FMJD : W:Wxx,yy,zz...:Bxx,yy,zz...)
         ↓
[5] sanity check (nombre de pièces ≤ 20 par camp, dame ≤ 4, etc.)
         ↓
fixture passages_<source>_diagrams.py — { diagram_id: FEN }
```

### Verrous techniques

- **Classification des pièces (étape 3)** — le plus dur :
  - Sur Sijbrands, distinguer une dame blanche d'une dame noire et d'une case
    vide demande une calibration **par PDF**. L'intensité moyenne au centre
    de la case ne suffit pas (cas (8,0) intensité 239 sur Sijbrands p.48 :
    vide ou pion blanc sur case claire ?).
  - Options :
    1. Heuristique calibrée à la main (rapide, fragile)
    2. Template matching (matrice de référence pour chaque type de pièce
       cropée d'un diagramme connu)
    3. Mini-CNN (overkill mais robuste — quelques centaines d'exemples
       suffisent pour 5 classes)
- **Annotation de référence** — pour valider/calibrer : il faut
  ~10 diagrammes par PDF dont le FEN est connu (saisi à la main) pour mesurer
  la précision du pipeline avant déploiement.
- **Mapping caption → FEN** : pareil que Lane B étape 3.

### Frontend

- Réutiliser `<Board>` (existant pour les leçons) avec une prop `fen`.
- Modal devient un mini-éditeur statique : pas de coups, juste la position.
  Plus tard, on peut greffer les coups annoncés dans le texte (« 1.39-33!
  28x39 2.43x34. ») comme animation jouable.

### Risque

Élevé. Aucun garant que le pipeline généralise du PDF Dubois (sur lequel il
marche) à Sijbrands sans réécriture lourde. Le risque cache aussi un piège
de **silence à dérive** : un FEN faux à 5 % est pire qu'une image, parce
que l'utilisateur fait confiance au plateau.

**Si on prend cette lane** : commencer par Sijbrands seul, mesurer la précision
sur 30 diagrammes annotés à la main, ne déployer qu'au-dessus de 95 %.

---

## 6. Séquencement recommandé

```
Sprint 1 (2-3 h)  : Lane A pour Springer + Roozenburg
                    → 4 sources couvertes par l'approche page-JPEG
Sprint 2 (1-2 h)  : Lane A pour Keller (selon priorité utilisateur)
                    → uniformité totale
Sprint 3 (1 jour) : Lane B sur Sijbrands seul (le PDF avec le plus de
                    passages → meilleur ROI)
Sprint 4 (2-4 j)  : Lane C pilote Sijbrands, avec annotation manuelle
                    de 30 diagrammes + mesure de précision
Sprint 5+         : Lane C autres PDFs si Sprint 4 valide la faisabilité
```

L'utilisateur peut s'arrêter après n'importe quel sprint et garder une UX
cohérente.

---

## 7. Punch list ouverte

- [ ] Compter `len(pages_référencées)` pour Springer, Roozenburg, Keller
      (commande Python en §3) — avant de chiffrer le bundle.
- [ ] Décider du stockage des JPGs si le total dépasse ~50 MB
      (git-lfs vs blob externe).
- [ ] Annoter 10 diagrammes Sijbrands à la main (FEN attendu) pour préparer
      Lane C même si on ne l'attaque pas tout de suite — ça débloque la
      mesure de précision le jour venu.
- [ ] Vérifier l'opportunité d'unifier `extract_diagrams.py` (dilf) et
      `book_extraction/board_detection.py` (draught-master). Aujourd'hui les
      deux co-existent, avec des seuils différents, ce qui rendra Lane B/C
      pénible à maintenir.
- [ ] Documenter la regex « Diagramme N » du frontend dans un test : si
      l'OCR (ou la prose) change le format pour « fig. N », le bouton
      disparaît silencieusement.

---

## Annexe — Snippet de génération JPEG (Lane A)

À placer en script ré-utilisable (chemin à arbitrer) :

```python
"""Render every <SOURCE> page mentioned in a passage as JPEG 600 px."""
import subprocess, tempfile
from pathlib import Path
from PIL import Image
from pedagogy.prose.fixtures.prose_passages_<source> import ALL_PASSAGES

PDF = Path("docs/corpus/<source>.pdf")
OUT = Path("backend/strategy/pages/<source>")
OUT.mkdir(parents=True, exist_ok=True)

for page in sorted({p.page for p in ALL_PASSAGES}):
    out = OUT / f"page_{page:04d}.jpg"
    if out.exists():
        continue
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([
            "pdftoppm", "-r", "100", "-f", str(page), "-l", str(page),
            "-png", str(PDF), f"{td}/p",
        ], check=True, capture_output=True)
        img = Image.open(next(Path(td).glob("p-*.png"))).convert("RGB")
        if img.width > 600:
            img = img.resize((600, int(img.height * 600 / img.width)), Image.LANCZOS)
        img.save(out, "JPEG", quality=80, optimize=True)
```
