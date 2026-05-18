# Panneaux pédagogiques — guide de lecture

> Toutes les visualisations décrites ici sont calculées par **dilf** sur
> chaque demi-coup analysé, puis affichées par **Draught Master**.
> Pour le contrat technique, voir [`PEDAGOGY_WEAKNESSES.md`](./PEDAGOGY_WEAKNESSES.md).

Quand tu analyses une partie ("🎓 Analyser la partie" dans la fiche d'une
partie importée), Draught Master t'expose **sept lentilles** sur la
position — chacune répond à une question précise. Ce document explique
chaque lentille, comment la lire, et ce qu'elle veut *vraiment* dire.

---

## 1. Bandeau résumé (au-dessus du plateau)

```
Phase milieu de jeu   Matériel +1   ⚠ 2 pièces en l'air   Menaces 3
```

| Élément | Réponse à |
|---|---|
| **Phase** | Où en est la partie ? `ouverture` (≤12 demi-coups) · `milieu de jeu` · `finale` (≤8 pièces ou dames des deux côtés) |
| **Matériel** | Qui a l'avantage matériel ? Convention : *point de vue blancs*, dames = 3 pions. `+1` = un pion d'avance pour les blancs. `0` = égalité. |
| **⚠ N pièces en l'air** | Combien de pièces sont capturables au prochain demi-coup ? Anneau rouge correspondant sur le plateau. |
| **Menaces N** *(togglable)* | Combien de captures l'adversaire peut jouer maintenant ? Clic → flèches rouges sur le plateau. |

**Phase ≠ phase ouverture des théoriciens.** Notre seuil est purement
mécanique (compteur de demi-coups + matériel) ; un coup de théorie
joué au 15ᵉ tour reste classé "milieu de jeu" parce qu'on a déjà
quitté la phase d'ouverture *temporellement*.

---

## 2. Anneau rouge — pièces qui pendent

Une pièce a un anneau rouge ⭕ si **l'adversaire pourrait la prendre au
prochain demi-coup**. C'est le signal le plus actionnable du panneau :
quand tu vois un anneau sur l'une de tes pièces, tu sais que tu viens
de jouer un coup qui l'expose.

Quand l'anneau est sur une pièce **adverse**, c'est l'inverse : tu as
une prise gratuite à jouer.

Important : l'anneau ne juge **pas** la qualité du coup. Sacrifier une
pièce volontairement crée un anneau temporaire ; les motifs de
combinaison (Sacrifice, Coup royal, etc.) sont une autre lentille.

---

## 3. Flèches rouges — menaces

Le toggle "Menaces N" affiche **toutes** les captures que l'adversaire
peut jouer en réponse. Si la prise est multiple, chaque saut est dessiné
comme une flèche distincte ; tu vois donc la *géométrie* du coup.

Quand l'utiliser : pour voir comment l'adversaire pourrait punir un coup
fragile, et pour t'entraîner à les anticiper.

Limite : si la position a 5+ captures possibles, le plateau devient
illisible. Le toggle est OFF par défaut pour cette raison.

---

## 4. Mini-grille Diagnostic — faiblesses positionnelles

Quatre familles de cases, comptées séparément pour chaque couleur :

| Famille | Définition | Pédagogie |
|---|---|---|
| **Isolés** | Pion sans aucune pièce amie sur les diagonales adjacentes | Vulnérable : tout déplacement le laisse à découvert |
| **Retardés** | Pion encore sur sa rangée de base alors que le reste du camp avance | Frein à la mobilité : empêche les pions avancés d'être soutenus |
| **Trous** | Case vide cernée par ≥ 3 pièces amies — faiblesse géométrique | Cible naturelle pour un poste adverse |
| **Postes** | Case avancée, soutenue diagonalement, à l'abri d'une prise simple | C'est une **force**, pas une faiblesse — les vraies bonnes cases |

**Cliquer sur un compteur ⬜N / ⬛N** → la case correspondante s'illumine
en jaune sur le plateau. La sélection persiste pendant que tu navigues
coup par coup : tu peux donc suivre l'**évolution** d'une faiblesse au
fil de la partie ("mon pion 23 est isolé pendant 8 demi-coups…").

---

## 5. Formations détectées

Cinq formations canoniques sont reconnues (signatures à 3 cases tirées
de Dubois) :

| Slug | Cases | À quoi ça ressemble |
|---|---|---|
| `classique_blancs` | 32, 37, 41 | Triangle d'attaque côté blanc |
| `classique_noirs`  | 10, 14, 19 | Symétrique noir |
| `roozenburg_blancs` | 28, 32, 37 | Pyramide centrale blanche |
| `roozenburg_noirs` | 14, 19, 23 | Pyramide centrale noire |
| `ghestem_blancs` | 27, 32, 38 | Diagonale large blanche |

**Cliquer sur un badge** → les 3 cases de la signature s'illuminent.
Pratique pour vérifier visuellement la formation.

**Faux positifs assumés.** La détection est purement set-based ("les 3
cases sont occupées par la bonne couleur"), donc à la position initiale
les Classiques sont déjà détectés. La détection sert d'**ancrage
visuel** plus que de classification fine.

---

## 6. Timeline matériel + score

Petit graphe SVG dans le panneau "Analyse pédagogique", entre le résumé
et la liste des coups. Deux courbes superposées :

- **Ligne ambre, épaisse** : le solde matériel (`material_balance`) au
  fil de la partie, échelle entière. Sa pente raconte l'histoire
  matérielle : sauts brusques = échanges ou prises ; plateaux = phases
  manœuvrières.
- **Ligne indigo, fine** : l'évaluation Scan (`score_before`) clipée à
  ±5 pions. C'est l'évaluation positionnelle complète (matériel +
  position + mobilité). Quand elle plonge alors que le matériel reste
  stable, c'est une **faute positionnelle** sans perte de bois.

**Le curseur ambre vertical** marque le demi-coup affiché sur le
plateau. **Cliquer dans le graphe** → le plateau saute à ce demi-coup.

À regarder : les divergences entre les deux lignes. Quand l'indigo
chute sans que l'ambre bouge, c'est une faute structurelle (poste perdu,
trou créé) qui ne se voit pas dans le compteur matériel. C'est souvent
**là** que la partie bascule.

---

## 7. Carte des faiblesses (panneau Profil)

Le panneau "Points faibles" sur la page profil contient, en bas, une
**carte 10×10** colorée par fréquence : pour chaque case, on compte
combien de fois elle est apparue dans une des 4 familles du Diagnostic
**à travers tes 30 dernières parties** (sur ta couleur uniquement —
les faiblesses de l'adversaire ne t'intéressent pas).

Cinq onglets :

| Onglet | Ce qui est compté | Lecture |
|---|---|---|
| **Toutes** | somme des 4 familles | Vue d'ensemble : où ton jeu est-il le plus instable ? |
| **Isolés** | uniquement pions isolés | Tes habitudes de placement faible |
| **Retardés** | pions arriérés | Pions de base que tu n'arrives pas à développer |
| **Trous** | trous dans ton dispositif | Cases que tu laisses régulièrement vides au mauvais moment |
| **Postes** | postes solides | **Vert, pas rouge** — c'est une force, ce sont tes points d'appui |

**Comment interpréter une case rouge vif** :

1. **Une case sur ta rangée arrière (46–50 pour blancs, 1–5 pour noirs)**
   apparaît souvent dans "Retardés" → c'est normal en début de partie,
   moins normal en finale (tu as tardé à activer tes pions de base).
2. **Une case du centre étendu (22–28, 32, 33)** récurrente en "Trous"
   → tu cèdes régulièrement le centre. À travailler.
3. **Une case d'aile (6–46 / 5–50)** en "Isolés" → tu joues des coups
   d'aile mal soutenus. Pense à renforcer avant d'engager.
4. **Une case avancée en vert dans "Postes"** → c'est ton style. Tu
   sais installer des points d'appui. Capitalise.

Limite : la carte n'est statistiquement parlante qu'à partir de
~10 parties analysées. En-dessous, le signal est trop sparse — un seul
match suffit à colorer une case en rouge vif. Le compteur "N parties"
en haut à droite te dit où tu en es.

---

## 8. Faiblesses partie-par-partie (PedagogyPanel)

Sous la timeline matériel, deux vues complémentaires sur la même donnée
sous-jacente : les listes `isolated_pawns_*` / `backward_pawns_*` /
`holes_*` / `outposts_*` calculées sur **chaque** demi-coup de la
partie courante.

### 8.1 Faiblesses distinctes (carte 10×10)

Même format visuel que la carte du profil, mais sur **une seule
partie**. Cinq onglets, ta couleur uniquement.

**Ce qui est compté** : une faiblesse persistante (par ex. trou sur 23
qui survit pendant 40 demi-coups) = **1 occurrence**. Si elle disparaît
puis réapparaît plus tard, +1. C'est un comptage de **streaks**, pas de
demi-coups.

**Pourquoi pas de demi-coups ?** Parce que ça gonflerait artificiellement
les faiblesses persistantes (un pion isolé qui dure 50 demi-coups
pèserait 50× plus qu'un trou tactique éclair, alors qu'on a affaire à
*une seule* erreur de placement chacune). La carte 10×10 répond à la
question "où ai-je eu des faiblesses dans cette partie" — pas "combien
de temps".

**Le warning "10 parties" du §7 ne s'applique pas ici** : on n'agrège
pas sur plusieurs parties, on décompose UNE partie. Le signal est
descriptif, pas statistique.

### 8.2 Gantt — durée des faiblesses

Si tu veux savoir *combien de temps* chaque faiblesse a duré, le Gantt
juste en-dessous le montre. Une ligne par case (top 12 par durée totale),
chaque streak = une barre horizontale colorée selon sa famille :

- 🟦 cyan = isolés
- 🟧 ambre = retardés
- 🟪 violet = trous
- 🟩 vert = postes

L'axe X = numéro de demi-coup (1 à N). Survoler une barre montre la
fenêtre exacte. Filtres : 5 boutons "Toutes / Isolés / Retardés / Trous /
Postes".

**À regarder** :

- Une barre qui couvre 50% de la partie sur un trou en 23 = "le centre
  était cédé sur la moitié de la partie".
- Plusieurs barres courtes décalées dans le temps = faiblesses
  tactiques transitoires, pas une faute structurelle.
- Une barre verte longue = poste solide tenu longtemps. C'est une
  réussite.

Les deux vues sont **complémentaires** : la carte dit *où*, le Gantt
dit *quand et combien de temps*.

---

## 9. Précision technique : d'où viennent ces nombres ?

Tous les panneaux ci-dessus sont alimentés par **un seul calcul** :
[`dilf.compute_features(state, half_move, engine) → Features`](https://github.com/jfrancoiscollin/dilf/blob/develop/pedagogy/features/formations.py).
Cette fonction est appelée par `assemble_verdict()` sur chaque
demi-coup, et le résultat est stocké dans
`MoveVerdict.features_after`, puis sérialisé dans
`move_verdicts.features_after_json` côté DB.

Conséquence pratique : si tu **réanalyses** une partie après une mise
à jour de dilf, les nouvelles familles (par exemple `hanging_pieces`
ajouté plus tard que `material_balance`) deviennent disponibles
rétroactivement.

Les parties analysées **avant** une mise à jour gardent leur ancien
snapshot ; le frontend défaut les champs manquants à `[]` ou `null`
sans crasher. Pour profiter des nouvelles lentilles sur une vieille
partie : "🎓 Analyser la partie" la relance proprement (et écrase
l'ancien `features_after_json`).

---

## 10. À lire ensuite

- [`PEDAGOGY_WEAKNESSES.md`](./PEDAGOGY_WEAKNESSES.md) — contrat dilf ↔ Draught Master
- [Code dilf, registry des motifs](https://github.com/jfrancoiscollin/dilf/blob/develop/pedagogy/motifs/) — liste exhaustive des coups tactiques détectés
- [Manuels Dubois embarqués](./livres/) — sources pédagogiques pour le mode Apprendre
