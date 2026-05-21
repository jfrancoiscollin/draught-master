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
contemporaine). Les 14 restantes illustrent des règles canoniques ou des
schémas inventés à fin pédagogique.

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
et atterrit en 22 (notation `31x22`). Voir aussi `BEG_CH02_004` pour
illustrer la **capture vers l'arrière** : le pion blanc 22 saute le
noir 27 vers l'arrière et atterrit en 31 (notation `22x31`) — ce qui
serait interdit pour un coup simple.

### 2.3. Rafle (capture multiple)

Si après avoir capturé un pion, le pion captureur peut **immédiatement
en capturer un autre** (en sautant à nouveau), il **doit** le faire. Il
peut ainsi enchaîner plusieurs sauts dans la même séquence. C'est ce
qu'on appelle une **rafle**.

Voir `BEG_CH02_005` : le pion blanc 31 saute le noir 27 (atterrit en 22),
puis enchaîne en sautant le noir 17 pour atterrir en 11. Notation
`31x11`, deux pions noirs capturés en une seule séquence.

### 2.4. Prise obligatoire

Quand un pion ou une dame **peut capturer**, la capture est
**obligatoire**. Le joueur ne peut pas refuser de prendre. C'est l'une
des règles les plus distinctives du jeu de dames international.

Voir `BEG_CH02_006` : le pion blanc 31 ne peut pas jouer 31-26 (coup
simple) parce que la prise `31x22` du noir 27 est disponible — il doit
prendre, même s'il préférerait jouer ailleurs.

### 2.5. Prise maximale (règle du nombre)

Quand **plusieurs captures** sont possibles, le joueur doit choisir
celle qui **capture le maximum de pièces**. Si deux rafles capturent le
même nombre de pièces, le joueur choisit librement (sauf cas spéciaux
documentés dans la règlementation FMJD).

Voir `BEG_CH02_007` : depuis la position W{31, 38} B{23, 27, 33}, le
blanc a deux captures possibles — `31x22` ne prend qu'un seul pion (le
27), tandis que `38x18` prend deux pions (33 et 23). La rafle `38x18`
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
de Mazette**.

### 3.1. La prise majoritaire

C'est le mécanisme de base. Le sacrifice blanc force le noir à effectuer
une **prise multiple** (plusieurs pions à la fois) par la règle du
nombre, ce qui dégarnit son camp et ouvre la voie à une rafle blanche
encore plus longue.

Voir `BEG_CH03_001` (Dubois D1) : `26-21 (17×28) 43×3`. Le sacrifice
blanc `26-21` est gobé par le noir 17 qui doit prendre par la rafle
majoritaire `17→26→37→28` (capturant 21, 31, 32). La rafle blanche
finale `43×3` ramasse alors 38, 28, 19 et 9 en traversant la grande
diagonale jusqu'à la promotion.

Voir aussi `BEG_CH03_003` (`33-29 (23×21) 26×10`), `BEG_CH03_005`
(`37-31 (27×20) 25×5`), `BEG_CH03_006` (`34-29 (25×32) 29×38`),
`BEG_CH03_008` (`33-29 (24×31) 36×20` — oser sacrifier 3 pions
consécutifs), `BEG_CH03_009` (`44-39 (25×43) 48×10`), `BEG_CH03_010`
(`34-30 (23×32) 30×37`) pour différentes variantes.

### 3.2. Le collage

Mécanisme plus subtil : quand le noir attaque **deux pions blancs**,
un blanc se sacrifie sur la case-clé de l'attaque, forçant le noir à
une prise majoritaire qui ouvre la rafle blanche.

Voir `BEG_CH03_004` (Dubois D4) : `34-29 (23×21) 29×7`. Les noirs
attaquaient deux pions blancs ; le sacrifice `34-29` exploite cette
configuration pour transformer la menace en combinaison gagnante.

Voir aussi `BEG_CH03_007` (`33-29 (17×37) 29×18`) — collage canonique
quand le noir attaque 2 pions.

### 3.3. Le coup de Mazette

Premier des **coups nommés** rencontrés dans ce manuel : un sacrifice
central qui contraint l'adversaire à une prise, ouvrant une rafle sur
la grande diagonale.

Voir `BEG_CH03_002` (Dubois D2) : `28-22 (17×28) 32×5` — le sacrifice
`28-22` force le noir 17 à prendre, et la rafle blanche `32→23→14→5`
traverse jusqu'à la promotion en capturant 3 pions noirs.


---

## Chapitre 4 — Le collage et l'envoi à dame combinés
<!-- pedagogy-motifs: envoi_a_dame, coup_turc -->

Le **collage** introduit au chapitre 3 (§3.2) prend toute sa puissance
quand il est combiné à un **envoi à dame** : on sacrifie un pion qui
arrive à la dernière rangée et se promeut, puis on récupère une dame
adverse qu'on capture avec avantage. C'est l'une des combinaisons les
plus spectaculaires du répertoire.

Les exercices viennent des chapitres 6 et 7 de Dubois (pages 20-25).

### 4.1. Combinaisons à coup turc

Un **coup turc** est une rafle dont la trajectoire forme une boucle —
le pion (ou la dame) revient près de sa case de départ après avoir
capturé. Voir `BEG_CH04_001`, `BEG_CH04_002`.

### 4.2. Envois à dame côté blanc

Le mécanisme typique : un pion blanc se sacrifie sur la 1ère rangée
(case 1 à 5), promeut en dame, et la dame blanche fait une rafle qui
détruit la défense noire.

Voir `BEG_CH04_005` (Dubois ch6 D7) : `29-24 (22×33) 32-28 (19×39) 28×6`.
Deux sacrifices successifs forcent les noirs à des prises majoritaires,
puis la rafle blanche `28→19→8→17→6` traverse jusqu'à la promotion en
dame en case 6.

### 4.3. Envois à dame côté noir

Le mécanisme symétrique : un pion noir descend en 46-50 et promeut.

Voir `BEG_CH04_006`, `BEG_CH04_007`.

### 4.4. Combinaisons longues à plusieurs phases

Certaines combinaisons enchaînent plusieurs collages successifs avant
la rafle finale. Voir `BEG_CH04_010` (Dubois ch7 D8) :
`34-29 (23×25) 27-22 (17×28) 32×3`. Deux sacrifices `34-29` puis
`27-22` enchaînés, chacun forçant une prise majoritaire noire, suivis
de la rafle finale `32→23→14→3` qui capture 3 pions et promeut en
dame.

---

## Chapitre 5 — L'envoi à dame
<!-- pedagogy-motifs: envoi_a_dame -->

L'**envoi à dame** est la promotion *volontaire* d'un pion par
sacrifice. On accepte de donner un pion (qui se promeut), pour
exploiter la dame nouvellement créée — ou pour piéger la dame adverse
qu'on récupère ensuite.

Ce chapitre approfondit le mécanisme déjà rencontré au chapitre 4,
avec 10 exercices issus du chapitre 4 de Dubois (pages 14-16).

### 5.1. Envoi à dame avec rafle directe

Le schéma le plus simple : un pion blanc atteint la case 1, 2, 3, 4 ou
5 par sacrifice, devient dame, et la dame fait immédiatement une rafle
gagnante.

Voir `BEG_CH05_001`, `BEG_CH05_002`, `BEG_CH05_003`.

### 5.2. Envoi à dame avec collage

Variante plus subtile : la promotion se fait via un collage, qui force
la position adverse à dégager les diagonales.

Voir `BEG_CH05_004`, `BEG_CH05_005`.

### 5.3. Envoi à dame côté noir

Symétriquement, le noir peut se sacrifier pour promouvoir.

Voir `BEG_CH05_009` (Dubois ch4 D9), `BEG_CH05_010` (Dubois ch4 D10 —
partie Bakker-Ivens 1976).

### 5.4. Pièges classiques

Certains envois à dame sont des **pièges** : on attire la dame adverse
sur une case où elle est ensuite capturable. Voir `BEG_CH05_007`.

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
trois parties historiques notables :
- **Laporta-Mostovoy 1970** (`BEG_CH06_007`)
- **Bergsma-de Vries 1961** (`BEG_CH06_009`)
- **Leclercq-Weiss 1903** (`BEG_CH06_010`)

### 6.1. L'exemple introductif

Voir `BEG_CH06_001` : position où la rafle finale `39×6` n'est pas
intuitive, mais l'analyse des 4 points de contact (34-30, 29-23, 37-32,
31-27) révèle qu'**inattendu** `31-27` ouvre une prise majoritaire à 4
pions qui débouche sur la rafle. **Sans l'analyse des points de
contact, ce coup ne se trouve pas.**

### 6.2. Application aux mécanismes connus

La méthode des points de contact permet de redécouvrir les mécanismes
appris précédemment : **prise majoritaire** (`BEG_CH06_003`), **collage**
(`BEG_CH06_004`), **gambit** (`BEG_CH06_005`).

### 6.3. Le coup Philippe (préview)

Le `BEG_CH06_002` est la forme la plus élémentaire du **coup Philippe**
— un coup nommé qui sera détaillé au chapitre 16. Trois pions blancs
contre trois pions noirs, sacrifice central `34-30`, rafle `40×7`.

### 6.4. Rafles « cachées »

Certaines combinaisons sont si peu intuitives qu'elles ne se trouvent
que par la méthode systématique. Voir `BEG_CH06_010` : rafle `1×41`
qui semble bloquée par le pion 36 — la méthode des points de contact
révèle que `(26-31)` fait disparaître le pion 36 et ouvre la voie.

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

Les 12 exercices (2 narratifs + 10 du chapitre 8 Dubois) montrent
comment exploiter ces temps de repos.

### 7.1. Cascade de temps de repos

L'exemple narratif `BEG_CH07_001` montre comment une seule attaque
noire (le pion noir 25 menace le pion blanc 30) ouvre une chaîne de
**trois** temps de repos consécutifs : `42-37 (25×34) 40×20 (15×24)
28-22 (17×28) 32×14`. Chaque coup blanc bénéficie d'un temps de repos
parce que le noir est forcé de capturer après lui.

### 7.2. Combinaison en phases

L'exemple `BEG_CH07_002` montre une combinaison à **3 phases distinctes**
(6 demi-coups au total) :
- **Phase 1** — placer un pion en 19 par sacrifice
- **Phase 2** — acheminer une pièce noire en 30 par envoi à dame
- **Phase 3** — exécuter la rafle finale `35×2`

### 7.3. Particularités

- `BEG_CH07_002` et `BEG_CH07_009` contiennent un **envoi à dame** —
  `final_move=None` par limitation actuelle du module.
- `BEG_CH07_012` (Dubois ch8 D10) introduit la notation `(ad lib)` :
  l'adversaire a plusieurs captures forcées équivalentes, toutes
  conduisent à la rafle gagnante `38×29`. Voir résolution R008 dans
  `RESOLUTIONS_debutant.md`.

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

### 8.1. Mécanisme typique

Voir `BEG_CH08_002` (l'un des deux exemples narratifs) :
`32-28 (23×21) 34-29 (18×27) 29×7`. Le `32-28` est le sacrifice
créateur, `34-29` est le coup gagné par le temps de repos, et la rafle
`29×7` conclut.

### 8.2. Parties historiques

- **Linssen-Bandstra 1982** (`BEG_CH08_003`)
- **Loenen-Hengefeld 1990** (`BEG_CH08_005`)
- **Badal-Kemperman 1994** (`BEG_CH08_006`) — rafle 24×11 très rare
- **Schippers-Barten 2012** (`BEG_CH08_007`)
- **van Leeuwen-de Jong 1968** (`BEG_CH08_008`)

### 8.3. Préview : le coup de Talon

`BEG_CH08_011` (Dubois D9 — Toet-Luteijn 1977) est un **coup de Talon**
— un coup nommé qui sera détaillé au chapitre 15. La formation blanche
31-36-37-41-46 est caractéristique.

---


## Chapitre 9 — Le coup de l'Express
<!-- pedagogy-motifs: coup_express -->

Le **coup de l'Express** est le premier des **coups nommés** —
des mécanismes combinatoires fréquents auxquels la tradition damiste
a donné un nom propre. Il se reconnaît à un schéma très caractéristique :
**quatre sacrifices consécutifs** qui acheminent les pions adverses
par paires successives, suivis d'une rafle finale typique `33×2` ou
`33×4`.

Les 12 exercices viennent du chapitre 13 de Dubois (pages 42-44).

### 9.1. La forme canonique

L'exemple narratif `BEG_CH09_001` montre la séquence complète :
`37-31 (26×37) 27-21 (16×27) 28-22 (27×18) 38-32 (37×28) 33×2`.

Le pion blanc `33` parcourt toute la grande diagonale (33→22→13→2) en
capturant 3 pions. La signature visuelle est très reconnaissable une
fois qu'on l'a vue.

### 9.2. Variantes

- **Rafle finale `33×4`** : variante symétrique de `33×2`. Voir
  `BEG_CH09_012` (Dubois D10).
- **Coup d'express côté noir** : symétrique avec rafle finissant en
  `(...×44)`. Voir `BEG_CH09_004` (Grotenhuis-Stokkel 1977) et
  `BEG_CH09_005` (Perot-Mostovoy 1968).

### 9.3. Parties historiques

- **Grotenhuis-Stokkel 1977** (`BEG_CH09_004`)
- **Perot-Mostovoy 1968** (`BEG_CH09_005`)
- **Ketelaars-Kalsbeek 1997** (`BEG_CH09_006`)

### 9.4. Cas problématique

`BEG_CH09_007` (Dubois D5) : la solution publiée Dubois ne se reconstruit
pas avec la position extraite. Position contestée, voir `BLOCAGES.md`.

---

## Chapitre 10 — Le coup de Ricochet

Le **coup de Ricochet** est caractérisé par une rafle qui **revient sur
sa case de départ** (ou très proche) après avoir traversé une zone clé.
C'est une variante du coup de l'Express qui exploite mieux l'**aile
gauche encombrée**.

Les 12 exercices viennent du chapitre 14 de Dubois (pages 45-47).

### 10.1. Schéma de base

`BEG_CH10_001` montre la forme canonique :
`34-30 (25×34) 40×18 (13×22) 28×26`. Le pion blanc 28 **ricoche** sur la
case 26 — exactement la case où le pion noir était initialement.

### 10.2. Application en partie

`BEG_CH10_002` montre comment le ricochet s'intègre dans une partie
réelle, avec un sacrifice préliminaire `27-22` qui prépare la formation
caractéristique.

### 10.3. Préview : le coup Napoléon

`BEG_CH10_009` (Dubois D7) est un **coup Napoléon** —
`28-22 (17×28) 27-21 (16×27) 31×24` — qui sera détaillé au chapitre 13.

### 10.4. Cas problématique

`BEG_CH10_008` (Dubois D6) : mismatch position/solution, voir
`BLOCAGES.md`.

---

## Chapitre 11 — Le coup de Rappel

Le **coup de Rappel** exploite une rafle adverse qui **descend trop
bas** (souvent jusqu'en case 39 pour les noirs). Un nouveau sacrifice
**force le pion à remonter** (« rappel ») où il est capturé
définitivement par la rafle finale.

Les 12 exercices viennent du chapitre 15 de Dubois (pages 48-50). Les
trois exemples narratifs montrent les variantes principales :

- **Schéma 1** (`BEG_CH11_001`) : `28-23 (19×39) 38-33 (39×28) 32×3`.
  Le pion noir 19 descend en 39, est rappelé par `38-33`, recapturé en
  28, puis la rafle blanche conclut.
- **Schéma 2** (`BEG_CH11_002`) : rafle finale en 4 au lieu de 3.
- **Schéma 3** (`BEG_CH11_003`) : rappel via case 32.

### 11.1. Parties historiques

- **Rapopport-Gertsenzon 1963** (`BEG_CH11_010`) — 4 demi-coups
- **van Aalten-Clerc 1976** (`BEG_CH11_011`) — 7 demi-coups

### 11.2. Préview : le coup de la Trappe

`BEG_CH11_008` (Dubois D5, Michiels-Marini 1986) et `BEG_CH11_009`
(Dubois D6) sont des **coups de la Trappe** — chapitre 14.

---

## Chapitre 12 — Le coup Renversé

Le **coup Renversé** est un mécanisme moins courant mais utile car il
**se marie facilement avec d'autres coups nommés** : coups de mazette,
coups Philippe, coups de Ricochet. Il inclut une variante notable, le
**coup de chevron**.

Les 10 exercices viennent du chapitre 16 de Dubois (pages 51-53).

### 12.1. Le coup de chevron

`BEG_CH12_002` (Dubois D2 — Datel-Schwarzman 1977) : variante du
renversé connue sous le nom de coup de chevron à cause de la forme de
la rafle finale `21×25`.

### 12.2. Coup renversé pur

`BEG_CH12_006` (Dubois D6) montre la forme canonique :
`33-29 (23×34) 39×30 (25×34) 27-21 (26×28) 32×25`. Caractéristique :
la rafle finale arrive en 25 (case de bord proche du départ).

### 12.3. Coup parallèle

`BEG_CH12_008` (Bergsma-Spoelstra 1952) introduit le **coup parallèle**
— mécanisme apparenté qui utilise une formation symétrique. Contient
la notation `(ad lib)`.

### 12.4. Parties historiques

- **Datel-Schwarzman 1977** (`BEG_CH12_002`)
- **Gordijn-den Hartogh 1952** (`BEG_CH12_004`)
- **Clasquin-van Es 1981** (`BEG_CH12_005`)
- **Bergsma-Spoelstra 1952** (`BEG_CH12_008`)
- **Spoelstra-Bergsma 1972** (`BEG_CH12_009`)

---

## Chapitre 13 — Le coup Napoléon
<!-- pedagogy-motifs: coup_napoleon -->

Le **coup Napoléon** est un coup en **4 sacrifices** débouchant sur une
rafle longue typique `31×4`, `39×8`, `40×16` (selon la diagonale
utilisée). Sa forme la plus pure est montrée dans le D9 Dubois.

Les 10 exercices viennent du chapitre 17 de Dubois (pages 54-56).

### 13.1. Le coup Napoléon pur

`BEG_CH13_009` (Dubois D9) : « un pur coup Napoléon » selon Dubois.
`27-22 (18×29) 28-22 (17×28) 26-21 (16×27) 31×4`. Quatre sacrifices
consécutifs ouvrent la trajectoire de la rafle finale `31→22→33→24→15→4`
(promotion en dame avec 5 captures).

### 13.2. Variantes

- **Rafle `39×8`** : `BEG_CH13_007` (D7)
- **Rafle `40×16`** : `BEG_CH13_008` (D8 — Kolodiev-Weytsman 1973)
- **Rafle `(...×46)` côté noir** : `BEG_CH13_003` (D3 — Baerends-Stoop 1984)

### 13.3. Cas problématique

`BEG_CH13_004` (Dubois D4) : solution publiée entièrement décalée par
rapport à la position extraite, voir `BLOCAGES.md`.

---

## Chapitre 14 — Le coup de la Trappe

Le **coup de la Trappe** est un mécanisme sophistiqué : un sacrifice
préliminaire **piège** un pion adverse dans une position où sa capture
forcée par un sacrifice subséquent **ouvre** la rafle finale. La trappe
est souvent **invisible** pour les joueurs peu entraînés — d'où son nom.

Les 10 exercices viennent du chapitre 18 de Dubois (pages 57-59).

### 14.1. Pur coup de la Trappe

`BEG_CH14_006` (Dubois D6) : forme canonique.
`31-27 (22×31) 26-21 (16×27) 37×26 (28×37) 42×4`.

### 14.2. Combinaisons longues à 7 demi-coups

Plusieurs exercices de ce chapitre dépassent les 5 demi-coups habituels :

- `BEG_CH14_004` (Kocken-Doomernik 1971) : `(16-21) 27×7 (18×27) 7×20
  (8-12) 32×21 (23×45)` — 7 demi-coups
- `BEG_CH14_005` (Hoogland-van den Broek 1912) : 7 demi-coups
- `BEG_CH14_008` (Bronstring-Holstvoogd 2005) : 7 demi-coups

### 14.3. Parties historiques

- **Hoogland-van den Broek 1912** (`BEG_CH14_005`)
- **Kocken-Doomernik 1971** (`BEG_CH14_004`)
- **Maertzdorf-Alofs 1997** (`BEG_CH14_007`)
- **Bronstring-Holstvoogd 2005** (`BEG_CH14_008`)
- **Kats-Agafonov 1965** (`BEG_CH14_010`)

---

## Chapitre 15 — Le coup de Talon
<!-- pedagogy-motifs: coup_de_talon -->

Le **coup de Talon** est un mécanisme surprenant qui **ne dévoile le
point d'appui de la rafle qu'au dernier moment**. Une formation
particulière (souvent 31-36-37-41-46 pour les blancs) cache la véritable
case de départ jusqu'à la fin.

Les 10 exercices viennent du chapitre 19 de Dubois (pages 60-62).

### 15.1. Coups de Talon purs

`BEG_CH15_004` (Dubois D4) : coup de dame à 3.
`34-29 (23×43) 33-29 (24×33) 28×48 (17×28) 32×3`.

`BEG_CH15_005` (Dubois D5) : coup de dame à 1, symétrique du précédent.
`32-28 (23×43) 33-28 (22×33) 29×49 (20×29) 34×1`.

### 15.2. Combinaisons à 7 demi-coups

`BEG_CH15_007` (Wiering-Sier 2008) et `BEG_CH15_008` (Depaepe-Groenendijk
2014) sont des exemples longs et difficiles.

### 15.3. Parties historiques

- **de Jongh-Bizot 1927** (`BEG_CH15_010`)
- **Lewkowicz-Blokland 1998** (`BEG_CH15_003`)
- **Vatutin-Steijlen 2007** (`BEG_CH15_006`)
- **Wiering-Sier 2008** (`BEG_CH15_007`)
- **Depaepe-Groenendijk 2014** (`BEG_CH15_008`)

### 15.4. Note sur D1

`BEG_CH15_001` (Dubois D1) contient une coquille typographique dans le
PDF (`(19x19)` au lieu d'une notation valide). La reconstruction a
néanmoins réussi en interprétant la suite logique de la position.

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

`BEG_CH06_002` (Dubois D1 ch5) : 3 pions blancs contre 3 pions noirs.
`34-30 (25×34) 40×7`. Sacrifice central, rafle de 3 captures.

### 16.2. Forme complète

`BEG_CH16_002` (Dubois ch20 D2 — Dartelen-Ligthart 1938) :
`33-28 (22×24) 31×22 (18×27) 34-30 (25×34) 40×16`. Une forme à 6 demi-coups
qui combine coup Philippe et collage.

### 16.3. Variantes

- **Variante via 37-31** : `BEG_CH16_003`
- **Coup Philippe par attaque noire** : `BEG_CH16_004` (Davidov-Romanov 1963)
- **Combinaison piégeuse** : `BEG_CH16_005` — la voie évidente échoue,
  il faut trouver une autre idée
- **Rafle 48×26** : `BEG_CH16_006` (Leijenaar-Romanskaia 2003)

### 16.4. Coup de Mazette dans le chapitre Philippe

`BEG_CH16_007` (Dubois D7) : « un coup de mazette classique ».
`28-22 (17×28) 25-20 (14×34) 40×18 (13×31) 32×5`. À retenir : la prise
forcée `(13×31)` libère la rafle finale `32×5`.

### 16.5. Coup turc (D1)

`BEG_CH16_001` (Dubois ch20 D1) est un **coup turc** combiné à un envoi
à dame. Mentionné par Dubois comme « la dernière combinaison en 3 temps »
— c'est la position-conclusion du livre Apprentissage Combinaisons.

### 16.6. Parties historiques

- **Dartelen-Ligthart 1938** (`BEG_CH16_002`)
- **Davidov-Romanov 1963** (`BEG_CH16_004`)
- **Merin-Agafonow 1975** (`BEG_CH16_008`)
- **Leijenaar-Romanskaia 2003** (`BEG_CH16_006`)
- **Aliar-Huijzer 2010** (`BEG_CH16_010`)

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

| Coup nommé | Chapitre principal | Aperçus dans | Détecteur dilf |
|---|---|---|---|
| Coup de Mazette | (introduit ch3, ch16) | — | ❌ à implémenter |
| Coup royal | — | (chap général) | ✅ `pedagogy/motifs/coup_royal.py` |
| Coup de l'Express | ch9 | ch13 (D7) | ❌ |
| Coup de Ricochet | ch10 | — | ❌ |
| Coup de Rappel | ch11 | ch14 | ❌ |
| Coup Renversé | ch12 | — | ❌ |
| Coup Napoléon | ch13 | ch10 (D7) | ❌ |
| Coup de la Trappe | ch14 | ch11 (D5, D6), ch12 (D5) | ❌ |
| Coup de Talon | ch15 | ch8 (D9) | ❌ |
| Coup Philippe | ch16 | ch6 (D1) | ❌ |
| Coup parallèle | ch12 (D8) | — | ❌ |
| Coup de chevron | ch12 (D2) | — | ❌ |
| Coup turc | ch16 (D1) | — | ❌ |

### B. Sources

- **Jean-Pierre Dubois** — *Apprentissage Combinaisons*, ~120 positions
  utilisées (chapitres 3 à 9 et 13 à 20 du livre).
- Connaissances générales du jeu pour les chapitres 1 et 2 (règles
  FMJD canoniques).

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
- **132 positions** ont une notation complète reconstruite (79 %)
- **34 positions** ont `final_move=None` (envois à dame, gambits,
  blocages — détails dans `BLOCAGES.md` et limitations PR #31)
- **3 blocages structurels** documentés pour résolution ultérieure
- **3 coquilles PDF** détectées et corrigées
- **8 résolutions** consignées dans `RESOLUTIONS_debutant.md`

---

*Manuel produit en mai 2026 par Claude (Anthropic) dans le cadre du
projet Draught Master, en collaboration avec l'auteur du projet et
le framework `dilf` (Draught Intelligence Learning Framework). Le code
source des fixtures est dans `fixtures_debutant.py`.*

