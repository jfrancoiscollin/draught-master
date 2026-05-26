# Manuel Débutant — Le jeu de dames international (FMJD 10×10)

*Manuel pédagogique du projet Draught Master, niveau Débutant.*
*166 positions illustrent les règles, les méthodes et les principaux
mécanismes combinatoires du jeu de dames international.*

---

## Préface

Ce manuel est conçu pour quelqu'un qui débute au jeu de dames
international, qu'il sache déjà jouer aux dames anglaises (variant 8×8,
règles différentes) ou qu'il découvre complètement le jeu. Il vise à
faire passer progressivement le lecteur de **« je connais les règles »**
à **« je vois venir les combinaisons usuelles »**.

Chaque position est référencée par un identifiant de la forme
`BEG_CHnn_mmm` (par exemple `BEG_CH03_001`) qui pointe vers une
fixture Python exploitable par le moteur du framework — chaque exercice
est donc directement testable au damier informatique.

**Sources** : 152 des 166 positions sont extraites de l'ouvrage
*Apprentissage Combinaisons* de Jean-Pierre Dubois (référence francophone
contemporaine). Les 14 restantes se répartissent en 12 positions de
connaissance générale (règles canoniques, positions standardisées) et
2 schémas inventés à fin pédagogique.

**Plan du manuel** :

1. La notation des cases (BEG_CH01)
2. Les règles du jeu (BEG_CH02)
3. Les combinaisons en deux temps (BEG_CH03)
4. Le collage et l'envoi à dame combinés (BEG_CH04)
5. L'envoi à dame (BEG_CH05)
6. La méthode des points de contact (BEG_CH06)
7. Les temps de repos créés par une attaque (BEG_CH07)
8. La création des temps de repos (BEG_CH08)
9. Le coup de l'Express (BEG_CH09)
10. Le coup de Ricochet (BEG_CH10)
11. Le coup de Rappel (BEG_CH11)
12. Le coup Renversé (BEG_CH12)
13. Le coup Napoléon (BEG_CH13)
14. Le coup de la Trappe (BEG_CH14)
15. Le coup de Talon (BEG_CH15)
16. Le coup Philippe (BEG_CH16)

Les chapitres 1 et 2 posent le vocabulaire, les chapitres 3 à 8
introduisent les **mécanismes fondamentaux**, les chapitres 9 à 16
détaillent les **coups nommés** qui forment le bagage technique d'un
joueur de niveau club.

---

## Chapitre 1 — La notation des cases

Le damier international comporte **100 cases** (10×10), dont seules les
**50 cases sombres** sont utilisées. Ces 50 cases sont numérotées de
**1 à 50** de gauche à droite et de haut en bas, **depuis le côté noir**
(haut du diagramme).

Voir `BEG_CH01_001` (position initiale standard) : les noirs occupent
les cases 1 à 20, les blancs les cases 31 à 50. Les rangées 21-30 sont
vides. Le trait est aux blancs.

Voir `BEG_CH01_002` (position après le premier coup blanc `32-28`) :
le pion blanc de la case 32 a glissé sur la case 28, et c'est
maintenant aux noirs de jouer.

### Notation des coups

- **Coup simple** (déplacement non capturant) : `cd-cf` où `cd` est la
  case de départ et `cf` la case finale. Exemple : `32-28` signifie
  « le pion en 32 se déplace en 28 ».
- **Coup de capture (rafle)** : `cd×cf` où `cd` est la case de départ
  et `cf` la case d'arrivée. Les cases intermédiaires et les pièces
  capturées ne sont pas explicitement notées — elles se déduisent
  géométriquement. Exemple : `32×16` signifie « le pion 32 effectue
  une rafle qui le mène en case 16 ». Selon la position, cette rafle
  peut capturer un, deux, trois pions ou plus.
- **Parenthèses autour d'un coup** : indique que c'est l'**adversaire**
  qui joue ce coup-là. Convention systématique chez Dubois.
- **Le trait** : indiqué par `W` (blanc) ou `B` (noir) en tête d'une
  notation FEN.

### Notation FEN

La notation FEN dames a la forme :

```
<trait>:W<cases blancs>:B<cases noirs>
```

Les dames sont préfixées d'un `K`. Exemple : `W:W31,32,K40:B7,K12,18`
signifie « trait aux blancs ; pions blancs en 31 et 32, dame blanche
en 40 ; pion noir en 7, dame noire en 12, pion noir en 18 ».

---

## Chapitre 2 — Les règles du jeu
<!-- pedagogy-motifs: prise_max_ratee -->

### 2.1. Déplacement des pions

Un pion se déplace **d'une case** en diagonale, **vers l'avant
uniquement** (vers le camp adverse). Pour un pion blanc, « vers l'avant »
signifie vers les cases de numéros plus petits ; pour un pion noir, vers
les cases de numéros plus grands.

Voir `BEG_CH02_001` : le pion blanc en case 35 (à l'angle droit du
damier) ne peut se déplacer qu'**en 30** — c'est sa seule case
diagonale vers l'avant disponible, le bord droit du plateau bloque
toute autre option. Voir aussi
`BEG_CH02_002` : le pion blanc en 22 ne peut **pas** reculer en 27 ou 28
librement ; ses seuls coups légaux sont 22-17 et 22-18 (vers l'avant).

### 2.2. Capture (prise simple)

Un pion **capture en sautant** par-dessus un pion adverse adjacent en
diagonale, à condition que la case derrière (le « champ d'atterrissage »)
soit **vide**. La capture peut se faire **en avant comme en arrière**
(contrairement au déplacement normal). Le pion capturé est retiré du
damier **à la fin de la séquence de prise**, pas pendant.

Voir `BEG_CH02_003` : le pion blanc 31 saute par-dessus le pion noir 27
et atterrit en 22 (notation `31×22`). Voir aussi `BEG_CH02_004` pour
illustrer la **capture vers l'arrière** : le pion blanc 22 saute le
noir 27 vers l'arrière et atterrit en 31 (notation `22×31`) — ce qui
serait interdit pour un coup simple.

### 2.3. Rafle (capture multiple)

Si après avoir capturé un pion, le pion captureur peut **immédiatement
en capturer un autre** (en sautant à nouveau), il **doit** le faire. Il
peut ainsi enchaîner plusieurs sauts dans la même séquence. C'est ce
qu'on appelle une **rafle**.

Voir `BEG_CH02_005` : le pion blanc 31 saute le noir 27 (atterrit en 22),
puis enchaîne en sautant le noir 17 pour atterrir en 11. Notation
`31×11`, deux pions noirs capturés en une seule séquence.

### 2.4. Prise obligatoire

Quand un pion ou une dame **peut capturer**, la capture est
**obligatoire**. Le joueur ne peut pas refuser de prendre. C'est l'une
des règles les plus distinctives du jeu de dames international.

Voir `BEG_CH02_006` : le pion blanc 31 ne peut pas jouer 31-26 (coup
simple) parce que la prise `31×22` du noir 27 est disponible — il doit
prendre, même s'il préférerait jouer ailleurs.

### 2.5. Prise maximale (règle du nombre)

Quand **plusieurs captures** sont possibles, le joueur doit choisir
celle qui **capture le maximum de pièces**. Si deux rafles capturent le
même nombre de pièces, le joueur choisit librement (sauf cas spéciaux
documentés dans la règlementation FMJD).

Voir `BEG_CH02_007` : depuis la position W{31, 38} B{23, 27, 33}, le
blanc a deux captures possibles — `31×22` ne prend qu'un seul pion (le
27), tandis que `38×18` prend deux pions (33 et 23). La rafle `38×18`
est **obligatoire** car elle capture le plus.

### 2.6. Promotion en dame

Un pion qui atteint la **dernière rangée adverse** (cases 1-5 pour les
blancs, 46-50 pour les noirs) **promeut en dame**. La promotion a lieu
uniquement si le pion **s'arrête** sur la dernière rangée. Si une rafle
fait traverser la dernière rangée sans s'y arrêter, **il n'y a pas
promotion** — c'est la fameuse règle du « non-soufflage de la dame ».

Voir `BEG_CH02_008` : le pion blanc 6 joue `6-1` et devient dame en
arrivant sur la première rangée.

### 2.7. La dame — déplacement et capture

La **dame** se déplace **librement** le long d'une diagonale, sur
**autant de cases libres** qu'elle veut (similaire au fou aux échecs).
Pour capturer, elle saute par-dessus un pion adverse sur sa diagonale et
peut **atterrir sur n'importe quelle case libre derrière**.

Voir `BEG_CH02_009` : la dame blanche en 32 peut glisser sur n'importe
quelle case libre des 4 diagonales qui la traversent. Voir
`BEG_CH02_010` : la dame blanche en 46 saute le pion noir 23 et choisit
sa case d'atterrissage parmi celles libres après lui sur la diagonale.

### 2.8. Non-soufflage (les captures restent jusqu'à la fin de la rafle)

Les pions capturés au cours d'une rafle **restent sur le plateau**
jusqu'à ce que la rafle soit complètement terminée. Conséquence : le
même pion ne peut pas être capturé deux fois dans une rafle, et la
trajectoire peut s'en trouver bloquée.

Voir `BEG_CH02_011` : la position W{23} B{18, 19, 28, 29} illustre cette
règle — le blanc 23 ne peut pas faire de boucle qui re-saute un pion
déjà capturé, ce qui limite ses trajectoires possibles.

### 2.9. Règle des 50 coups (nullité)

Si pendant **50 coups** consécutifs aucun pion n'est capturé ni promu,
la partie est déclarée **nulle**. Cette règle empêche les parties qui
pourraient tourner indéfiniment.

Voir `BEG_CH02_012` : finale dame contre dame (W_king{28} vs B_king{23})
— sans intervention extérieure, ces deux dames pourraient se poursuivre
indéfiniment. La règle des 50 coups conclut la partie en nulle.

---

## Chapitre 3 — Les combinaisons en deux temps

Une **combinaison** est un enchaînement forcé de coups qui aboutit à un
gain matériel ou positionnel. Les combinaisons les plus simples se font
en **trois demi-coups** : un sacrifice blanc, une prise forcée noire,
puis une rafle blanche.

Le schéma générique est :

> **1.** Le blanc sacrifie un (ou plusieurs) pion.
> **2.** Le noir doit prendre (prise obligatoire).
> **3.** Le blanc effectue une rafle qui capture autant ou plus de
> pions, avec en bonus un avantage positionnel décisif.

Les 10 exercices de ce chapitre sont les D1 à D10 de la page 6 du livre
*Apprentissage Combinaisons* de Dubois. Ils illustrent trois mécanismes
fondamentaux : la **prise majoritaire**, le **collage**, et le **coup
de Mazette**. Toutes les fixtures sont `verified=true` au moteur Scan
(cf `scan/scan_analysis_debutant.json`) ; chaque sous-section se clôt
par un tableau **Validation Scan** donnant le premier coup recommandé,
l'évaluation finale et la profondeur d'analyse. Une éval `+99` signale
un gain forcé annoncé par Scan, pas une avance matérielle littérale —
convention détaillée au §7.3.

### 3.1. La prise majoritaire

C'est le mécanisme de base. Le sacrifice blanc force le noir à effectuer
une **prise multiple** (plusieurs pions à la fois) par la règle du
nombre, ce qui dégarnit son camp et ouvre la voie à une rafle blanche
encore plus longue.

Exemple canonique — `BEG_CH03_001` (Dubois D1) :

> `published_notation` Dubois : `26-21 (17×28) 43×3`

Le sacrifice blanc `26-21` est gobé par le noir 17 qui doit prendre par
la règle de prise majoritaire (3 pions capturés). La rafle blanche
finale `43×3` traverse la grande diagonale jusqu'à la promotion,
capturant les pions 38, 28, 19 et 9 (cf `final_move.captures` de la
fixture).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH03_001` | `26-21` | +99.97 | 99 | — |
| `BEG_CH03_003` | `33-29` | +99.77 | 34 | — |
| `BEG_CH03_005` | `37-31` | +99.85 | 99 | — |
| `BEG_CH03_006` | `34-29` | +99.81 | 68 | — |
| `BEG_CH03_008` | `33-29` | +99.85 | 99 | — |
| `BEG_CH03_009` | `44-39` | +99.87 | 99 | — |
| `BEG_CH03_010` | `34-30` | +5.97 | 32 | — |

`published_notation` Dubois pour les variantes additionnelles :
`BEG_CH03_003` `33-29 (23×21) 26×10`, `BEG_CH03_005`
`37-31 (27×20) 25×5`, `BEG_CH03_006` `34-29 (25×32) 29×38`,
`BEG_CH03_008` `33-29 (24×31) 36×20` (sacrifice à 3 pions),
`BEG_CH03_009` `44-39 (25×43) 48×10`, `BEG_CH03_010`
`34-30 (23×32) 30×37`.

### 3.2. Le collage

Mécanisme plus subtil : quand le noir attaque **deux pions blancs**,
un blanc se sacrifie sur la case-clé de l'attaque, forçant le noir à
une prise majoritaire qui ouvre la rafle blanche.

Exemple — `BEG_CH03_004` (Dubois D4) :

> `published_notation` Dubois : `34-29 (23×21) 29×7`

Le sacrifice `34-29` transforme la menace adverse (configuration de
départ documentée par `claude_notes` de la fixture) en combinaison
gagnante ; la rafle finale `29×7` capture 4 pions noirs et atteint la
promotion en case 7 (cf `final_move.captures` = 12, 13, 14, 24).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH03_004` | `34-29` | +99.81 | 71 | — |
| `BEG_CH03_007` | `33-29` | +5.62 | 30 | — |

`published_notation` Dubois pour `BEG_CH03_007` :
`33-29 (17×37) 29×18` (collage canonique sur attaque à 2 pions).

### 3.3. Le coup de Mazette

Premier des **coups nommés** rencontrés dans ce manuel : un sacrifice
central qui contraint l'adversaire à une prise, ouvrant une rafle sur
la grande diagonale.

Exemple — `BEG_CH03_002` (Dubois D2) :

> `published_notation` Dubois : `28-22 (17×28) 32×5`

Le sacrifice `28-22` force le noir 17 à prendre par `17×28`. La rafle
blanche finale `32×5` capture 3 pions noirs (10, 19, 28 — cf
`final_move.captures`) et atteint la promotion en case 5 sur la grande
diagonale.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH03_002` | `28-22` | +99.97 | 99 | — |


---

## Chapitre 4 — Le collage et l'envoi à dame combinés
<!-- pedagogy-motifs: envoi_a_dame, coup_turc -->

Le **collage** introduit au chapitre 3 (§3.2) prend toute sa puissance
quand il est combiné à un **envoi à dame** : on sacrifie un pion qui
arrive à la dernière rangée et se promeut, puis on récupère une dame
adverse qu'on capture avec avantage. C'est l'une des combinaisons les
plus spectaculaires du répertoire.

Les 11 exercices viennent des chapitres 6 et 7 de Dubois (pages 20-25).
Toutes les fixtures sont `verified=true` au moteur Scan (cf
`scan/scan_analysis_debutant.json`) ; chaque sous-section se clôt par
un tableau **Validation Scan** donnant le premier coup recommandé,
l'évaluation finale et la profondeur d'analyse.

### 4.1. Le collage en 3 temps (exemple introductif)

L'exemple narratif du chapitre montre la structure CONTACT-PRISE-COLLAGE-
PRISE-RAFLE qui définit le collage.

Exemple — `BEG_CH04_001` (Dubois ch6 intro) :

> `published_notation` Dubois : `37-31 (26x17) 39-34 (21x43) 34x5`

Premier sacrifice `37-31`, prise forcée noire, puis le second sacrifice
`39-34` (le « collage » proprement dit) crée le point d'appui exploité
par la rafle `34×5` (cf `final_move.path = 34→23→12→3→14→5`, captures
8, 9, 10, 18, 29 — `claude_notes` mentionne un coup turc par 14).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH04_001` | `37-31` | +13.72 | 28 | — |

### 4.2. Prise majoritaire et collage classique

Plusieurs exercices de Dubois ch6 illustrent la prise majoritaire ou
le collage en 3 temps sans envoi à dame.

`published_notation` Dubois pour les fixtures de cette section :
- `BEG_CH04_002` (ch6 D1, prise majoritaire) : `25-20 (15x31) 36x20`
  (cf `claude_notes` : Dubois imprime `(15x21)`, vraie notation
  `(15x31)` — coquille R004)
- `BEG_CH04_003` (ch6 D4, gambit à 2 pions) : `27-21 (16x18) 28-23`
  (combinaison atypique, `final_move=None`)
- `BEG_CH04_004` (ch6 D6, collage classique) :
  `32-27 (21x23) 34-29 (17x39) 29x16`
- `BEG_CH04_008` (ch7 D2, collage à 4 pions) : `29-23 (26x30) 23x1`

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH04_002` | `25-20` | +3.50 | 31 | — |
| `BEG_CH04_003` | `27-21` | +4.23 | 31 | — |
| `BEG_CH04_004` | `32-27` | +5.33 | 30 | — |
| `BEG_CH04_008` | `29-23` | +99.77 | 28 | — |

### 4.3. Collage avec élimination préalable / coup royal

Certains collages demandent d'éliminer d'abord un pion gêneur.

Exemple — `BEG_CH04_005` (Dubois ch6 D7) :

> `published_notation` Dubois : `29-24 (22x33) 32-28 (19x39) 28x6`

Le premier sacrifice `29-24` est suivi de la prise noire, puis le
collage `32-28` ouvre la rafle `28×6` (cf `final_move.path =
28→19→8→17→6`, captures 11, 12, 13, 23).

Le **coup royal** est une variante célèbre de collage avec rafle
aboutissant en case 7. Exemple — `BEG_CH04_006` (Dubois ch6 D9) :

> `published_notation` Dubois : `27-22 (18x27) 32x21 (23x34) 40x7`

`final_move.path = 40→29→20→9→18→7` avec 5 captures (12, 13, 14, 24, 34
— cf `claude_notes` : motif tactique nommé, détecteur dédié dans
`pedagogy/motifs/coup_royal.py`).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH04_005` | `29-24` | +4.55 | 27 | — |
| `BEG_CH04_006` | `27-22` | +99.83 | 99 | — |

### 4.4. Envois à dame combinés au collage

Le mécanisme typique : un pion se sacrifie sur la dernière rangée,
promeut en dame, et la dame est ensuite ramenée par un nouveau
sacrifice pour servir de cible à la rafle finale.

Exemple — `BEG_CH04_007` (Dubois ch6 D10, Rustenburg-van Dartelen 1934) :

> `published_notation` Dubois : `38-32 (27x49) 34-30 (49x24) 29x7`

Le sacrifice `38-32` force le noir à promouvoir en dame (`27x49`), puis
le collage `34-30` ramène la dame sur la diagonale par `(49x24)` où la
rafle blanche `29×7` la capture (`final_move=None` car le module pion-
only ne reconstruit pas les rafles de dame, cf `claude_notes` et R007).

`published_notation` Dubois pour les variantes additionnelles :
- `BEG_CH04_009` (ch7 D5, triple mécanisme — `final_move=None`) :
  `28-23 (19x48) 17-12 (48x19) 12x1`

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH04_007` | `38-32` | +8.16 | 28 | — |
| `BEG_CH04_009` | `28-23` | +99.91 | 99 | — |

### 4.5. Combinaisons longues à plusieurs phases (coup de mazette)

Certaines combinaisons enchaînent plusieurs collages successifs avant
la rafle finale.

Exemple — `BEG_CH04_010` (Dubois ch7 D8) :

> `published_notation` Dubois : `34-29 (23x25) 27-22 (17x28) 32x3`

Deux sacrifices `34-29` puis `27-22` enchaînés forcent chacun une prise
majoritaire noire, puis la rafle `32×3` capture 3 pions et promeut en
dame (cf `final_move.path = 32→23→14→3`, captures 9, 19, 28 ;
`claude_notes` : coquille PDF `31x3` corrigée en `32x3`, R006).

`published_notation` Dubois pour `BEG_CH04_011` (ch7 D9, variante
symétrique) : `28-22 (18x36) 24-19 (14x23) 29x27`.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH04_010` | `34-29` | +99.81 | 99 | — |
| `BEG_CH04_011` | `28-22` | +5.09 | 30 | — |

---

## Chapitre 5 — L'envoi à dame
<!-- pedagogy-motifs: envoi_a_dame -->

L'**envoi à dame** est la promotion *volontaire* d'un pion par
sacrifice. On accepte de donner un pion (qui se promeut), pour
exploiter la dame nouvellement créée — ou pour piéger la dame adverse
qu'on récupère ensuite.

Ce chapitre approfondit le mécanisme déjà rencontré au chapitre 4,
avec 10 exercices issus du chapitre 4 de Dubois (pages 14-16). Les
fixtures contenant une rafle de dame ont `final_move=None`
(limitation R007 du module pion-only).

### 5.1. Envois à dame narratifs (3 et 5 temps)

Les deux exemples narratifs du chapitre 4 Dubois montrent les schémas
de base.

Exemple — `BEG_CH05_001` (Dubois ch4 intro, 3 temps) :

> `published_notation` Dubois : `36-31 (26x46) 42-37 (46x39) 43x5`

Le sacrifice `36-31` force le noir à promouvoir en dame en 46, puis
`42-37` ramène la dame sur la diagonale (`46x39`) où la rafle blanche
`43×5` la capture (cf `claude_notes` : `final_move=None`, R007).

Exemple — `BEG_CH05_002` (Dubois ch4 intro 2, 5 temps en 3 phases) :

> `published_notation` Dubois : `33-29 (24x33) 38x18 (13x22) 37-31 (26x48) 40-35 (48x30) 35x4`

`explanation` de la fixture distingue trois phases : élimination
(`33-29 (24x33) 38x18 (13x22)`), envoi à dame (`37-31 (26x48) 40-35
(48x30)`), rafle finale (`35x4`).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH05_001` | `36-31` | +5.11 | 22 | — |
| `BEG_CH05_002` | `33-29` | +99.79 | 87 | — |

### 5.2. Prises majoritaires consolidantes (D1, D2, D3, D5, D7)

Dubois mêle dans ce chapitre des exercices de prise majoritaire qui
consolident les acquis sans envoi à dame.

Exemple — `BEG_CH05_003` (Dubois ch4 D1, coup royal sous sa forme la
plus simple) :

> `published_notation` Dubois : `33-28 (23x34) 40x7`

Sacrifice `33-28`, prise majoritaire noire forcée (3 pions), rafle
`40×7` (cf `final_move.path = 40→29→20→9→18→7`, 5 captures incluant 34
— forme canonique du coup royal).

`published_notation` Dubois pour les variantes additionnelles :
- `BEG_CH05_004` (ch4 D2, Salomé-Nimbi 2015) : `27-21 (26x30) 35x2`
- `BEG_CH05_005` (ch4 D3, rafle longue à 6 captures) :
  `32-27 (22x44) 49x7`
- `BEG_CH05_006` (ch4 D5, coup royal variante) : `33-29 (23x32) 37x10`
- `BEG_CH05_007` (ch4 D7) : `33-29 (24x31) 37x10`

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH05_003` | `33-28` | +99.89 | 99 | — |
| `BEG_CH05_004` | `27-21` | +4.22 | 29 | — |
| `BEG_CH05_005` | `32-27` | +8.96 | 28 | — |
| `BEG_CH05_006` | `33-29` | +99.91 | 99 | — |
| `BEG_CH05_007` | `33-29` | +99.87 | 99 | — |

### 5.3. Envois à dame côté blanc (D8)

Exemple — `BEG_CH05_008` (Dubois ch4 D8) :

> `published_notation` Dubois : `37-31 (26x48) 47-42 (48x22) 28x10`

Le sacrifice `37-31` force le noir à promouvoir en 48, puis `47-42`
ramène la dame en 22 (`48x22`) où la rafle blanche `28×10` la capture
(`final_move=None` car la rafle de dame `(48x22)` n'est pas
reconstructible par le module pion-only — cf `claude_notes`, R007).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH05_008` | `37-31` | +6.44 | 29 | — |

### 5.4. Envois à dame côté noir (D9, D10 — parties historiques)

Trait aux noirs : le blanc est envoyé à dame, puis ramené, puis capturé
par une rafle noire.

Exemple — `BEG_CH05_009` (Dubois ch4 D9, Navarro-Roozenburg 1956) :

> `published_notation` Dubois : `(13-19) 24x4 (11-16) 4x27 (21x45)`

Premier sacrifice noir `(13-19)`, le blanc 24 doit prendre et promeut
en 4 (rafle `24x4`), puis `(11-16)` force la dame blanche à reprendre
en 27 (`4x27`), enfin la rafle noire `(21x45)` capture la dame (cf
`claude_notes` : `final_move=None`, rafle de dame `4x27`).

`published_notation` Dubois pour `BEG_CH05_010` (ch4 D10,
Bakker-Ivens 1976) : `(14-19) 23x5 (4-10) 5x8 (3x45)`.

🔴 **Divergences Scan flaggées (cosmétiques)** — Pour `BEG_CH05_009`
et `BEG_CH05_010`, la `published_notation` commence par un coup entre
parenthèses (`(13-19)`, `(14-19)`) alors que le PV Scan le donne en
clair (`13-19`, `14-19`). Les parenthèses signalent simplement que le
trait est aux noirs dans la convention Dubois — pas une vraie
divergence tactique.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH05_009` | `13-19` | +2.14 | 25 | 🔴 |
| `BEG_CH05_010` | `14-19` | +3.17 | 25 | 🔴 |

---

## Chapitre 6 — La méthode des points de contact
<!-- pedagogy-weaknesses: isolated, backward -->

Jusqu'à présent, nous avons cherché les combinaisons en partant de la
**rafle finale** : « où peut atterrir une rafle ? quelles cases-clés
faut-il atteindre ? ». Cette méthode est efficace mais incomplète.

Une approche complémentaire consiste à identifier les **points de
contact** entre pions blancs et noirs adverses (les cases où deux pions
se touchent en diagonale), puis à **imaginer mentalement chaque
sacrifice possible** à partir de ces points, sans chercher d'abord
l'issue. Cette méthode révèle des combinaisons que la recherche
« par la rafle » manque.

Les 11 exercices viennent du chapitre 5 de Dubois (pages 17-19), avec
trois parties historiques notables (`BEG_CH06_007`, `BEG_CH06_009`,
`BEG_CH06_010`).

### 6.1. L'exemple introductif

Exemple — `BEG_CH06_001` (Dubois ch5 intro) :

> `published_notation` Dubois : `31-27 (22x24) 34-30 (25x34) 39x6`

Le `concept` de la fixture détaille la méthode : Dubois identifie 4
points de contact (34-30, 29-23, 37-32, 31-27), et c'est l'exploration
du point inattendu `31-27` qui révèle une prise majoritaire à 4 pions
ouvrant la rafle `39×6` (cf `final_move.path = 39→30→19→8→17→6`,
5 captures dont 34). Sans l'analyse systématique, le coup ne se
trouve pas.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH06_001` | `31-27` | +2.99 | 24 | — |

### 6.2. Le coup Philippe (préview du chapitre 16)

Exemple — `BEG_CH06_002` (Dubois ch5 D1, forme la plus épurée du coup
Philippe) :

> `published_notation` Dubois : `34-30 (25x34) 40x7`

Trois pions blancs contre trois pions noirs, sacrifice central `34-30`,
rafle `40×7` (cf `final_move.path = 40→29→18→7`, captures 12, 23, 34).
Le coup Philippe sera détaillé au chapitre 16.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH06_002` | `34-30` | +99.97 | 99 | — |

### 6.3. Application aux mécanismes connus

La méthode des points de contact permet de redécouvrir les mécanismes
appris précédemment.

`published_notation` Dubois pour les fixtures de cette section :
- `BEG_CH06_003` (ch5 D2, prise majoritaire) : `27-21 (17x39) 43x3`
  (rafle 4 captures, `final_move.path = 43→34→23→14→3`)
- `BEG_CH06_004` (ch5 D3, collage) : `26-21 (25x32) 21x3`
  (rafle avec coup turc par 23, captures 9, 17, 18, 19)
- `BEG_CH06_005` (ch5 D4, gambit) : `26-21 (27x16) 38-32`
  (combinaison qui se termine par coup simple, `final_move=None`)
- `BEG_CH06_006` (ch5 D5, rafle longue) : `17-12 (7x29) 44x2`
  (rafle de 6 captures sur 7 cases, `final_move.path =
  44→33→24→15→4→13→2`)

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH06_003` | `27-21` | +87.35 | 31 | — |
| `BEG_CH06_004` | `26-21` | +6.51 | 27 | — |
| `BEG_CH06_005` | `26-21` | +3.42 | 33 | — |
| `BEG_CH06_006` | `17-12` | +99.97 | 99 | — |

### 6.4. Parties historiques et rafles « cachées »

Trois parties illustrent la méthode appliquée à des positions complexes.

Exemple — `BEG_CH06_007` (Dubois ch5 D6, Laporta-Mostovoy 1970, trait
aux noirs) :

> `published_notation` Dubois : `(17-21) 26x10 (4x35)`

Sacrifice noir `(17-21)`, le blanc 26 prend (rafle de 3 pions 21, 16, 7
selon `explanation` de la fixture), puis rafle noire finale `(4x35)`
sur la grande diagonale (`final_move.path = 4→15→24→33→44→35`,
5 captures).

`published_notation` Dubois pour les variantes additionnelles :
- `BEG_CH06_008` (ch5 D7, 4 points de contact) :
  `35-30 (24x44) 33x13 (18x9) 27x49` (combinaison à 5 demi-coups)
- `BEG_CH06_009` (ch5 D8, Bergsma-de Vries 1961) :
  `33-29 (24x22) 34-30 (25x34) 40x16`
- `BEG_CH06_011` (ch5 D10, point d'appui alternatif) :
  `23-19 (14x32) 44-40 (35x33) 29x9` (rafle 6 captures, coup turc
  par 18)

Exemple emblématique — `BEG_CH06_010` (Dubois ch5 D9, Leclercq-Weiss
1903, trait aux noirs) :

> `published_notation` Dubois : `(14-20) 23x25 (26-31) 36x7 (1x41)`

La rafle finale `(1x41)` semble bloquée par le pion blanc 36, mais le
coup intermédiaire `(26-31) 36x7` fait disparaître ce pion 36 — exemple
emblématique de rafle « cachée » révélée par les points de contact (cf
`claude_notes`, `final_move.path = 1→12→23→32→41`, captures 7, 18, 28,
37).

🔴 **Divergences Scan flaggées (cosmétiques)** — Pour `BEG_CH06_007`
et `BEG_CH06_010`, la `published_notation` commence par un coup entre
parenthèses (`(17-21)`, `(14-20)`) alors que le PV Scan le donne en
clair. Convention Dubois : parens = trait aux noirs.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH06_007` | `17-21` | +2.29 | 30 | 🔴 |
| `BEG_CH06_008` | `35-30` | +99.79 | 99 | — |
| `BEG_CH06_009` | `33-29` | +1.18 | 24 | — |
| `BEG_CH06_010` | `14-20` | +8.41 | 32 | 🔴 |
| `BEG_CH06_011` | `23-19` | +99.83 | 89 | — |

---

## Chapitre 7 — Les temps de repos créés par une attaque
<!-- pedagogy-motifs: sacrifice -->
<!-- pedagogy-weaknesses: holes -->

Un **temps de repos** est l'opportunité de jouer **un coup
supplémentaire** sans que l'adversaire puisse répliquer librement —
parce qu'il est obligé de capturer (prise obligatoire). Ces temps de
repos sont créés quand l'adversaire **attaque** un de mes pions :
je suis obligé de défendre ou de laisser prendre, mais entre temps
**j'ai un coup gratuit**.

Les 12 exercices (`BEG_CH07_001` à `BEG_CH07_012`) montrent comment
exploiter ces temps de repos. Chaque exercice ci-dessous est annoté
à partir de la **variante principale (PV) calculée par le moteur
Scan** (`scan/scan_analysis_debutant.json`) — c'est la source de
vérité tactique. Quand la `published_notation` du livre diverge du
PV Scan, c'est le PV qui fait foi, le livre est traité comme
suspect.

### 7.1. Cascade de temps de repos (`BEG_CH07_001`)

> **Position de départ** (trait aux blancs)
> Pions blancs : 27, 28, 30, 32, 35, 38, 40, 42, 43, 45.
> Pions noirs : 3, 8, 13, 15, 16, 17, 18, 19, 24, 25.
> Menace immédiate : le pion noir 25 attaque le pion blanc 30
> (atterrissage en 34).

L'attaque noire `(25×34)` est inévitable. Plutôt que défendre, les
blancs encaissent la prise — chaque demi-coup adverse devient une
prise forcée qui leur offre un coup libre.

**PV Scan** (profondeur 30, éval +6.34, blancs gagnants) :

> `42-37 (25×34×30) 40×20 (15×24) 28-22 (17×28) 32×14 …`

Lecture : `42-37` lance le mécanisme. Les noirs *doivent* capturer
(25×34×30 — rafle qui prend les pions 30 puis 34). Les blancs
reprennent en rafle (40×20×24×34), puis enchaînent jusqu'à `32×14`.
La position résultante est nettement gagnante pour les blancs.

🔴 **À vérifier (rédacteur humain)** — l'ancienne formulation
disait que la chaîne contenait **« trois temps de repos
consécutifs »**. Le PV Scan en montre effectivement plusieurs ;
compter rigoureusement ces temps de repos à la main pour valider le
nombre cité.

### 7.2. Combinaison forcée (`BEG_CH07_002`)

> **Position de départ** (trait aux blancs)
> Pions blancs : 23, 27, 29, 35, 39, 42, 48.
> Pions noirs : 6, 8, 12, 14, 19, 25, 26.
> Menace immédiate : le pion noir 19 attaque le pion blanc 23
> (atterrissage en 28).

**PV Scan** (profondeur 37, éval +89.65 → gain quasi-forcé pour les
blancs) :

> `42-37 (19×28×23) 29-23 (28×19×23) 37-31 …`

Lecture : `42-37` provoque la rafle obligatoire `19×28×23` (les
noirs prennent simultanément 28 et 23). Les blancs réinjectent
immédiatement `29-23`, ce qui force la deuxième rafle obligatoire
`28×19×23`. Le coup `37-31` qui suit verrouille un avantage
matériel décisif.

> 🔴 **À VÉRIFIER (cadrage §zéro-invention)** — La
> `published_notation` historique de cette fixture
> (`42-37 (19x28) 29-23 (28x19) 37-31 (26x37) 48-42 (37x48) 39-34
> (48x30) 35x2`) est **incohérente** : elle prétend qu'un envoi à
> dame `39-34` puis `(48x30)` puis `35x2` est jouable, mais le
> pion blanc 35 a déjà quitté le plateau à ce moment. Le PV Scan
> ci-dessus est plus court (5 plies) et solide ; il **remplace**
> la solution publiée. Cette entrée peut sortir de
> `A_VERIFIER_MOTEUR.md §1` une fois validée par relecture
> humaine.

### 7.3. Catalogue Dubois ch. 8 (`BEG_CH07_003` à `BEG_CH07_012`)

Dix combinaisons illustrant la création et l'exploitation de temps
de repos par une attaque. Le tableau ci-dessous donne l'éval Scan
finale (positive = avantage blanc), la profondeur d'analyse atteinte,
et le premier coup du PV. La **variante principale complète** est
disponible dans `scan/scan_analysis_debutant.json`.

| Fixture | Titre Dubois | Premier coup PV | Éval | Profondeur |
|---------|--------------|-----------------|------|-----------|
| `BEG_CH07_003` | D1 | `14-20` | +8.56 | 30 |
| `BEG_CH07_004` | D2 | `27-21` | +1.73 | 27 |
| `BEG_CH07_005` | D3 | `27-22` | +90.67 | 28 |
| `BEG_CH07_006` | D4 | `28-22` | +7.63 | 26 |
| `BEG_CH07_007` | D5 — Attaque et point d'appui mobile | `26-21` | +99.73 | 34 |
| `BEG_CH07_008` | D6 | `17-22` | +2.05 | 22 |
| `BEG_CH07_009` | D7 (envoi à dame) | `28-23` | +1.10 | 27 |
| `BEG_CH07_010` | D8 | `39-34` | +1.52 | 25 |
| `BEG_CH07_011` | D9 | `13-18` | +3.74 | 23 |
| `BEG_CH07_012` | D10 (`ad lib`) | `32-27` | +99.73 | 28 |

🔴 **À vérifier (rédacteur humain)** — la colonne « Titre Dubois »
ci-dessus est reprise du champ `title` des fixtures (saisie pré-cadrage
zéro-invention). Vérifier la correspondance avec l'édition Dubois
papier ; corriger les titres si nécessaire.

🔴 **Divergences flaggées par Scan (cf `notes` du JSON)** —
`BEG_CH07_003`, `BEG_CH07_008`, `BEG_CH07_011` : la
`published_notation` commence par un coup entre parenthèses
(`(14-20)`, `(17-22)`, `(13-18)`) alors que le PV Scan le donne en
clair. C'est probablement un artefact de transcription (parens =
coup adverse dans la convention Dubois) — pas une vraie divergence
tactique, mais à confirmer.

### 7.4. Particularités

- `BEG_CH07_002` et `BEG_CH07_009` contiennent un **envoi à dame** —
  `final_move=None`.
- `BEG_CH07_012` (Dubois ch. 8 D10) introduit la notation `(ad lib)` :
  l'adversaire a plusieurs captures forcées équivalentes. Voir
  résolution R008 dans `RESOLUTIONS_debutant.md`.

---

## Chapitre 8 — La création des temps de repos
<!-- pedagogy-motifs: sacrifice -->
<!-- pedagogy-weaknesses: holes, outposts -->

Quand l'adversaire n'attaque rien, on peut **créer artificiellement**
un temps de repos en **sacrifiant un pion** qui force une prise. Cette
technique étend le champ des combinaisons à des positions « silencieuses »
où aucune menace n'est apparente.

Les 12 exercices (2 narratifs + 10 du chapitre 9 Dubois, pages 29-31)
illustrent la méthode systématique en 3 phases :

> **Phase 1** : créer un temps de repos par un sacrifice qui force une
> prise.
> **Phase 2** : profiter du temps de repos pour un coup préparatoire.
> **Phase 3** : dérouler les prises et la rafle finale.

### 8.1. Exemples narratifs (création en 2 sacrifices, puis méthode en 3 phases)

Exemple — `BEG_CH08_001` (Dubois ch9 intro 1) :

> `published_notation` Dubois : `37-31 (26x28) 38-33 (21x32) 33x4`

Deux sacrifices successifs (`37-31` puis `38-33`) créent les temps de
repos. Rafle finale `33×4` (`final_move.path = 33→22→13→4`, 3 captures
9, 18, 28).

Exemple — `BEG_CH08_002` (Dubois ch9 intro 2, méthode en 3 phases) :

> `published_notation` Dubois : `32-28 (23x21) 34-29 (18x27) 29x7`

Phase 1 : `32-28` crée le temps de repos. Phase 2 : `34-29` exploite la
prise forcée. Phase 3 : rafle finale `29×7` (cf `final_move.path =
29→20→9→18→7`, 4 captures 12, 13, 14, 24).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH08_001` | `37-31` | +5.94 | 31 | — |
| `BEG_CH08_002` | `32-28` | +6.80 | 29 | — |

### 8.2. Parties historiques

Plusieurs parties illustrent la création artificielle de temps de repos.

Exemple — `BEG_CH08_003` (Dubois ch9 D1, Linssen-Bandstra 1982) :

> `published_notation` Dubois : `28-23 (19x28) 30x6`

Une seule rafle (`30×6`) fonctionne ; le sacrifice `28-23` fait sauter
le pion 19 (cf `concept` de la fixture). `final_move.path =
30→19→8→17→6`, 4 captures (11, 12, 13, 24).

`published_notation` Dubois pour les variantes additionnelles :
- `BEG_CH08_004` (ch9 D2, prise majoritaire) : `33-29 (35x22) 29x29`
  (rafle qui revient sur sa case de départ — coup turc, cf
  `claude_notes`)
- `BEG_CH08_005` (ch9 D3, Loenen-Hengefeld 1990) :
  `33-29 (24x22) 32-27 (35x24) 27x9`
- `BEG_CH08_007` (ch9 D5, Schippers-Barten 2012) :
  `34-30 (23x25) 27-21 (17x37) 41x5`
- `BEG_CH08_009` (ch9 D7) : `22-17 (11x31) 34-29 (16x27) 29x7`
- `BEG_CH08_010` (ch9 D8) : `26-21 (17x28) 38-33 (22x31) 33x15`
- `BEG_CH08_012` (ch9 D10) : `28-23 (19x17) 27-22 (17x28) 32x3`

Exemple notable — `BEG_CH08_006` (Dubois ch9 D4, Badal-Kemperman 1994,
trait aux noirs, rafle rare `24x11`) :

> `published_notation` Dubois : `(15-20) 28x17 (29-34) 40x29 (24x11)`

La rafle noire finale `(24×11)` est très rare (cf `concept` de la
fixture : « démontre la valeur de la recherche systématique »).
`final_move.path = 24→33→42→31→22→11`, 5 captures.

Exemple — `BEG_CH08_008` (Dubois ch9 D6, van Leeuwen-de Jong 1968,
trait aux noirs) :

> `published_notation` Dubois : `(3-9) 26x17 (23-29) 34x12 (7x47)`

Le point d'appui de la rafle est en 7 (cf `concept`). Rafle finale noire
`(7×47)` (`final_move.path = 7→18→27→38→47`, 4 captures 12, 22, 32, 42).

🔴 **Divergences Scan flaggées (cosmétiques)** — Pour `BEG_CH08_006` et
`BEG_CH08_008`, la `published_notation` commence par un coup entre
parenthèses (`(15-20)`, `(3-9)`) alors que le PV Scan le donne en clair
— convention Dubois pour trait aux noirs.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH08_003` | `28-23` | +5.11 | 31 | — |
| `BEG_CH08_004` | `33-29` | +6.99 | 29 | — |
| `BEG_CH08_005` | `33-29` | +88.58 | 30 | — |
| `BEG_CH08_006` | `15-20` | +1.85 | 34 | 🔴 |
| `BEG_CH08_007` | `34-30` | +3.82 | 22 | — |
| `BEG_CH08_008` | `3-9` | +5.42 | 24 | 🔴 |
| `BEG_CH08_009` | `22-17` | +91.67 | 33 | — |
| `BEG_CH08_010` | `26-21` | +2.77 | 27 | — |
| `BEG_CH08_012` | `28-23` | +99.79 | 28 | — |

### 8.3. Préview : le coup de Talon

`BEG_CH08_011` (Dubois ch9 D9, Toet-Luteijn 1977) est un **coup de
Talon** — coup nommé qui sera détaillé au chapitre 15.

> `published_notation` Dubois : `24-20 (15x42) 37x48 (26x37) 41x3`

La formation blanche 31-36-37-41-46 est caractéristique du coup de
Talon (cf `claude_notes`). Rafle finale `41×3` (`final_move.path =
41→32→23→14→3`, 4 captures 9, 19, 28, 37).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH08_011` | `24-20` | +10.26 | 30 | — |

---


## Chapitre 9 — Le coup de l'Express
<!-- pedagogy-motifs: coup_express -->

Le **coup de l'Express** est le premier des **coups nommés** — des
mécanismes combinatoires fréquents auxquels la tradition damiste a
donné un nom propre. Il se reconnaît à un schéma très caractéristique :
**quatre sacrifices consécutifs** qui acheminent les pions adverses
par paires successives, suivis d'une rafle finale typique `33×2` ou
`33×4`.

Les 12 exercices viennent du chapitre 13 de Dubois (pages 42-44).

### 9.1. La forme canonique

Exemple — `BEG_CH09_001` (Dubois ch13 narratif) :

> `published_notation` Dubois : `37-31 (26x37) 27-21 (16x27) 28-22 (27x18) 38-32 (37x28) 33x2`

Quatre sacrifices consécutifs, puis le pion blanc 33 parcourt la grande
diagonale jusqu'à 2 (cf `final_move.path = 33→22→13→2`, captures 8, 18,
28 — promotion en dame). La signature visuelle est reconnaissable.

`BEG_CH09_002` (`published_notation` : `33x2`) est la position finale
illustrative qui montre l'aboutissement de la rafle (cf `claude_notes` :
« pas de combinaison à jouer »). 🔴 Le PV Scan note la rafle en forme
détaillée `33×2×8×18×28` — c'est la même rafle annotée plus en détail,
pas une divergence tactique.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH09_001` | `37-31` | +99.87 | 99 | — |
| `BEG_CH09_002` | `33×2×8×18×28` | +99.95 | 99 | 🔴 |

### 9.2. Variantes du coup de l'Express côté blanc

`published_notation` Dubois pour les fixtures côté blanc :
- `BEG_CH09_003` (ch13 D1) : `34-29 (23x32) 31-27 (32x21) 26x10`
- `BEG_CH09_007` (ch13 D5, coquille PDF corrigée — cf R009 et
  `claude_notes`) : `32-27 (23x21) 38-32 (29x40) 45x3`
- `BEG_CH09_008` (ch13 D6) : `32-27 (31x22) 24-20 (15x33) 39x10`
- `BEG_CH09_009` (ch13 D7) : `29-23 (18x29) 33x24 (22x31) 36x9`
- `BEG_CH09_010` (ch13 D8) : `34-29 (23x34) 39x30 (28x37) 41x3`
- `BEG_CH09_011` (ch13 D9, schéma canonique) :
  `24-19 (13x24) 29x20 (15x24) 37-31 (26x28) 33x2`
- `BEG_CH09_012` (ch13 D10, rafle `33×4`) :
  `29-24 (20x18) 37-31 (26x37) 38-32 (37x28) 33x4`

`BEG_CH09_007` mérite une note pédagogique : la coquille PDF d'origine
(`43-38` au lieu de `38-32`) faisait jouer un pion blanc 43 sur la case
38 déjà occupée par un autre blanc. La résolution R009 retient qu'un
même chiffre (ici `38`) peut être ambigu entre case de départ et case
d'arrivée — la validation par recherche exhaustive est indispensable.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH09_003` | `34-29` | +99.77 | 35 | — |
| `BEG_CH09_007` | `32-27` | +3.94 | 28 | — |
| `BEG_CH09_008` | `32-27` | +99.79 | 26 | — |
| `BEG_CH09_009` | `29-23` | +5.61 | 32 | — |
| `BEG_CH09_010` | `34-29` | +8.63 | 27 | — |
| `BEG_CH09_011` | `24-19` | +11.05 | 33 | — |
| `BEG_CH09_012` | `29-24` | +4.08 | 27 | — |

### 9.3. Coup de l'Express côté noir (parties historiques)

Trois parties historiques où c'est le noir qui exécute l'express.

`published_notation` Dubois :
- `BEG_CH09_004` (ch13 D2, Grotenhuis ten Harkel-Stokkel 1977, trait
  aux noirs) : `(17-22) 28x17 (19x28) 33x13 (24x11)`
- `BEG_CH09_005` (ch13 D3, Perot-Mostovoy 1968, trait aux noirs) :
  `(23-29) 33x15 (17-21) 16x27 (22x44)`
- `BEG_CH09_006` (ch13 D4, Ketelaars-Kalsbeek 1997, trait aux noirs) :
  `(27-31) 36x29 (19-24) 30x10 (4x35)`

🔴 **Divergences Scan flaggées** — Pour ces trois fixtures, le PV Scan
ne commence **pas** par le coup noir publié, mais par un coup blanc
préliminaire :
- `BEG_CH09_004` : `published_notation` commence par `(17-22)`, Scan PV
  par `27-21` (éval −4.30, profondeur 31 — Scan évalue la position
  côté blanc avant le sacrifice noir).
- `BEG_CH09_005` : `published_notation` commence par `(23-29)`, Scan PV
  par `39-34` (éval −6.71, profondeur 28).
- `BEG_CH09_006` : `published_notation` commence par `(27-31)`, Scan PV
  par `41-37` (éval −3.24, profondeur 26).

Dans ces trois cas, l'évaluation Scan **négative** indique que les noirs
sont gagnants (le moteur regarde la position du point de vue du joueur
au trait, et c'est aux noirs de jouer). Le PV complet est disponible
dans `scan_analysis_debutant.json` — le coup noir publié reste correct,
Scan en propose un précédent que les blancs joueraient pour minimiser
les dégâts.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH09_004` | `27-21` | -4.30 | 31 | 🔴 |
| `BEG_CH09_005` | `39-34` | -6.71 | 28 | 🔴 |
| `BEG_CH09_006` | `41-37` | -3.24 | 26 | 🔴 |

### 9.4. Coquille PDF identifiée et résolue (rappel)

Voir §9.2 et `BEG_CH09_007` : coquille PDF (`43-38` → `38-32`)
corrigée par recherche exhaustive (R009). La résolution est documentée
dans `RESOLUTIONS_debutant.md`.

---

## Chapitre 10 — Le coup de Ricochet

Le **coup de Ricochet** est caractérisé par une rafle qui **revient sur
sa case de départ** (ou très proche) après avoir traversé une zone clé.
C'est une variante du coup de l'Express qui exploite mieux l'**aile
gauche encombrée**.

Les 12 exercices viennent du chapitre 14 de Dubois (pages 45-47).

### 10.1. Schéma de base

Exemple — `BEG_CH10_001` (Dubois ch14 narratif) :

> `published_notation` Dubois : `34-30 (25x34) 40x18 (13x22) 28x26`

Sacrifices `34-30` puis `40×18`, puis le pion blanc 28 ricoche sur la
case 26 où le pion noir était initialement (cf `final_move.path =
28→17→26`, captures 21 et 22). Schéma canonique.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH10_001` | `34-30` | +99.81 | 99 | — |

### 10.2. Application en partie (combinaison longue)

Exemple — `BEG_CH10_002` (Dubois ch14 narratif appliqué) :

> `published_notation` Dubois : `27-22 (18x27) 31x22 12-18 46-41 (18x27) 34-30 (25x34) 40x18 (13x22) 28x26`

Combinaison à 6 demi-coups (cf `explanation` de la fixture) : sacrifice
préliminaire `27-22 (18x27) 31x22`, réponse noire forcée `12-18`, coup
silencieux blanc `46-41`, puis schéma standard du ricochet
(`final_move=None` à cause de la notation à plusieurs phases —
`claude_notes`).

🔴 **Divergence Scan flaggée** — Pour `BEG_CH10_002`, Scan recommande
`31-26` comme premier coup (éval +0.56, profondeur 25), là où la
`published_notation` Dubois commence par `27-22`. Le manuel s'appuie
sur la combinaison Dubois pour l'enseignement du ricochet ; le PV Scan
court (avec `31-26`) est dans `scan_analysis_debutant.json` et peut
être étudié séparément.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH10_002` | `31-26` | +0.56 | 25 | 🔴 |

### 10.3. Coups de dame et combinaisons classiques (D1 à D6, D9)

`published_notation` Dubois pour les fixtures de cette section :
- `BEG_CH10_003` (ch14 D1, coup de dame en 5) :
  `28-22 (17x30) 40-34 (24x42) 34x5`
- `BEG_CH10_004` (ch14 D2, coup de dame en 4) :
  `29-24 (20x27) 49-44 (22x33) 31x4`
- `BEG_CH10_005` (ch14 D3, combinaison ultra classique) :
  `28-22 (17x28) 27-21 (16x38) 42x24`
- `BEG_CH10_006` (ch14 D4, Kloot-Kuipers 1939) :
  `37-31 (26x39) 40-34 (39x30) 35x4`
- `BEG_CH10_007` (ch14 D5, coup de dame en 1) :
  `37-31 (36x27) 29-23 (18x38) 43x1`
- `BEG_CH10_008` (ch14 D6, coquille PDF corrigée — R010, cf
  `claude_notes`) : `27-21 (17x28) 40-34 (30x39) 44x2`
- `BEG_CH10_011` (ch14 D9, coup de dame à 4 via ricochet) :
  `35-30 (24x35) 26-21 (17x37) 41x23 (18x29) 33x4`

`BEG_CH10_008` mérite une note pédagogique : la coquille d'origine
(`37-31 (26x28)`) cumulait une triple inversion typographique (37↔27,
31↔21, 26↔17), corrigée par recherche exhaustive (R010).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH10_003` | `28-22` | +2.12 | 24 | — |
| `BEG_CH10_004` | `29-24` | +1.17 | 26 | — |
| `BEG_CH10_005` | `28-22` | +1.35 | 25 | — |
| `BEG_CH10_006` | `37-31` | +1.30 | 25 | — |
| `BEG_CH10_007` | `37-31` | +7.13 | 25 | — |
| `BEG_CH10_008` | `27-21` | +99.79 | 42 | — |
| `BEG_CH10_011` | `35-30` | +0.81 | 25 | — |

### 10.4. Préview : le coup Napoléon

`BEG_CH10_009` (Dubois ch14 D7) introduit le **coup Napoléon** —
détaillé au chapitre 13.

> `published_notation` Dubois : `28-22 (17x28) 27-21 (16x27) 31x24`

`final_move.path = 31→22→33→24` avec 3 captures (27, 28, 29 — cf
`claude_notes`).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH10_009` | `28-22` | +1.88 | 27 | — |

### 10.5. Ricochets dissimulés (parties historiques noires)

Deux parties historiques où c'est le noir qui exécute le ricochet — les
combinaisons sont très longues (7 demi-coups).

`published_notation` Dubois :
- `BEG_CH10_010` (ch14 D8, Coenen-van Ingen 1990, trait aux noirs) :
  `(23-28) 22x11 (28x39) 34x43 (25x34) 40x29 (24x22)` (cf
  `final_move.path = 24→33→42→31→22`, 4 captures)
- `BEG_CH10_012` (ch14 D10, Le Goff-Molimard 1909, trait aux noirs) :
  `(15-20) 29x27 (20x29) 34x23 (19x28) 32x23 (21x45)` (rafle cachée
  dont `final_move.path = 21→32→43→34→45`)

🔴 **Divergences Scan flaggées (cosmétiques)** — Pour `BEG_CH10_010` et
`BEG_CH10_012`, la `published_notation` commence par un coup entre
parenthèses (`(23-28)`, `(15-20)`) alors que le PV Scan le donne en
clair — convention Dubois trait aux noirs.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH10_010` | `23-28` | +5.11 | 27 | 🔴 |
| `BEG_CH10_012` | `15-20` | +7.17 | 23 | 🔴 |

### 10.6. Coquille PDF identifiée et résolue (rappel)

Voir §10.3 et `BEG_CH10_008` : triple inversion typographique
(37↔27, 31↔21, 26↔17) corrigée par recherche exhaustive (R010).

---

## Chapitre 11 — Le coup de Rappel

Le **coup de Rappel** exploite une rafle adverse qui **descend trop
bas** (souvent jusqu'en case 39 pour les noirs). Un nouveau sacrifice
**force le pion à remonter** (« rappel ») où il est capturé
définitivement par la rafle finale.

Les 12 exercices viennent du chapitre 15 de Dubois (pages 48-50).

### 11.1. Les trois schémas narratifs

Exemple — `BEG_CH11_001` (Dubois ch15 schéma 1) :

> `published_notation` Dubois : `28-23 (19x39) 38-33 (39x28) 32x3`

Le sacrifice `28-23` est pris par `(19×39)` — le pion noir descend trop
bas. Le rappel `38-33` force le pion 39 à remonter (`39×28`), puis la
rafle `32×3` conclut (cf `final_move.path = 32→23→12→3`, captures 8,
18, 28).

`published_notation` Dubois pour les autres schémas narratifs :
- `BEG_CH11_002` (schéma 2, rafle finale en 4) :
  `30-24 (19x39) 40-34 (39x30) 35x4`
- `BEG_CH11_003` (schéma 3, rappel via case 32) :
  `28-22 (17x37) 38-32 (37x28) 33x4`

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH11_001` | `28-23` | +99.95 | 99 | — |
| `BEG_CH11_002` | `30-24` | +99.95 | 99 | — |
| `BEG_CH11_003` | `28-22` | +99.95 | 99 | — |

### 11.2. Rappels côté blanc (D1 à D4, D7)

`published_notation` Dubois pour les fixtures de cette section :
- `BEG_CH11_004` (ch15 D1, rafle finissant en 7 via pion de base 49) :
  `32-28 (23x34) 44-40 (35x44) 49x7`
- `BEG_CH11_005` (ch15 D2, acheminer un pion noir en 22) :
  `22-17 (11x31) 32-27 (31x22) 28x10`
- `BEG_CH11_006` (ch15 D3) : `34-30 (35x42) 43-38 (42x33) 39x6`
- `BEG_CH11_007` (ch15 D4, combinaison + fin de partie) :
  `24-20 (14x23) 32-28 (23x32) 37x19`
- `BEG_CH11_010` (ch15 D7, Rapopport-Gertsenzon 1963, 4 demi-coups) :
  `38-32 (28x37) 25-20 (15x33) 34-29 (33x24) 30x6`

🔴 **Divergence Scan flaggée** — Pour `BEG_CH11_005`, la
`published_notation` Dubois commence par `22-17` (sacrifice immédiat
sur la trajectoire de rappel), tandis que Scan préfère `37-31` (éval
+10.58, profondeur 29) comme premier coup. Le PV complet est dans
`scan_analysis_debutant.json` ; la solution Dubois reste enseignable
en tant que mécanisme de rappel, mais Scan trouve une voie plus
efficace.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH11_004` | `32-28` | +99.79 | 27 | — |
| `BEG_CH11_005` | `37-31` | +10.58 | 29 | 🔴 |
| `BEG_CH11_006` | `34-30` | +99.75 | 30 | — |
| `BEG_CH11_007` | `24-20` | +99.67 | 28 | — |
| `BEG_CH11_010` | `38-32` | +8.67 | 27 | — |

### 11.3. Préview : le coup de la Trappe

`BEG_CH11_008` (Dubois ch15 D5, Michiels-Marini 1986) et `BEG_CH11_009`
(Dubois ch15 D6) sont des **coups de la Trappe** — détaillés au
chapitre 14.

`published_notation` Dubois :
- `BEG_CH11_008` : `44-39 (35x44) 32-28 (23x34) 50x10`
- `BEG_CH11_009` : `38-32 (30x39) 27-22 (18x29) 44x2`

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH11_008` | `44-39` | +4.87 | 26 | — |
| `BEG_CH11_009` | `38-32` | +99.81 | 32 | — |

### 11.4. Rappels côté noir (parties historiques, 7 demi-coups)

Deux parties historiques où c'est le noir qui exécute le rappel sur 7
demi-coups.

`published_notation` Dubois :
- `BEG_CH11_011` (ch15 D8, van Aalten-Clerc 1976, coup de dame à 50,
  trait aux noirs) :
  `(23-28) 32x23 (22-28) 23x32 (13-19) 24x22 (17x50)` (cf
  `final_move.path = 17→28→39→50`, captures 22, 33, 44)
- `BEG_CH11_012` (ch15 D9, rafle en 44, trait aux noirs) :
  `(22-27) 21x32 (18-22) 29x27 (7-11) 16x18 (13x44)` (cf
  `final_move.path = 13→22→31→42→33→44`, 5 captures)

🔴 **Divergences Scan flaggées (cosmétiques)** — Pour `BEG_CH11_011` et
`BEG_CH11_012`, la `published_notation` commence par un coup entre
parenthèses (`(23-28)`, `(22-27)`) alors que le PV Scan le donne en
clair — convention Dubois trait aux noirs.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH11_011` | `23-28` | +1.47 | 25 | 🔴 |
| `BEG_CH11_012` | `22-27` | +7.02 | 27 | 🔴 |

---

## Chapitre 12 — Le coup Renversé

Le **coup Renversé** est un mécanisme moins courant mais utile car il
**se marie facilement avec d'autres coups nommés** : coups de mazette,
coups Philippe, coups de Ricochet. Il inclut une variante notable, le
**coup de chevron**.

Les 10 exercices viennent du chapitre 16 de Dubois (pages 51-53).

### 12.1. Coup renversé pur (D6 — forme canonique)

Exemple — `BEG_CH12_006` (Dubois ch16 D6) :

> `published_notation` Dubois : `33-29 (23x34) 39x30 (25x34) 27-21 (26x28) 32x25`

Quatre demi-coups préparatoires, puis rafle finale `32×25` qui arrive
en case de bord proche du départ — c'est la signature du coup renversé
(cf `final_move.path = 32→23→14→25`, 3 captures 19, 20, 28).

`published_notation` Dubois pour les variantes côté blanc :
- `BEG_CH12_001` (ch16 D1, rafle en 4) :
  `35-30 (24x35) 26-21 (17x28) 33x4`
- `BEG_CH12_003` (ch16 D3, coup de dame à 2) :
  `25-20 (24x15) 37-31 (26x30) 35x2`
- `BEG_CH12_007` (ch16 D7, avec temps de repos) :
  `28-22 (19x30) 29-24 (30x19) 27-21 (26x28) 32x3`
- `BEG_CH12_010` (ch16 D10, combinaison fulgurante en 5 demi-coups) :
  `28-22 (17x37) 47-41 (21x43) 39x48 (19x28) 41x5`

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH12_001` | `35-30` | +6.09 | 26 | — |
| `BEG_CH12_003` | `25-20` | +7.12 | 29 | — |
| `BEG_CH12_006` | `33-29` | +2.36 | 30 | — |
| `BEG_CH12_007` | `28-22` | +6.89 | 27 | — |
| `BEG_CH12_010` | `28-22` | +99.81 | 41 | — |

### 12.2. Le coup de chevron (D2 — Datel-Schwarzman 1977)

Exemple — `BEG_CH12_002` (Dubois ch16 D2, trait aux noirs) :

> `published_notation` Dubois : `(19-23) 28x19 (17x28) 32x12 (21x25)`

Variante du renversé connue sous le nom de **coup de chevron** à cause
de la forme de la rafle finale `(21×25)` (cf `claude_notes` et
`final_move.path = 21→32→43→34→25`, 4 captures 27, 30, 38, 39).

🔴 **Divergence Scan flaggée (cosmétique)** — Pour `BEG_CH12_002`, la
`published_notation` commence par `(19-23)` entre parenthèses (trait
aux noirs) alors que le PV Scan le donne en clair (`19-23`, éval +2.61,
profondeur 24).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH12_002` | `19-23` | +2.61 | 24 | 🔴 |

### 12.3. Combinaisons avec parties historiques (D4, D5)

`published_notation` Dubois :
- `BEG_CH12_004` (ch16 D4, Gordijn-den Hartogh 1952, exploitation pion
  de bande 35) : `34-30 (35x24) 33-28 (22x33) 38x18`
- `BEG_CH12_005` (ch16 D5, Clasquin-van Es 1981, préview coup de la
  Trappe) : `28-22 (18x38) 24-20 (15x24) 29x27`

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH12_004` | `34-30` | +1.94 | 26 | — |
| `BEG_CH12_005` | `28-22` | +6.14 | 26 | — |

### 12.4. Coup parallèle et coup renversé + envoi à dame (D8, D9)

Exemple — `BEG_CH12_008` (Dubois ch16 D8, Bergsma-Spoelstra 1952) :

> `published_notation` Dubois : `26-21 (17x28) 29-23 (18x29) 39-33 43x5`

Mécanisme connu sous le nom de **coup parallèle**. Contient la
notation `(ad lib)` au niveau des captures forcées — `final_move=None`
à cause des branches multiples (cf `claude_notes` et R008).

🔴 **Divergence Scan flaggée** — Pour `BEG_CH12_008`, Scan recommande
`39-33` comme premier coup (éval +0.25, profondeur 21), là où la
`published_notation` Dubois commence par `26-21`. Cette substitution
de premier coup change l'ordre des sacrifices ; le PV complet est
dans `scan_analysis_debutant.json`. La forme Dubois reste enseignable
mais Scan trouve une voie alternative.

Exemple — `BEG_CH12_009` (Dubois ch16 D9, Spoelstra-Bergsma 1972,
trait aux noirs, coup renversé + envoi à dame) :

> `published_notation` Dubois : `(15-20) 24x15 (4-10) 15x4 (18-22) 4x27 (21x45)`

Le blanc 24 est envoyé à dame en 4 (`24x15` puis `15x4`), ramené par
`(18-22)` en 27 (`4x27`), et capturé par la rafle noire `(21×45)`
(`final_move=None`, R007).

🔴 **Divergence Scan flaggée (cosmétique)** — Pour `BEG_CH12_009`, la
`published_notation` commence par `(15-20)` (trait aux noirs).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH12_008` | `39-33` | +0.25 | 21 | 🔴 |
| `BEG_CH12_009` | `15-20` | +0.97 | 23 | 🔴 |

---

## Chapitre 13 — Le coup Napoléon
<!-- pedagogy-motifs: coup_napoleon -->

Le **coup Napoléon** est un coup en **4 sacrifices** débouchant sur une
rafle longue typique `31×4`, `39×8`, `40×16` (selon la diagonale
utilisée). Sa forme la plus pure est montrée dans le D9 Dubois.

Les 10 exercices viennent du chapitre 17 de Dubois (pages 54-56).

### 13.1. Le coup Napoléon pur (D9)

Exemple — `BEG_CH13_009` (Dubois ch17 D9) :

> `published_notation` Dubois : `27-22 (18x29) 28-22 (17x28) 26-21 (16x27) 31x4`

« Un pur coup Napoléon » selon Dubois (cf `claude_notes`). Quatre
sacrifices consécutifs ouvrent la trajectoire de la rafle finale
`31×4` (cf `final_move.path = 31→22→33→24→15→4`, 5 captures : 10, 20,
27, 28, 29 — promotion en dame).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH13_009` | `27-22` | +6.61 | 27 | — |

### 13.2. Variantes côté blanc (D5, D6, D7, D8, D10)

`published_notation` Dubois :
- `BEG_CH13_005` (ch17 D5, Haijtink-Scholte Lubberink 1994) :
  `38-32 (27x38) 23-18 (13x22) 24-19 (14x23) 29x7`
- `BEG_CH13_006` (ch17 D6, van Leijen-Schunselaar 1971, combine rappel
  et Napoléon) : `23-19 (14x34) 33-29 (34x23) 25-20 (15x24) 30x19`
- `BEG_CH13_007` (ch17 D7, rafle `39×8`) :
  `22-18 (13x31) 32-28 (23x32) 34-29 (24x33) 39x8`
- `BEG_CH13_008` (ch17 D8, Kolodiev-Weytsman 1973, rafle `40×16`) :
  `32-28 (23x32) 24-19 (13x33) 34-30 (25x34) 40x16`
- `BEG_CH13_010` (ch17 D10, Papinski-Lewandowski 1979, rafle `48×6`) :
  `34-30 (25x34) 28-22 (17x28) 32x23 (21x43) 48x6`

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH13_005` | `38-32` | +6.43 | 26 | — |
| `BEG_CH13_006` | `23-19` | +1.29 | 25 | — |
| `BEG_CH13_007` | `22-18` | +99.77 | 29 | — |
| `BEG_CH13_008` | `32-28` | +87.72 | 32 | — |
| `BEG_CH13_010` | `34-30` | +9.56 | 25 | — |

### 13.3. Envoi à dame surprenant (D1) et coup de l'Express embarqué (D4)

Exemple — `BEG_CH13_001` (Dubois ch17 D1) :

> `published_notation` Dubois : `38-33 (29x49) 31-27 (49x24) 27x18`

Envoi à dame du noir suivi du rappel `31-27` (`final_move=None`,
R007 — rafle de dame `49x24`, cf `claude_notes`).

Exemple — `BEG_CH13_004` (Dubois ch17 D4, coquille PDF corrigée — R011) :

> `published_notation` Dubois : `28-22 (27x18) 37-31 (26x28) 33x4`

Coup de l'Express embarqué dans le chapitre Napoléon (cf `concept`).
La coquille d'origine inversait les opérandes (`(18x27)` au lieu de
`(27x18)`) — la résolution R011 retient un nouveau type de coquille
(inversion départ↔arrivée).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH13_001` | `38-33` | +6.06 | 28 | — |
| `BEG_CH13_004` | `28-22` | +5.62 | 32 | — |

### 13.4. Coups Napoléon côté noir (parties historiques, D2, D3)

Deux parties où c'est le noir qui exécute le Napoléon.

Exemple — `BEG_CH13_002` (Dubois ch17 D2, Bom-van Dijk 1963, trait aux
noirs) :

> `published_notation` Dubois : `(23-28) 16x27 (17-22) 34x32 (22x44)`

Combinaison finissant en 44 (`final_move.path = 22→31→42→33→44`,
captures 27, 37, 38, 39).

🔴 **Divergence Scan flaggée** — Pour `BEG_CH13_002`, le PV Scan
commence par `13-18` (éval +0.41, profondeur 28) là où la
`published_notation` Dubois commence par `(23-28)`. Cette substitution
de premier coup change le sacrifice initial ; le PV complet est dans
`scan_analysis_debutant.json`. La forme Dubois reste enseignable pour
le mécanisme Napoléon côté noir, mais Scan trouve une voie où les
blancs anticipent.

Exemple — `BEG_CH13_003` (Dubois ch17 D3, Baerends-Stoop 1984, coup de
dame en 46, trait aux noirs) :

> `published_notation` Dubois : `(24-30) 34x23 (22-27) 31x13 (8x46)`

`final_move.path = 8→19→28→37→46`, 4 captures (13, 23, 32, 41).

🔴 **Divergence Scan flaggée (cosmétique)** — Pour `BEG_CH13_003`, la
`published_notation` commence par `(24-30)` entre parenthèses (trait
aux noirs).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH13_002` | `13-18` | +0.41 | 28 | 🔴 |
| `BEG_CH13_003` | `24-30` | -0.26 | 23 | 🔴 |

### 13.5. Coquille PDF identifiée et résolue (rappel)

Voir §13.3 et `BEG_CH13_004` : coquille par inversion départ↔arrivée
(`(18x27)` → `(27x18)`) corrigée par recherche exhaustive (R011).

---

## Chapitre 14 — Le coup de la Trappe

Le **coup de la Trappe** est un mécanisme sophistiqué : un sacrifice
préliminaire **piège** un pion adverse dans une position où sa capture
forcée par un sacrifice subséquent **ouvre** la rafle finale. La trappe
est souvent **invisible** pour les joueurs peu entraînés — d'où son nom.

Les 10 exercices viennent du chapitre 18 de Dubois (pages 57-59).

### 14.1. Pur coup de la Trappe (D6)

Exemple — `BEG_CH14_006` (Dubois ch18 D6, forme canonique) :

> `published_notation` Dubois : `31-27 (22x31) 26-21 (16x27) 37x26 (28x37) 42x4`

Quatre demi-coups préparatoires, puis rafle finale `42×4` (cf
`final_move.path = 42→31→22→13→4`, 4 captures 9, 18, 27, 37).
Forme canonique du coup de la Trappe (cf `claude_notes`).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH14_006` | `31-27` | +11.25 | 27 | — |

### 14.2. Coups de la Trappe côté blanc (D1, D2, D3, D9)

`published_notation` Dubois :
- `BEG_CH14_001` (ch18 D1, rafle `30×6`) :
  `26-21 (17x26) 32-27 (22x24) 30x6`
- `BEG_CH14_002` (ch18 D2, révision du coup de Rappel) :
  `28-23 (19x39) 38-33 (39x28) 32x14`
- `BEG_CH14_003` (ch18 D3, rafle finale en 9) :
  `28-23 (17x19) 33-28 (24x31) 36x9`
- `BEG_CH14_009` (ch18 D9, van Dijk, mécanisme inattendu) :
  `28-22 (18x36) 34-30 (25x23) 33-28 (23x32) 38x9`

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH14_001` | `26-21` | +2.38 | 27 | — |
| `BEG_CH14_002` | `28-23` | +10.05 | 32 | — |
| `BEG_CH14_003` | `28-23` | +89.51 | 33 | — |
| `BEG_CH14_009` | `28-22` | +99.75 | 26 | — |

### 14.3. Combinaisons longues à 7 demi-coups (D4, D5, D8)

Plusieurs parties historiques dépassent les 5 demi-coups habituels.

Exemple — `BEG_CH14_004` (Dubois ch18 D4, Kocken-Doomernik 1971, trait
aux noirs) :

> `published_notation` Dubois : `(16-21) 27x7 (18x27) 7x20 (8-12) 32x21 (23x45)`

Trappe noire à 7 demi-coups (cf `claude_notes`, `final_move.path =
23→32→43→34→45`, captures 28, 38, 39, 40).

`published_notation` Dubois pour les autres parties :
- `BEG_CH14_005` (ch18 D5, Hoogland-van den Broek 1912, coup de dame
  à 4) : `28-23 (19x39) 30x19 (13x33) 38x29 (39x30) 35x4`
- `BEG_CH14_008` (ch18 D8, Bronstring-Holstvoogd 2005, trait aux noirs,
  7 demi-coups) : `(20-24) 29x9 (16-21) 27x7 (18x27) 9x18 (1x43)`

🔴 **Divergences Scan flaggées (cosmétiques)** — Pour `BEG_CH14_004` et
`BEG_CH14_008`, la `published_notation` commence par un coup entre
parenthèses (`(16-21)`, `(20-24)`) alors que le PV Scan le donne en
clair — convention Dubois trait aux noirs.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH14_004` | `16-21` | +2.78 | 30 | 🔴 |
| `BEG_CH14_005` | `28-23` | +5.47 | 27 | — |
| `BEG_CH14_008` | `20-24` | +7.20 | 32 | 🔴 |

### 14.4. Autres parties historiques (D7, D10)

Exemple — `BEG_CH14_007` (Dubois ch18 D7, Maertzdorf-Alofs 1997) :

> `published_notation` Dubois : `29-24 (20x38) 39-34 (22x33) 27-21 (17x28) 43x5`

Coup de dame à 5 par trappe (cases vides 37, 38 — cf `concept`).
`final_move.path = 43→32→23→14→5`, 4 captures.

🔴 **Divergence Scan flaggée** — Pour `BEG_CH14_007`, Scan recommande
`43-38` comme premier coup (éval −0.05, profondeur 23), là où la
`published_notation` Dubois commence par `29-24`. Cette substitution
de premier coup propose une voie alternative — l'éval Scan proche de
zéro indique que la position est très équilibrée. Le PV complet est
dans `scan_analysis_debutant.json`. Le mécanisme Dubois reste
enseignable mais le verdict objectif est nettement plus tempéré.

Exemple — `BEG_CH14_010` (Dubois ch18 D10, Kats-Agafonov 1965, trait
aux noirs, envoi à dame + ricochet) :

> `published_notation` Dubois : `(14-20) 23x3 (17-21) 3x17 (21x34) 40x29 (24x11)`

`final_move=None` à cause de la rafle de dame `(3x17)` (cf
`claude_notes`, R007).

🔴 **Divergence Scan flaggée (cosmétique)** — Pour `BEG_CH14_010`,
`(14-20)` entre parenthèses (trait aux noirs).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH14_007` | `43-38` | -0.05 | 23 | 🔴 |
| `BEG_CH14_010` | `14-20` | +6.49 | 31 | 🔴 |

---

## Chapitre 15 — Le coup de Talon
<!-- pedagogy-motifs: coup_de_talon -->

Le **coup de Talon** est un mécanisme surprenant qui **ne dévoile le
point d'appui de la rafle qu'au dernier moment**. Une formation
particulière (souvent 31-36-37-41-46 pour les blancs) cache la véritable
case de départ jusqu'à la fin.

Les 10 exercices viennent du chapitre 19 de Dubois (pages 60-62).

### 15.1. Coups de Talon purs (D4, D5)

Exemple — `BEG_CH15_004` (Dubois ch19 D4, coup de dame à 3 par talon
pur) :

> `published_notation` Dubois : `34-29 (23x43) 33-29 (24x33) 28x48 (17x28) 32x3`

`final_move.path = 32→23→12→3`, 3 captures (8, 18, 28). Forme
canonique (cf `claude_notes`).

Exemple — `BEG_CH15_005` (Dubois ch19 D5, coup de dame à 1, symétrique
du D4) :

> `published_notation` Dubois : `32-28 (23x43) 33-28 (22x33) 29x49 (20x29) 34x1`

🔴 **Divergence Scan flaggée** — Pour `BEG_CH15_004`, Scan recommande
`33-29` comme premier coup (éval +92.04, profondeur 28), là où la
`published_notation` Dubois commence par `34-29`. C'est une substitution
de premier coup ; les deux variantes mènent au même mécanisme de talon,
mais Scan privilégie la séquence `33-29` puis `34-29`. Le PV complet
est dans `scan_analysis_debutant.json`.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH15_004` | `33-29` | +92.04 | 28 | 🔴 |
| `BEG_CH15_005` | `32-28` | +9.70 | 30 | — |

### 15.2. Coups de Talon côté blanc (D1, D2, D9)

`BEG_CH15_001` (Dubois ch19 D1) : coup de mazette dans le coup de Talon.

> `published_notation` Dubois : `28-23 (19x19) 27-22 (17x28) 32x5`

La notation Dubois imprime `(19x19)` — probable typo PDF que
`claude_notes` confirme. La reconstruction a néanmoins réussi
(`final_move.path = 32→23→14→5`, captures 10, 19, 28).

`published_notation` Dubois pour les variantes additionnelles :
- `BEG_CH15_002` (ch19 D2, rafle en 7) :
  `34-30 (25x32) 33-28 (22x33) 29x7`
- `BEG_CH15_009` (ch19 D9, pur coup de la Trappe) :
  `37-31 (36x27) 38-33 (27x38) 24-20 (15x24) 29x7`
- `BEG_CH15_010` (ch19 D10, de Jongh-Bizot 1927) :
  `35-30 (24x33) 42-37 (33x42) 31-26 (42x31) 26x10`

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH15_001` | `28-23` | +1.57 | 25 | — |
| `BEG_CH15_002` | `34-30` | +3.60 | 28 | — |
| `BEG_CH15_009` | `37-31` | +4.88 | 28 | — |
| `BEG_CH15_010` | `35-30` | +4.47 | 25 | — |

### 15.3. Combinaisons à 7 demi-coups (parties historiques)

Trois parties historiques à 7 demi-coups montrent le coup de Talon dans
sa forme la plus complexe.

Exemple — `BEG_CH15_003` (Dubois ch19 D3, Lewkowicz-Blokland 1998) :

> `published_notation` Dubois : `27-21 (16x38) 33x42 (24x33) 44-40 (35x44) 50x8`

`final_move.path = 50→39→28→19→8`, 4 captures (13, 23, 33, 44).

🔴 **Divergence Scan flaggée** — Pour `BEG_CH15_003`, Scan recommande
`27-22` comme premier coup (éval +8.77, profondeur 29), là où la
`published_notation` Dubois commence par `27-21`. Cette substitution
de premier coup remplace le sacrifice initial par un autre adjacent ;
le PV complet est dans `scan_analysis_debutant.json`. Le mécanisme
Dubois reste enseignable pour le coup de Talon.

`published_notation` Dubois pour `BEG_CH15_006` (ch19 D6,
Vatutin-Steijlen 2007, Talon + Trappe) :
`44-39 (35x44) 23-18 (12x34) 50x10 (15x4) 21x1`

Exemple — `BEG_CH15_007` (Dubois ch19 D7, Wiering-Sier 2008, trait aux
noirs, 7 demi-coups) :

> `published_notation` Dubois : `(7-12) 16x7 (19-23) 28x8 (17x28) 8x17 (1x41)`

Trappe cachée (cf `claude_notes`, `final_move.path = 1→12→21→32→41`,
captures 7, 17, 27, 37).

`published_notation` Dubois pour `BEG_CH15_008` (ch19 D8,
Depaepe-Groenendijk 2014, trait aux noirs, 7 demi-coups) :
`(7-12) 16x7 (14-20) 25x14 (19x10) 30x17 (1x41)`

🔴 **Divergences Scan flaggées (cosmétiques)** — Pour `BEG_CH15_007` et
`BEG_CH15_008`, la `published_notation` commence par `(7-12)` (trait
aux noirs).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH15_003` | `27-22` | +8.77 | 29 | 🔴 |
| `BEG_CH15_006` | `44-39` | +6.94 | 31 | — |
| `BEG_CH15_007` | `7-12` | +99.83 | 99 | 🔴 |
| `BEG_CH15_008` | `7-12` | +2.33 | 28 | 🔴 |

### 15.4. Note sur D1

`BEG_CH15_001` (Dubois D1) contient une coquille typographique dans le
PDF (`(19x19)` au lieu d'une notation valide — cf `claude_notes`). La
reconstruction a néanmoins réussi en interprétant la suite logique de
la position.

---

## Chapitre 16 — Le coup Philippe
<!-- pedagogy-motifs: coup_philippe -->

Le **coup Philippe** est l'un des mécanismes les plus **simples et les
mieux connus** du répertoire. Il a déjà été abordé au chapitre 6
(`BEG_CH06_002`) sous sa forme la plus élémentaire. Ce chapitre final
l'étudie sous ses formes plus développées, avec **partenariats
fréquents** avec d'autres coups nommés (coup de mazette, coup turc).

Les 10 exercices viennent du chapitre 20 de Dubois (pages 63-65).

### 16.1. Forme la plus élémentaire (rappel)

`BEG_CH06_002` (Dubois ch5 D1) — voir §6.2.

> `published_notation` Dubois : `34-30 (25x34) 40x7`

3 pions blancs contre 3 pions noirs, sacrifice central, rafle de 3
captures. C'est la forme la plus épurée du coup Philippe.

### 16.2. Forme complète (D2 — Dartelen-Ligthart 1938)

Exemple — `BEG_CH16_002` (Dubois ch20 D2) :

> `published_notation` Dubois : `33-28 (22x24) 31x22 (18x27) 34-30 (25x34) 40x16`

Forme à 6 demi-coups qui combine coup Philippe et collage. Avec deux
pions noirs en 23 et 25, le sacrifice `33-28` puis le collage `34-30`
ouvrent la rafle `40×16` (cf `final_move.path = 40→29→18→7→16`,
captures 11, 12, 23, 34).

`published_notation` Dubois pour les variantes :
- `BEG_CH16_003` (ch20 D3, variante via 37-31) :
  `37-31 (26x28) 33x22 (18x27) 34-30 (25x34) 40x16`
- `BEG_CH16_004` (ch20 D4, Davidov-Romanov 1963, schéma Philippe via
  attaque noire) : `31-26 (21x23) 26-21 (16x27) 34-30 (25x34) 40x16`
- `BEG_CH16_005` (ch20 D5, combinaison piégeuse — la voie évidente
  échoue, cf `claude_notes`) :
  `32-27 (21x34) 39x30 (35x24) 33-28 (22x33) 38x7`
- `BEG_CH16_006` (ch20 D6, Leijenaar-Romanskaia 2003, rafle `48×26`) :
  `33-28 (22x24) 34-30 (25x34) 32-28 (23x43) 48x26`

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH16_002` | `33-28` | +0.50 | 23 | — |
| `BEG_CH16_003` | `37-31` | +2.69 | 25 | — |
| `BEG_CH16_004` | `31-26` | +0.95 | 23 | — |
| `BEG_CH16_005` | `32-27` | +7.49 | 28 | — |
| `BEG_CH16_006` | `33-28` | +1.08 | 24 | — |

### 16.3. Coup de Mazette dans le chapitre Philippe (D7)

Exemple — `BEG_CH16_007` (Dubois ch20 D7) :

> `published_notation` Dubois : `28-22 (17x28) 25-20 (14x34) 40x18 (13x31) 32x5`

« Coup de mazette classique » selon `claude_notes`. À retenir : la
prise forcée `(13×31)` libère la rafle finale `32×5`
(`final_move.path = 32→23→14→5`, 3 captures 10, 19, 28).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH16_007` | `28-22` | +5.01 | 24 | — |

### 16.4. Coup turc avec envoi à dame (D1 — conclusion du livre)

`BEG_CH16_001` (Dubois ch20 D1) est un **coup turc** combiné à un envoi
à dame — « la dernière combinaison en 3 temps » selon Dubois, position-
conclusion du livre Apprentissage Combinaisons.

> `published_notation` Dubois : `37-31 (26x48) 47-41 (48x33) 38x29`

Le sacrifice `37-31` force la promotion noire en 48 (`26x48`), puis
`47-41` provoque la rafle de dame `(48x33)`, enfin la rafle blanche
`38×29` conclut (`final_move=None`, R007 — rafle de dame, cf
`claude_notes`).

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH16_001` | `37-31` | +5.67 | 30 | — |

### 16.5. Parties historiques côté noir (D8) et complexes (D9, D10)

Exemple — `BEG_CH16_008` (Dubois ch20 D8, Merin-Agafonow 1975, trait
aux noirs, envoi à dame avec temps de réserve) :

> `published_notation` Dubois : `(14-19) 27x18 (13x22) 24x4 (17-21) 4x27 (21x23)`

Le sacrifice noir `(14-19)` est suivi de l'envoi à dame du blanc
(`24x4` — promotion), puis le rappel `(17-21)` ramène la dame en 27
(`4x27`), et la rafle noire `(21×23)` conclut (`final_move=None`, R007).

🔴 **Divergence Scan flaggée (cosmétique)** — Pour `BEG_CH16_008`,
`(14-19)` entre parenthèses (trait aux noirs).

Exemple — `BEG_CH16_009` (Dubois ch20 D9, visualisation 32-28) :

> `published_notation` Dubois : `34x23 (19x48) 30x37 (48x31) 36x27`

`concept` de la fixture : « pas de vraie méthode, il faut visualiser ».
Envoi à dame du noir avec rafle de dame `(48×31)`, `final_move=None`
(R007, cf `claude_notes`).

🔴 **Divergence Scan flaggée** — Pour `BEG_CH16_009`, Scan recommande
`32-28` comme premier coup (éval +4.80, profondeur 32), là où la
`published_notation` Dubois commence par `34x23` (qui est une rafle
forcée — la fixture indique implicitement que les noirs ont attaqué).
Cette substitution change radicalement la séquence : Scan trouve un
sacrifice silencieux `32-28` plus efficace que la rafle immédiate. Le
PV complet est dans `scan_analysis_debutant.json` — le coup Dubois
reste enseignable pour le mécanisme de l'envoi à dame.

`published_notation` Dubois pour `BEG_CH16_010` (ch20 D10,
Aliar-Huijzer 2010) :
`27-21 (16x29) 42-38 (23x43) 34x14 (25x34) 30x6`

`claude_notes` mentionne une anomalie dans la notation publiée :
`30.48x6` — variante 30x6 retenue.

**Validation Scan** :

| Fixture | Premier coup PV | Éval | Profondeur | Divergence |
|---------|-----------------|------|-----------|------------|
| `BEG_CH16_008` | `14-19` | +1.41 | 26 | 🔴 |
| `BEG_CH16_009` | `32-28` | +4.80 | 32 | 🔴 |
| `BEG_CH16_010` | `27-21` | +2.99 | 31 | — |

---

## Conclusion

Le lecteur qui a parcouru les 16 chapitres et travaillé les 166 positions
de ce manuel a acquis le **bagage tactique d'un joueur de niveau club** :

- **Règles complètes** du jeu international FMJD 10×10
- **Méthodes systématiques** de recherche de combinaisons (rafle finale,
  points de contact, temps de repos)
- **8 mécanismes fondamentaux** : prise majoritaire, collage, envoi à
  dame, gambit, points de contact, temps de repos, création de temps
  de repos, coup parallèle
- **8 coups nommés** : Express, Ricochet, Rappel, Renversé, Napoléon,
  Trappe, Talon, Philippe, plus Mazette (introduit en passant)

**Pour aller plus loin** : le manuel Intermédiaire abordera le sens
positionnel (centre, ailes, opposition, tempo), les fins de partie
classiques, et les bibliothèques d'ouvertures (système Roozenburg,
Keller, etc.).

**Pour s'entraîner concrètement** : chaque position de ce manuel est
disponible comme exercice dans l'application Draught Master. Tapez son
identifiant (`BEG_CH09_001` par exemple) dans le moteur de recherche
de l'application pour la charger directement au damier.

---

## Annexes

### A. Index des coups nommés

Les **coups nommés** sont des mécanismes combinatoires fréquents
auxquels la tradition damiste a donné un nom propre. Ils se reconnaissent
à une **signature tactique** (suite de sacrifices, forme de la rafle,
position des pions). Cet index reprend les descriptions des chapitres
correspondants ; cf chapitres 9 à 16 pour le développement complet et
les fixtures associées.

#### Coup de Mazette — *ch3 (intro), ch16 (variante)*

**Signature** : sacrifice central qui contraint l'adversaire à une
prise, ouvrant une rafle sur la grande diagonale. Premier des coups
nommés rencontrés dans ce manuel (cf §3.3).

**Détecteur dilf** : ❌ à implémenter.

#### Coup royal — *ch4 §4.3 (`BEG_CH04_006`), ch5 §5.2 (`BEG_CH05_003`)*

**Signature** : variante célèbre de collage avec rafle aboutissant en
case 7. Forme canonique : `path = 40→29→20→9→18→7`, 5 captures.

**Détecteur dilf** : ✅ `pedagogy/motifs/coup_royal.py`.

#### Coup de l'Express — *ch9 (canonique), ch13 (D7)*

**Signature** : **quatre sacrifices consécutifs** qui acheminent les
pions adverses par paires successives, suivis d'une rafle finale typique
`33×2` ou `33×4` sur la grande diagonale.

**Détecteur dilf** : ❌ à implémenter.

#### Coup de Ricochet — *ch10*

**Signature** : rafle qui **revient sur sa case de départ** (ou très
proche) après avoir traversé une zone clé. Variante du coup de l'Express
exploitant mieux l'aile.

**Détecteur dilf** : ❌ à implémenter.

#### Coup de Rappel — *ch11 (canonique), ch14 (combiné Trappe)*

**Signature** : exploite une rafle adverse qui **descend trop bas**
(souvent jusqu'en case 39 pour les noirs) ; un nouveau sacrifice
**force le pion à remonter** (« rappel ») où il est capturé.

**Détecteur dilf** : ❌ à implémenter.

#### Coup Renversé — *ch12 §12.1 (`BEG_CH12_006`)*

**Signature** : mécanisme moins courant mais utile car il **se marie
facilement avec d'autres coups nommés** (mazette, Philippe, Ricochet).
Inclut deux variantes : coup de chevron (§12.2) et coup parallèle (§12.4).

**Détecteur dilf** : ❌ à implémenter.

#### Coup de chevron — *ch12 §12.2 (`BEG_CH12_002`, Datel-Schwarzman 1977)*

**Signature** : variante du coup renversé, nommée d'après la forme de la
rafle finale `(21×25)` côté noir (`path = 21→32→43→34→25`, 4 captures).

**Détecteur dilf** : ❌ à implémenter.

#### Coup parallèle — *ch12 §12.4 (`BEG_CH12_008`, Bergsma-Spoelstra 1952)*

**Signature** : variante du coup renversé combinant **plusieurs sacrifices
parallèles** ; notation Dubois utilise `(ad lib)` pour les captures forcées
équivalentes.

**Détecteur dilf** : ❌ à implémenter.

#### Coup Napoléon — *ch13 (canonique), ch10 (D7)*

**Signature** : combinaison en **4 sacrifices** débouchant sur une rafle
longue typique `31×4`, `39×8` ou `40×16` (selon la diagonale utilisée).
Forme la plus pure dans Dubois ch17 D9.

**Détecteur dilf** : ❌ à implémenter.

#### Coup de la Trappe — *ch14 (canonique), ch11 (D5, D6), ch12 (D5)*

**Signature** : un sacrifice préliminaire **piège** un pion adverse
dans une position où sa capture forcée par un sacrifice subséquent
**ouvre** la rafle finale. Mécanisme sophistiqué.

**Détecteur dilf** : ❌ à implémenter.

#### Coup de Talon — *ch15 (canonique), ch8 (D9)*

**Signature** : mécanisme surprenant qui **ne dévoile le point d'appui
de la rafle qu'au dernier moment**. Formation typique 31-36-37-41-46
côté blanc qui cache la véritable case de départ.

**Détecteur dilf** : ❌ à implémenter.

#### Coup Philippe — *ch16 (canonique), ch6 (D1, `BEG_CH06_002`)*

**Signature** : l'un des mécanismes les plus **simples et les mieux
connus** du répertoire. Déjà abordé au chapitre 6 sous sa forme
élémentaire.

**Détecteur dilf** : ❌ à implémenter.

#### Coup turc — *signalé en ch4 (`BEG_CH04_001`), ch6 (`BEG_CH06_004`, `BEG_CH06_011`), ch8 (`BEG_CH08_004`)*

**Signature** : motif où la rafle passe sur la même ligne/colonne
avec un pion adverse qui se trouve « écrasé » par un saut subséquent.
Souvent annoté dans `claude_notes` (`coup turc par <case>`) plutôt que
nommé explicitement par Dubois.

**Détecteur dilf** : ❌ à implémenter.

#### Récapitulatif

| Coup nommé | Chapitre principal | Aperçus dans | Détecteur dilf |
|---|---|---|---|
| Coup de Mazette | ch3 §3.3 | ch16 | ❌ à implémenter |
| Coup royal | ch4 §4.3, ch5 §5.2 | — | ✅ `pedagogy/motifs/coup_royal.py` |
| Coup de l'Express | ch9 | ch13 (D7) | ❌ |
| Coup de Ricochet | ch10 | — | ❌ |
| Coup de Rappel | ch11 | ch14 | ❌ |
| Coup Renversé | ch12 §12.1 | — | ❌ |
| Coup de chevron | ch12 §12.2 | — | ❌ |
| Coup parallèle | ch12 §12.4 | — | ❌ |
| Coup Napoléon | ch13 | ch10 (D7) | ❌ |
| Coup de la Trappe | ch14 | ch11 (D5, D6), ch12 (D5) | ❌ |
| Coup de Talon | ch15 | ch8 (D9) | ❌ |
| Coup Philippe | ch16 | ch6 (D1) | ❌ |
| Coup turc | (motif transverse) | ch4, ch6, ch8 | ❌ |

### B. Sources

- **Jean-Pierre Dubois** — *Apprentissage Combinaisons*, ~152 positions
  utilisées (chapitres 3 à 9 et 13 à 20 du livre).
- Connaissances générales du jeu pour les chapitres 1 et 2 (règles
  FMJD canoniques) — 12 positions.
- 2 positions inventées ad-hoc (ch2, illustrations de règles).

Pour un **audit fixture-par-fixture** (source, référence Dubois, statut
Scan, statut `final_move`, notes Claude par fixture), voir
[`sources_debutant.md`](sources_debutant.md). Ce document est généré
automatiquement par `python3 scripts/regenerate_sources_doc.py` depuis
`fixtures_debutant.py` et `scan/scan_analysis_debutant.json` — toute
divergence narrative entre le manuel et ce tableau doit être
investiguée.

### C. Notation Dubois

La notation utilisée dans ce manuel suit les conventions Dubois,
documentées dans `docs/dubois-notation.md` du framework dilf
(introduit par la PR #31, mai 2026). Conventions principales :

- `aXb` : rafle abrégée, de `a` à `b` (le chemin se déduit)
- `(c)` : coup adverse
- `(ad lib)` : captures forcées équivalentes (cf chapitre 7 D10)
- `+1p`, `+2p` : indicateur de gain matériel net (non-rafle)

### D. Statistiques du manuel

- **166 positions** réparties sur 16 chapitres
- **152 du corpus Dubois** (92 %), 12 de connaissance générale (7 %),
  2 inventées (1 %)
- **135 positions** ont une notation complète reconstruite (81 %)
- **31 positions** ont `final_move=None` (envois à dame, gambits,
  fixtures illustratives sans rafle — détails dans les `claude_notes`
  des fixtures et limitations PR #31)
- **3 blocages structurels** initialement détectés, **tous résolus**
  (cf R009, R010, R011 dans `RESOLUTIONS_debutant.md`)
- **6 coquilles PDF** détectées et corrigées (R002, R004, R006, R009,
  R010, R011)
- **11 résolutions** consignées dans `RESOLUTIONS_debutant.md`
  (R001 à R011)

---

*Manuel produit en mai 2026 par Claude (Anthropic) dans le cadre du
projet Draught Master, en collaboration avec l'auteur du projet et
le framework `dilf` (Draught Intelligence Learning Framework). Le code
source des fixtures est dans `fixtures_debutant.py`.*

