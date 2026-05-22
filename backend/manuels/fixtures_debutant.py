"""Fixtures du manuel Débutant — Draught Master.

Conforme cadrage §3 : chaque BeginnerPosition référence soit une position
brute extraite par pipeline dilf (source=CORPUS), soit une position
construite par Claude (source=GENERAL_KNOWLEDGE | INVENTED).

Le moteur Scan validera chaque fixture en aval (verified=False par
défaut, voir cadrage §4.6).

Production : conversation Débutant, mai 2026.
Voir RESOLUTIONS_debutant.md pour la trace des résolutions appliquées.

Reconstruction des `final_move` depuis la notation Dubois courte (`aXb`) :
voir `pedagogy.notation.dubois.reconstruct_pawn_capture` (mergé sur main
via PR #31 — cf RESOLUTIONS §R001 et ameliorations_dilf_debutant.md §2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pedagogy.game import GameState, Move


class SourceType(Enum):
    CORPUS = "corpus"
    GENERAL_KNOWLEDGE = "general"
    INVENTED = "invented"


@dataclass(frozen=True)
class BeginnerPosition:
    """Wrapper pédagogique sur une position GameState.

    Voir cadrage §3 pour la sémantique des champs. Le naming des champs
    bibliographiques (`published_notation`, `final_move`) suit la
    convention de `pedagogy/tests/fixtures/dubois_coup_royal.py`
    (template dilf de référence).
    """
    # Identité pédagogique
    id: str
    theme: str
    title: str

    # Position
    state: GameState

    # Pédagogie + traçabilité bibliographique (naming aligné dilf)
    concept: str = ""
    published_notation: str = ""    # Notation Dubois verbatim (ou corrigée si coquille)
    final_move: Move | None = None  # Reconstruction du Move final pour le détecteur
    explanation: str = ""

    # Traçabilité étendue (spécifique aux manuels)
    source: SourceType = SourceType.GENERAL_KNOWLEDGE
    source_ref: str = ""            # ex: "dubois_apprent_combin_p6_d01"
    crop_id: str = ""               # ex: "crops/page_006_d01.png" si CORPUS
    verified: bool = False
    confidence: str = "medium"      # "high" | "medium" | "low"
    claude_notes: str = ""


# ============================================================================
# Chapitre 1 — Le damier et la notation
# ============================================================================

BEG_CH01_001 = BeginnerPosition(
    id="BEG_CH01_001",
    theme="notation",
    title="Position de départ — 20 pions blancs, 20 pions noirs",
    state=GameState(
        white_men=frozenset(range(31, 51)),
        black_men=frozenset(range(1, 21)),
        turn="white",
    ),
    concept=(
        "La position de départ du jeu de dames international comporte 20 pions "
        "blancs (cases 31 à 50) et 20 pions noirs (cases 1 à 20). Les blancs "
        "jouent les premiers."
    ),
    explanation=(
        "Chaque case sombre du damier 10×10 porte un numéro de 1 à 50, "
        "lus de gauche à droite et de haut en bas du point de vue des noirs. "
        "La case 1 est en haut à gauche, la case 50 en bas à droite."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)

BEG_CH01_002 = BeginnerPosition(
    id="BEG_CH01_002",
    theme="notation",
    title="Premier coup : 32-28",
    state=GameState(
        white_men=frozenset((set(range(31, 51)) - {32}) | {28}),
        black_men=frozenset(range(1, 21)),
        turn="black",
    ),
    concept=(
        "Le coup '32-28' désigne le déplacement d'un pion de la case 32 "
        "vers la case 28. C'est l'une des ouvertures les plus jouées."
    ),
    published_notation="32-28",
    explanation=(
        "Un coup simple (sans prise) se note 'case_départ - case_arrivée'. "
        "Le pion 32 avance d'une case en diagonale vers 28."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)


# ============================================================================
# Chapitre 2 — Les règles du jeu
# ============================================================================
# Positions canoniques illustrant chaque règle FMJD. Source : positions
# de pédagogie élémentaire universellement utilisées dans la littérature
# dames (GENERAL_KNOWLEDGE) ou positions construites par Claude pour
# illustrer un point précis (INVENTED, marqué explicitement).

BEG_CH02_001 = BeginnerPosition(
    id="BEG_CH02_001",
    theme="regle_deplacement",
    title="Déplacement du pion — un pas en diagonale vers l'avant",
    state=GameState(
        white_men=frozenset({35}),
        black_men=frozenset(),
        turn="white",
    ),
    concept=(
        "Un pion se déplace d'une case en diagonale, vers l'avant uniquement. "
        "Le pion blanc 35 est sur le bord droit du damier : son seul "
        "déplacement légal est 35-30 (diagonale haut-gauche). La diagonale "
        "haut-droite est bloquée par le bord du plateau."
    ),
    explanation=(
        "Les blancs avancent vers les petites cases (1-5), les noirs vers les "
        "grandes cases (46-50). Un pion ne peut PAS reculer (sauf lors d'une "
        "capture, voir BEG_CH02_004)."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)

BEG_CH02_002 = BeginnerPosition(
    id="BEG_CH02_002",
    theme="regle_deplacement",
    title="Le pion ne peut pas reculer (sauf lors d'une capture)",
    state=GameState(
        white_men=frozenset({22}),
        black_men=frozenset(),
        turn="white",
    ),
    concept=(
        "Le pion blanc 22 ne peut PAS reculer en 27 ou 28 librement. Ses "
        "seuls mouvements possibles sont 22-17 et 22-18 (vers l'avant)."
    ),
    explanation=(
        "Cette règle est asymétrique avec celle des échecs : le pion ne peut "
        "avancer que dans le sens de sa progression. Exception : lors d'une "
        "capture, il peut sauter par-dessus une pièce adverse même en arrière "
        "(voir BEG_CH02_004)."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)

BEG_CH02_003 = BeginnerPosition(
    id="BEG_CH02_003",
    theme="regle_capture",
    title="Capture simple — le pion saute par-dessus un adversaire",
    state=GameState(
        white_men=frozenset({31}),
        black_men=frozenset({27}),
        turn="white",
    ),
    concept=(
        "Le pion blanc 31 saute par-dessus le pion noir 27 et atterrit sur "
        "la case immédiatement après, soit 22. Le pion noir est capturé."
    ),
    published_notation="31x22",
    final_move=Move(path=(31, 22), captures=(27,)),
    explanation=(
        "La capture se note avec un 'x' au lieu d'un '-'. Pour qu'un saut "
        "soit possible, il faut : (1) un pion adverse en diagonale "
        "immédiate, (2) la case juste après vide."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)

BEG_CH02_004 = BeginnerPosition(
    id="BEG_CH02_004",
    theme="regle_capture",
    title="Capture vers l'arrière — autorisée pour le pion en capture",
    state=GameState(
        white_men=frozenset({22}),
        black_men=frozenset({27}),
        turn="white",
    ),
    concept=(
        "Contrairement au déplacement simple, le pion peut capturer en "
        "arrière. Ici, le pion blanc 22 saute le noir 27 vers l'arrière et "
        "atterrit en 31."
    ),
    published_notation="22x31",
    final_move=Move(path=(22, 31), captures=(27,)),
    explanation=(
        "Cette règle est l'une des spécificités du jeu de dames international "
        "(elle n'existe pas dans toutes les variantes nationales du jeu)."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)

BEG_CH02_005 = BeginnerPosition(
    id="BEG_CH02_005",
    theme="regle_rafle",
    title="Rafle — capture multiple en chaîne",
    state=GameState(
        white_men=frozenset({31}),
        black_men=frozenset({17, 27}),
        turn="white",
    ),
    concept=(
        "Si après avoir capturé un pion, le pion qui a sauté peut en "
        "capturer un autre, il DOIT continuer. C'est la rafle."
    ),
    published_notation="31x11",
    final_move=Move(path=(31, 22, 11), captures=(17, 27)),
    explanation=(
        "Trajectoire : 31 saute 27 (atterrit en 22), puis 22 saute 17 "
        "(atterrit en 11). Deux pions capturés en un seul coup. La rafle "
        "peut changer de diagonale entre chaque saut (voir RESOLUTIONS §R001)."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)

BEG_CH02_006 = BeginnerPosition(
    id="BEG_CH02_006",
    theme="regle_prise_obligatoire",
    title="Prise obligatoire — la capture prime sur le coup simple",
    state=GameState(
        white_men=frozenset({31}),
        black_men=frozenset({27}),
        turn="white",
    ),
    concept=(
        "Si une capture est possible, elle est OBLIGATOIRE. Ici, le pion "
        "31 ne peut pas jouer 31-26 (coup simple) : il doit jouer 31x22."
    ),
    explanation=(
        "Cette règle s'applique même si la capture est désavantageuse "
        "stratégiquement. Le joueur n'a aucune liberté de refuser un saut "
        "disponible. La règle vaut quel que soit le côté qui prend (pion "
        "ou dame, blanc ou noir)."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)

BEG_CH02_007 = BeginnerPosition(
    id="BEG_CH02_007",
    theme="regle_prise_maximale",
    title="Prise maximale — la rafle la plus longue est obligatoire",
    state=GameState(
        white_men=frozenset({31, 38}),
        black_men=frozenset({23, 27, 33}),
        turn="white",
    ),
    concept=(
        "Quand plusieurs captures sont possibles, le joueur DOIT choisir "
        "celle qui prend le plus de pions adverses. Ici, 31x22 capture "
        "1 pion (27) mais 38x18 capture 2 pions (33 et 23). Le coup 38x18 "
        "est obligatoire."
    ),
    published_notation="38x18",
    final_move=Move(path=(38, 29, 18), captures=(23, 33)),
    explanation=(
        "Règle spécifique au jeu de dames international (et non au jeu "
        "anglais). Si plusieurs rafles capturent le même nombre maximum "
        "de pions, le joueur a alors le libre choix entre elles."
    ),
    source=SourceType.INVENTED,
    confidence="high",
    claude_notes=(
        "Position construite par Claude pour illustrer l'asymétrie 1 vs 2 "
        "captures. Tagué INVENTED parce que la configuration exacte n'est "
        "pas un schéma de littérature mais une construction pédagogique."
    ),
)

BEG_CH02_008 = BeginnerPosition(
    id="BEG_CH02_008",
    theme="regle_promotion",
    title="Promotion — le pion qui atteint la dernière rangée devient dame",
    state=GameState(
        white_men=frozenset({6}),
        black_men=frozenset(),
        turn="white",
    ),
    concept=(
        "Quand un pion blanc atteint la première rangée (cases 1-5), il "
        "est immédiatement promu en dame. Idem pour les noirs vers la "
        "dernière rangée (46-50). Le pion blanc 6 (sur le bord gauche) "
        "n'a qu'un seul coup légal : 6-1, qui le promeut en dame."
    ),
    explanation=(
        "La promotion se produit dès qu'un pion atteint sa rangée "
        "d'arrivée. Si la promotion survient pendant une rafle, le pion "
        "redevient une dame uniquement à la FIN de la rafle (règle FMJD "
        "stricte) — il ne peut pas continuer la rafle avec les pouvoirs "
        "de dame après promotion intermédiaire."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)

BEG_CH02_009 = BeginnerPosition(
    id="BEG_CH02_009",
    theme="regle_dame",
    title="Déplacement de la dame — glissade sur toute la diagonale",
    state=GameState(
        white_kings=frozenset({32}),
        black_men=frozenset(),
        turn="white",
    ),
    concept=(
        "Contrairement au pion, la dame se déplace sur N'IMPORTE QUEL "
        "nombre de cases en diagonale, dans n'importe quelle direction "
        "(avant ou arrière), tant que toutes les cases traversées sont "
        "libres."
    ),
    explanation=(
        "Depuis la case 32, la dame blanche peut atteindre 5, 10, 14, 16, "
        "19, 21, 23, 27, 28, 37, 41, 46, 49 (entre autres) en un seul "
        "coup. Une dame qui s'arrête peut s'arrêter sur n'importe quelle "
        "case libre de sa trajectoire."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)

BEG_CH02_010 = BeginnerPosition(
    id="BEG_CH02_010",
    theme="regle_dame",
    title="Capture par la dame — saute un pion et atterrit n'importe où après",
    state=GameState(
        white_kings=frozenset({46}),
        black_men=frozenset({23}),
        turn="white",
    ),
    concept=(
        "Pour capturer, la dame glisse sur sa diagonale, saute par-dessus "
        "un pion adverse (un seul à la fois, jamais deux d'affilée), puis "
        "atterrit sur N'IMPORTE QUELLE case libre située après lui sur la "
        "même diagonale."
    ),
    explanation=(
        "Ici la dame en 46 peut sauter le pion noir 23 et atterrir sur "
        "n'importe quelle case libre entre 19, 14, ou 5 (toutes sur la "
        "même diagonale et au-delà de 23). Si une rafle est possible, la "
        "dame doit continuer, en choisissant éventuellement son point "
        "d'atterrissage pour préparer la capture suivante."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)

BEG_CH02_011 = BeginnerPosition(
    id="BEG_CH02_011",
    theme="regle_non_soufflage",
    title="Non-soufflage — un pion capturé reste sur le plateau jusqu'à la fin de la rafle",
    state=GameState(
        white_men=frozenset({23}),
        black_men=frozenset({18, 19, 28, 29}),
        turn="white",
    ),
    concept=(
        "Les pions capturés au cours d'une rafle restent sur le plateau "
        "jusqu'à ce que la rafle soit COMPLÈTEMENT terminée. Conséquence : "
        "on ne peut pas re-sauter un pion déjà capturé, et la trajectoire "
        "peut s'en trouver bloquée."
    ),
    explanation=(
        "Cette règle, appelée règle de non-soufflage, est cruciale pour les "
        "rafles complexes. Sans elle, un pion pourrait revenir tourner "
        "autour d'une zone et tout ramasser, ce qui est impossible en "
        "réalité. Voir le « coup turc » (RESOLUTIONS §R001, BEG_CH03_005) "
        "pour un cas où un pion revisite une case VIDE déjà traversée — "
        "c'est autorisé, contrairement à la re-capture interdite."
    ),
    source=SourceType.INVENTED,
    confidence="high",
    claude_notes=(
        "Position construite par Claude pour illustrer la règle de "
        "non-soufflage. Le pion 23 peut commencer une rafle mais elle se "
        "termine quand il ne peut plus sauter de pion non-capturé."
    ),
)

BEG_CH02_012 = BeginnerPosition(
    id="BEG_CH02_012",
    theme="regle_nullite",
    title="Règle des 50 coups — issue nulle de la partie",
    state=GameState(
        white_kings=frozenset({28}),
        black_kings=frozenset({23}),
        turn="white",
    ),
    concept=(
        "Si pendant 50 coups consécutifs aucune capture ni promotion n'a "
        "lieu, la partie est déclarée nulle. Cette règle empêche les "
        "parties qui pourraient tourner indéfiniment."
    ),
    explanation=(
        "Position-type de fin de partie : deux dames qui se promènent sans "
        "pouvoir se capturer. Sans la règle des 50 coups, ce serait infini. "
        "D'autres règles de nullité existent : répétition de position "
        "(trois fois la même position avec le même joueur au trait), "
        "accord mutuel des joueurs."
    ),
    source=SourceType.GENERAL_KNOWLEDGE,
    confidence="high",
)


# ============================================================================
# Chapitre 3 — Combinaisons en 2 temps
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 1, page 6 (D1-D10).
# Notation Dubois : `aXb` désigne le départ et l'arrivée d'une rafle qui peut
# zigzaguer sur plusieurs diagonales (voir RESOLUTIONS §R001).

BEG_CH03_001 = BeginnerPosition(
    id="BEG_CH03_001",
    theme="prise_majoritaire",
    title="Dubois D1 — Le schéma CONTACT-PRISE-RAFLE",
    state=GameState(
        white_men=frozenset({26, 31, 32, 43}),
        black_men=frozenset({9, 17, 19, 38}),
        turn="white",
    ),
    concept=(
        "Premier exemple canonique de combinaison en 2 temps. Le sacrifice "
        "26-21 force le noir à prendre par sa rafle majoritaire (3 pions), "
        "libérant la rafle blanche finale qui capture les 4 noirs restants."
    ),
    published_notation="26-21 (17x28) 43x3",
    final_move=Move(path=(43, 32, 23, 14, 3), captures=(9, 19, 28, 38)),
    explanation=(
        "La rafle noire 17x28 zigzague : 17→26→37→28, captures 21, 31, 32. "
        "Elle est forcée par la règle de prise majoritaire. "
        "Puis 43x3 ramasse 38, 28, 19, 9."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p6_d01",
    crop_id="crops/page_006_d01.png",
    confidence="high",
)

BEG_CH03_002 = BeginnerPosition(
    id="BEG_CH03_002",
    theme="coup_de_mazette",
    title="Dubois D2 — Coup de mazette classique",
    state=GameState(
        white_men=frozenset({28, 32, 37}),
        black_men=frozenset({10, 17, 19}),
        turn="white",
    ),
    concept=(
        "Le coup de mazette est nommé par Dubois — combinaison en 2 temps "
        "très fréquente où un sacrifice central libère la grande diagonale."
    ),
    published_notation="28-22 (17x28) 32x5",
    final_move=Move(path=(32, 23, 14, 5), captures=(10, 19, 28)),
    explanation=(
        "Après 28-22, le noir 17 est contraint de prendre par 17x28. "
        "La rafle 32x5 (32→23→14→5) capture trois noirs sur la grande "
        "diagonale et atteint la promotion."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p6_d02",
    crop_id="crops/page_006_d02.png",
    confidence="high",
)

BEG_CH03_003 = BeginnerPosition(
    id="BEG_CH03_003",
    theme="prise_majoritaire",
    title="Dubois D3 — Choisir le bon sacrifice",
    state=GameState(
        white_men=frozenset({25, 26, 27, 33, 38, 39, 40}),
        black_men=frozenset({12, 13, 14, 16, 18, 23, 24}),
        turn="white",
    ),
    concept=(
        "Plusieurs blancs peuvent se sacrifier mais une seule combinaison "
        "fonctionne. Examiner systématiquement chaque possibilité."
    ),
    published_notation="33-29 (23x21) 26x10",
    final_move=Move(path=(26, 17, 8, 19, 10), captures=(12, 13, 14, 21)),
    explanation=(
        "33-29 force le noir 23 à prendre par 23x21 (rafle 4 pions : "
        "23→34→43→32→21, captures 27, 29, 38, 39). Rafle blanche 26x10."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p6_d03",
    crop_id="crops/page_006_d03.png",
    confidence="high",
)

BEG_CH03_004 = BeginnerPosition(
    id="BEG_CH03_004",
    theme="collage",
    title="Dubois D4 — Le collage (attaque sur 2 pions)",
    state=GameState(
        white_men=frozenset({27, 28, 33, 34, 35, 38, 43}),
        black_men=frozenset({12, 13, 14, 16, 19, 23, 24}),
        turn="white",
    ),
    concept=(
        "Quand les noirs attaquent 2 pions blancs, le mécanisme de défense "
        "par collage entre en jeu — un blanc se sacrifie pour forcer une "
        "prise majoritaire qui ouvre la rafle."
    ),
    published_notation="34-29 (23x21) 29x7",
    final_move=Move(path=(29, 20, 9, 18, 7), captures=(12, 13, 14, 24)),
    explanation=(
        "Le sacrifice 34-29 colle le pion noir 24. Prise forcée 23x21 "
        "(zigzag 23→32→21). Puis rafle 29x7 sur la grande diagonale."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p6_d04",
    crop_id="crops/page_006_d04.png",
    confidence="high",
)

BEG_CH03_005 = BeginnerPosition(
    id="BEG_CH03_005",
    theme="prise_majoritaire",
    title="Dubois D5 — Combinaison inattendue",
    state=GameState(
        white_men=frozenset({24, 25, 33, 37, 41, 42, 43}),
        black_men=frozenset({8, 9, 10, 13, 18, 19, 26, 27}),
        turn="white",
    ),
    concept=(
        "Une combinaison non évidente où la solution échappe à l'intuition "
        "immédiate. Il faut envisager toutes les prises majoritaires."
    ),
    published_notation="37-31 (27x20) 25x5",
    final_move=Move(
        path=(25, 14, 3, 12, 23, 14, 5),
        captures=(8, 9, 10, 18, 19, 20),
    ),
    explanation=(
        "Le sacrifice 37-31 déclenche une longue rafle noire "
        "(27→36→47→38→29→20, captures 24, 31, 33, 41, 42). La rafle blanche "
        "25x5 traverse tout le damier."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p6_d05",
    crop_id="crops/page_006_d05.png",
    confidence="high",
    claude_notes=(
        "Rafle 25x5 a deux trajectoires possibles aux captures identiques "
        "(cf RESOLUTIONS §R003). La trajectoire stockée passe par 14 deux "
        "fois (coup turc)."
    ),
)

BEG_CH03_006 = BeginnerPosition(
    id="BEG_CH03_006",
    theme="prise_majoritaire",
    title="Dubois D6 — Attaque de 2 pions, sans collage",
    state=GameState(
        white_men=frozenset({26, 30, 33, 34, 38, 39, 40, 41}),
        black_men=frozenset({12, 13, 14, 16, 19, 22, 24, 25}),
        turn="white",
    ),
    concept=(
        "Quand le collage n'est pas possible, examiner toutes les autres "
        "prises possibles."
    ),
    published_notation="34-29 (25x32) 29x38",
    final_move=Move(path=(29, 20, 9, 18, 27, 38), captures=(13, 14, 22, 24, 32)),
    explanation=(
        "34-29 force 25x32 (rafle 3 pions : 30, 38, 39). Puis 29x38 "
        "(5 pions sur la grande diagonale)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p6_d06",
    crop_id="crops/page_006_d06.png",
    confidence="high",
)

BEG_CH03_007 = BeginnerPosition(
    id="BEG_CH03_007",
    theme="collage",
    title="Dubois D7 — Collage classique",
    state=GameState(
        white_men=frozenset({22, 30, 32, 33, 35, 47}),
        black_men=frozenset({11, 13, 14, 17, 19, 24}),
        turn="white",
    ),
    concept=(
        "Quand le noir attaque 2 pions blancs, le collage est la défense "
        "canonique."
    ),
    published_notation="33-29 (17x37) 29x18",
    final_move=Move(path=(29, 20, 9, 18), captures=(13, 14, 24)),
    explanation=(
        "33-29 colle l'attaque noire. Prise 17x37 (rafle 17→28→37, captures "
        "22, 32). Rafle finale 29x18."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p6_d07",
    crop_id="crops/page_006_d07.png",
    confidence="high",
)

BEG_CH03_008 = BeginnerPosition(
    id="BEG_CH03_008",
    theme="prise_majoritaire",
    title="Dubois D8 — Oser donner 3 pions",
    state=GameState(
        white_men=frozenset({28, 30, 32, 33, 35, 36, 37, 38, 39}),
        black_men=frozenset({11, 12, 13, 14, 17, 19, 21, 23, 24}),
        turn="white",
    ),
    concept=(
        "Sacrifier 3 pions consécutifs ne vient pas naturellement. Il faut "
        "examiner toutes les prises majoritaires, même contre-intuitives."
    ),
    published_notation="33-29 (24x31) 36x20",
    final_move=Move(
        path=(36, 27, 16, 7, 18, 9, 20),
        captures=(11, 12, 13, 14, 21, 31),
    ),
    explanation=(
        "33-29 déclenche 24x31 (3 pions). Rafle 36x20 sur 7 cases : "
        "36→27→16→7→18→9→20, ramasse 6 pions."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p6_d08",
    crop_id="crops/page_006_d08.png",
    confidence="high",
)

BEG_CH03_009 = BeginnerPosition(
    id="BEG_CH03_009",
    theme="prise_majoritaire",
    title="Dubois D9 — Prise majoritaire déterminante",
    state=GameState(
        white_men=frozenset({30, 32, 35, 44, 48}),
        black_men=frozenset({14, 23, 25, 29, 33}),
        turn="white",
    ),
    concept=(
        "L'identification rapide de la prise majoritaire est la clé."
    ),
    published_notation="44-39 (25x43) 48x10",
    final_move=Move(path=(48, 39, 28, 19, 10), captures=(14, 23, 33, 43)),
    explanation=(
        "Sacrifice 44-39. Prise 25x43 (rafle 2 pions). Rafle blanche 48x10 "
        "(4 pions sur la grande diagonale)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p6_d09",
    crop_id="crops/page_006_d09.png",
    confidence="high",
    claude_notes=(
        "⚠️ Coquille PDF Dubois : le PDF source imprime '43-38' mais aucun "
        "blanc n'est en 43. La vraie notation est '44-39' (cf RESOLUTIONS §R002). "
        "published_notation contient la notation corrigée."
    ),
)

BEG_CH03_010 = BeginnerPosition(
    id="BEG_CH03_010",
    theme="prise_majoritaire",
    title="Dubois D10 — Solution contre-intuitive",
    state=GameState(
        white_men=frozenset({29, 31, 33, 34, 35, 36, 38, 39}),
        black_men=frozenset({12, 13, 16, 18, 20, 22, 23, 24}),
        turn="white",
    ),
    concept=(
        "Comme D8, une solution qui défie l'intuition."
    ),
    published_notation="34-30 (23x32) 30x37",
    final_move=Move(path=(30, 19, 8, 17, 28, 37), captures=(12, 13, 22, 24, 32)),
    explanation=(
        "34-30 force 23x32 (3 pions). Rafle blanche 30x37 : 30→19→8→17→28→37, "
        "ramasse 5 pions."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p6_d10",
    crop_id="crops/page_006_d10.png",
    confidence="high",
)


# ============================================================================
# Chapitre 4 — Le collage et l'envoi à dame
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitres 6 et 7
# (pages 20-25). Le collage est un deuxième sacrifice intercalé qui crée
# le point d'appui pour la rafle finale.
#
# Sélection : 1 position GENERAL_KNOWLEDGE introductive (exemple narratif
# de la page 20) + 10 positions CORPUS extraites par pipeline dilf.
#
# Note : le diagramme D5 du chapitre 6 (Dubois) a été écarté — diagramme
# faux dans le livre source (cf RESOLUTIONS §R005).

BEG_CH04_001 = BeginnerPosition(
    id="BEG_CH04_001",
    theme="collage",
    title="Exemple introductif — Le collage en 3 temps",
    state=GameState(
        white_men=frozenset({22, 25, 27, 32, 35, 36, 37, 38, 39, 48, 49}),
        black_men=frozenset({8, 9, 10, 13, 15, 16, 18, 19, 21, 26, 29}),
        turn="white",
    ),
    concept=(
        "Le collage est une combinaison en 3 temps : un premier sacrifice "
        "ouvre la position, une prise forcée du noir suit, puis un DEUXIÈME "
        "sacrifice (le collage proprement dit) crée le point d'appui à partir "
        "duquel la rafle finale peut partir."
    ),
    published_notation="37-31 (26x17) 39-34 (21x43) 34x5",
    final_move=Move(
        path=(34, 23, 12, 3, 14, 5),
        captures=(8, 9, 10, 18, 29),
    ),
    explanation=(
        "Étape 1 — 37-31 sacrifice (le blanc 37 vient en 31). "
        "Étape 2 — (26x17) prise forcée par le noir 26 (rafle 3 pions). "
        "Étape 3 — 39-34 LE COLLAGE : second sacrifice qui crée le point d'appui "
        "en 34. "
        "Étape 4 — (21x43) prise forcée du collage. "
        "Étape 5 — 34x5 rafle finale (34→23→12→3→14→5, 5 captures dont coup turc "
        "par 14). C'est cette structure CONTACT-PRISE-COLLAGE-PRISE-RAFLE qui "
        "définit le collage."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p20_intro",
    crop_id="crops/page_020_d01.png",
    confidence="high",
    claude_notes=(
        "Exemple narratif d'introduction du chapitre 6 Dubois (page 20). "
        "Sert d'ouverture pédagogique au chapitre Collage du manuel Débutant."
    ),
)

BEG_CH04_002 = BeginnerPosition(
    id="BEG_CH04_002",
    theme="prise_majoritaire",
    title="Dubois ch6 D1 — Prise majoritaire menant à un point d'appui",
    state=GameState(
        white_men=frozenset({25, 28, 29, 30, 32, 36, 37, 38, 39}),
        black_men=frozenset({8, 12, 13, 14, 15, 16, 17, 19, 22}),
        turn="white",
    ),
    concept=(
        "Une combinaison en 2 temps où la prise majoritaire force le noir "
        "vers une case où il sera repris par la rafle blanche."
    ),
    published_notation="25-20 (15x31) 36x20",
    final_move=Move(path=(36, 27, 18, 9, 20), captures=(13, 14, 22, 31)),
    explanation=(
        "25-20 sacrifice. Prise noire majoritaire (15x31) trajectoire "
        "15→24→33→42→31, captures 20, 29, 37, 38 (4 pions forcés). Rafle "
        "blanche 36x20 = 36→27→18→9→20, captures 13, 14, 22, 31."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p21_d01",
    crop_id="crops/page_021_d01.png",
    confidence="high",
    claude_notes=(
        "⚠️ Coquille PDF : Dubois imprime '(15x21)', vraie notation '(15x31)' "
        "(typo 1er chiffre 2 → 3). Cf RESOLUTIONS §R004."
    ),
)

BEG_CH04_003 = BeginnerPosition(
    id="BEG_CH04_003",
    theme="gambit",
    title="Dubois ch6 D4 — Gambit de 2 pions (sans rafle finale)",
    state=GameState(
        white_men=frozenset({22, 27, 28, 32, 35, 37, 38, 45}),
        black_men=frozenset({8, 11, 13, 16, 20, 24, 29, 30}),
        turn="white",
    ),
    concept=(
        "Une variante du collage où les blancs gagnent en sacrifiant deux "
        "pions pour atteindre une position finale supérieure. La combinaison "
        "se termine sur un coup simple, pas une rafle."
    ),
    published_notation="27-21 (16x18) 28-23",
    final_move=None,
    explanation=(
        "27-21 premier sacrifice. (16x18) prise zigzagante. Puis 28-23 — "
        "sacrifice non capture qui colle définitivement la position. "
        "Pas de rafle finale, mais gain positionnel décisif."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p21_d04",
    crop_id="crops/page_021_d04.png",
    confidence="high",
    claude_notes=(
        "Combinaison atypique : se termine par un coup simple (28-23), "
        "pas par une rafle. final_move=None."
    ),
)

BEG_CH04_004 = BeginnerPosition(
    id="BEG_CH04_004",
    theme="collage",
    title="Dubois ch6 D6 — Premier collage en 3 temps",
    state=GameState(
        white_men=frozenset({22, 26, 28, 32, 33, 34, 36, 38, 43, 48, 50}),
        black_men=frozenset({6, 8, 11, 12, 13, 14, 15, 17, 19, 21, 24}),
        turn="white",
    ),
    concept=(
        "Le collage classique en 3 temps : sacrifice initial, prise noire "
        "forcée, DEUXIÈME sacrifice (le collage proprement dit), puis la "
        "rafle finale qui exploite le point d'appui créé."
    ),
    published_notation="32-27 (21x23) 34-29 (17x39) 29x16",
    final_move=Move(path=(29, 20, 9, 18, 7, 16), captures=(11, 12, 13, 14, 24)),
    explanation=(
        "32-27 sacrifice initial. (21x23) prise forcée. 34-29 COLLAGE — c'est "
        "ce deuxième sacrifice qui fait la différence avec une combinaison en "
        "2 temps. (17x39) prise du collage. Rafle finale 29x16 sur 5 cases "
        "(29→20→9→18→7→16, 5 captures)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p21_d06",
    crop_id="crops/page_021_d06.png",
    confidence="high",
)

BEG_CH04_005 = BeginnerPosition(
    id="BEG_CH04_005",
    theme="collage",
    title="Dubois ch6 D7 — Collage avec élimination préalable",
    state=GameState(
        white_men=frozenset({26, 27, 29, 32, 34, 36, 37, 38, 40, 43, 48}),
        black_men=frozenset({11, 12, 13, 14, 15, 16, 18, 19, 20, 22, 23}),
        turn="white",
    ),
    concept=(
        "Le collage demande parfois d'éliminer un pion qui bloque la rafle "
        "finale avant de créer le point d'appui."
    ),
    published_notation="29-24 (22x33) 32-28 (19x39) 28x6",
    final_move=Move(path=(28, 19, 8, 17, 6), captures=(11, 12, 13, 23)),
    explanation=(
        "29-24 attaque. (22x33) prise. 32-28 collage. (19x39) prise du "
        "collage. Rafle 28x6 (28→19→8→17→6, captures 11, 12, 13, 23)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p21_d07",
    crop_id="crops/page_021_d07.png",
    confidence="high",
)

BEG_CH04_006 = BeginnerPosition(
    id="BEG_CH04_006",
    theme="coup_royal",
    title="Dubois ch6 D9 — Le coup royal",
    state=GameState(
        white_men=frozenset({27, 28, 32, 33, 37, 38, 39, 40, 45}),
        black_men=frozenset({6, 12, 13, 14, 18, 19, 23, 24, 26}),
        turn="white",
    ),
    concept=(
        "Le coup royal de Manoury est un classique : une rafle finale "
        "finissant à la case 7 (ou symétrique), caractérisée par une "
        "trajectoire passant par 18, 9, 7."
    ),
    published_notation="27-22 (18x27) 32x21 (23x34) 40x7",
    final_move=Move(path=(40, 29, 20, 9, 18, 7), captures=(12, 13, 14, 24, 34)),
    explanation=(
        "27-22 sacrifice. (18x27) prise. 32x21 rafle intermédiaire (2 "
        "captures). (23x34) prise. Rafle finale 40x7 = 40→29→20→9→18→7 "
        "(5 captures dont 34) — une des plus emblématiques rafles du "
        "répertoire combinatoire."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p21_d09",
    crop_id="crops/page_021_d09.png",
    confidence="high",
    claude_notes=(
        "Combinaison emblématique : le « Coup royal » est un motif tactique "
        "nommé. Voir aussi pedagogy/motifs/coup_royal.py pour le détecteur "
        "automatique dans dilf."
    ),
)

BEG_CH04_007 = BeginnerPosition(
    id="BEG_CH04_007",
    theme="envoi_a_dame",
    title="Dubois ch6 D10 — Envoi à dame + collage (Rustenburg-van Dartelen 1934)",
    state=GameState(
        white_men=frozenset({15, 28, 29, 33, 34, 37, 38, 40, 41, 43, 45}),
        black_men=frozenset({3, 4, 5, 12, 13, 14, 16, 19, 21, 26, 27}),
        turn="white",
    ),
    concept=(
        "L'association d'un envoi à dame et d'un collage permet d'amener une "
        "pièce du camp adverse à un emplacement stratégique pour la rafle "
        "finale. Position issue d'une partie historique."
    ),
    published_notation="38-32 (27x49) 34-30 (49x24) 29x7",
    final_move=None,
    explanation=(
        "38-32 sacrifice. (27x49) le noir promeut sa dame. 34-30 collage. "
        "(49x24) la nouvelle dame noire fait une rafle de dame. Puis 29x7 "
        "rafle blanche finale. C'est l'archétype de la combinaison "
        "envoi-à-dame + collage."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p21_d10",
    crop_id="crops/page_021_d10.png",
    confidence="high",
    claude_notes=(
        "⚠️ Solution contient un envoi à dame intermédiaire et une rafle de "
        "dame ((49x24)). Le module pedagogy.notation.dubois (PR #31) ne gère "
        "que les pions, donc final_move=None. Cf RESOLUTIONS §R007. "
        "Suggestion §5bis dans ameliorations_dilf : étendre aux rafles de dame."
    ),
)

BEG_CH04_008 = BeginnerPosition(
    id="BEG_CH04_008",
    theme="collage",
    title="Dubois ch7 D2 — Collage classique (attaque de 4 pions)",
    state=GameState(
        white_men=frozenset({27, 29, 31, 32, 33, 34, 35, 36, 43, 48}),
        black_men=frozenset({7, 8, 9, 13, 15, 16, 18, 19, 22, 26}),
        turn="white",
    ),
    concept=(
        "Quand les noirs attaquent plusieurs pions simultanément, le collage "
        "est la défense canonique : on accepte le sacrifice pour reprendre "
        "tout le matériel adverse."
    ),
    published_notation="29-23 (26x30) 23x1",
    final_move=Move(path=(23, 14, 3, 12, 1), captures=(7, 8, 9, 19)),
    explanation=(
        "29-23 sacrifice. (26x30) prise noire forcée. Rafle blanche 23x1 "
        "(23→14→3→12→1, 4 captures sur la grande diagonale, finit en promotion)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p24_d02",
    crop_id="crops/page_024_d02.png",
    confidence="high",
)

BEG_CH04_009 = BeginnerPosition(
    id="BEG_CH04_009",
    theme="envoi_a_dame",
    title="Dubois ch7 D5 — Triple mécanisme : majoritaire + envoi à dame + collage",
    state=GameState(
        white_men=frozenset({24, 26, 28, 32, 34, 38, 42}),
        black_men=frozenset({7, 8, 9, 13, 17, 18, 19}),
        turn="white",
    ),
    concept=(
        "Une combinaison rare avec peu de pions qui réunit trois mécanismes : "
        "prise majoritaire, envoi à dame du noir, et collage de la dame "
        "nouvellement promue."
    ),
    published_notation="28-23 (19x48) 17-12 (48x19) 12x1",
    final_move=None,
    explanation=(
        "28-23 sacrifice. (19x48) le noir promeut sa dame en 48. 17-12 "
        "collage de la dame. (48x19) la dame noire fait une rafle de dame. "
        "Puis 12x1 — rafle blanche finale."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p24_d05",
    crop_id="crops/page_024_d05.png",
    confidence="high",
    claude_notes=(
        "⚠️ Idem D10 chap 6 : contient une rafle de dame non reconstructible "
        "par le module actuel. final_move=None. Cf RESOLUTIONS §R007."
    ),
)

BEG_CH04_010 = BeginnerPosition(
    id="BEG_CH04_010",
    theme="coup_de_mazette",
    title="Dubois ch7 D8 — Coup de mazette",
    state=GameState(
        white_men=frozenset({27, 30, 32, 34, 35, 37, 43}),
        black_men=frozenset({9, 16, 17, 19, 21, 23, 24}),
        turn="white",
    ),
    concept=(
        "Le coup de mazette appliqué en mode collage : deux sacrifices "
        "successifs qui forcent l'adversaire à se mettre dans la position "
        "de rafle."
    ),
    published_notation="34-29 (23x25) 27-22 (17x28) 32x3",
    final_move=Move(path=(32, 23, 14, 3), captures=(9, 19, 28)),
    explanation=(
        "34-29 premier sacrifice. (23x25) prise. 27-22 deuxième sacrifice. "
        "(17x28) prise. Rafle finale 32x3 (32→23→14→3, 3 captures sur la "
        "grande diagonale)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p24_d08",
    crop_id="crops/page_024_d08.png",
    confidence="high",
    claude_notes=(
        "⚠️ Coquille PDF : Dubois imprime '31x3', vraie notation '32x3' "
        "(typo 2e chiffre 1 → 2). Cf RESOLUTIONS §R006."
    ),
)

BEG_CH04_011 = BeginnerPosition(
    id="BEG_CH04_011",
    theme="coup_de_mazette",
    title="Dubois ch7 D9 — Coup de mazette inversé",
    state=GameState(
        white_men=frozenset({24, 28, 29, 31, 34, 37, 39, 40, 44, 47}),
        black_men=frozenset({8, 9, 11, 12, 14, 15, 17, 18, 21, 25}),
        turn="white",
    ),
    concept=(
        "Variante symétrique du coup de mazette où la rafle finale ne va "
        "pas sur la grande diagonale 1-50 mais sur l'autre."
    ),
    published_notation="28-22 (18x36) 24-19 (14x23) 29x27",
    final_move=Move(path=(29, 18, 7, 16, 27), captures=(11, 12, 21, 23)),
    explanation=(
        "28-22 sacrifice. (18x36) prise. 24-19 deuxième sacrifice. (14x23) "
        "prise. Rafle 29x27 = 29→18→7→16→27 (4 captures)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p24_d09",
    crop_id="crops/page_024_d09.png",
    confidence="high",
)


# ============================================================================
# Chapitre 5 — L'envoi à dame
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 4, pages 14-16.
#
# L'envoi à dame consiste à promouvoir volontairement un pion (ou à laisser
# l'adversaire promouvoir un des siens) pour exploiter la position de la
# dame nouvellement créée — soit en la reprenant avec avantage, soit en
# l'utilisant comme point d'appui pour une rafle.
#
# Le chapitre Dubois mêle plusieurs types de combinaisons :
# - exemples narratifs en 3 et 5 phases (positions 1, 2)
# - exercices de prise majoritaire (D1-D7) sans envoi à dame, qui consolident
#   les acquis des chapitres précédents
# - exercices avec envoi à dame proprement dit (D8, D9, D10)
#
# 5 fixtures avec final_move=None (envois à dame, limitation R007).

BEG_CH05_001 = BeginnerPosition(
    id="BEG_CH05_001",
    theme="envoi_a_dame",
    title="Exemple narratif Dubois ch4 — Envoi à dame en 3 temps",
    state=GameState(
        white_men=frozenset({25, 30, 33, 35, 36, 38, 41, 42, 43, 44, 47, 48, 50}),
        black_men=frozenset({3, 6, 8, 9, 10, 13, 16, 18, 19, 24, 26, 27, 29}),
        turn="white",
    ),
    concept=(
        "Premier exemple narratif Dubois : on rêve d'une rafle aboutissant à "
        "5, mais il manque un noir en 39. Le mécanisme est d'envoyer un de "
        "ses pions à dame en sacrifiant, puis de reprendre la dame avec "
        "avantage pour qu'elle atterrisse en 39 où elle servira de cible "
        "pour la rafle finale."
    ),
    published_notation="36-31 (26x46) 42-37 (46x39) 43x5",
    final_move=None,
    explanation=(
        "Étape 1 — 36-31 sacrifice. Étape 2 — (26x46) le noir promeut sa "
        "dame en case 46 (dernière rangée du noir). Étape 3 — 42-37 nouveau "
        "sacrifice (la dame doit reprendre). Étape 4 — (46x39) la dame "
        "noire prend et atterrit en 39. Étape 5 — 43x5 rafle blanche qui "
        "capture la dame noire fraîchement placée."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p14_intro1",
    crop_id="crops/page_014_d01.png",
    confidence="high",
    claude_notes=(
        "Exemple narratif page 14. Contient une rafle de dame ((46x39)), "
        "non reconstructible par le module pion-only. final_move=None. "
        "Cf RESOLUTIONS §R007."
    ),
)

BEG_CH05_002 = BeginnerPosition(
    id="BEG_CH05_002",
    theme="envoi_a_dame",
    title="Exemple narratif Dubois ch4 — Combinaison en 3 phases (5 temps)",
    state=GameState(
        white_men=frozenset({30, 33, 34, 35, 37, 38, 42}),
        black_men=frozenset({9, 13, 16, 19, 23, 24, 26}),
        turn="white",
    ),
    concept=(
        "Deuxième exemple narratif Dubois en 3 phases : phase 1 d'élimination "
        "(deux sacrifices pour retirer les pions gêneurs), phase 2 d'envoi "
        "à dame (acheminement d'une pièce sur la case clé via dame), phase "
        "3 d'exécution de la rafle finale."
    ),
    published_notation="33-29 (24x33) 38x18 (13x22) 37-31 (26x48) 40-35 (48x30) 35x4",
    final_move=None,
    explanation=(
        "Phase 1 (élimination) : 33-29 (24x33) 38x18 (13x22) — deux pions "
        "noirs supprimés. "
        "Phase 2 (envoi à dame) : 37-31 (26x48) le noir promeut, "
        "40-35 (48x30) la dame est forcée vers 30. "
        "Phase 3 (rafle) : 35x4 capture finale."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p14_intro2",
    crop_id="crops/page_014_d04.png",
    confidence="high",
    claude_notes=(
        "Exemple narratif page 14, deuxième position. Combinaison en 5 "
        "demi-coups, 3 phases distinctes. Contient (48x30) rafle de dame "
        "→ final_move=None."
    ),
)

BEG_CH05_003 = BeginnerPosition(
    id="BEG_CH05_003",
    theme="coup_royal",
    title="Dubois ch4 D1 — Coup royal sous sa forme la plus simple",
    state=GameState(
        white_men=frozenset({27, 33, 38, 39, 40, 45}),
        black_men=frozenset({12, 13, 14, 19, 23, 24}),
        turn="white",
    ),
    concept=(
        "La formation noire en étoile 13-14-19-23-24 est l'origine la plus "
        "fréquente du coup royal. Ici la version la plus dépouillée du motif."
    ),
    published_notation="33-28 (23x34) 40x7",
    final_move=Move(path=(40, 29, 20, 9, 18, 7), captures=(12, 13, 14, 24, 34)),
    explanation=(
        "33-28 sacrifice. (23x34) prise majoritaire forcée (3 pions). "
        "Rafle 40x7 = 40→29→20→9→18→7 (5 captures dont 34). "
        "Forme canonique du coup royal."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p15_d01",
    crop_id="crops/page_015_d01.png",
    confidence="high",
)

BEG_CH05_004 = BeginnerPosition(
    id="BEG_CH05_004",
    theme="prise_majoritaire",
    title="Dubois ch4 D2 — Prise majoritaire surprenante (Salomé-Nimbi 2015)",
    state=GameState(
        white_men=frozenset({22, 27, 29, 33, 34, 35, 43, 48}),
        black_men=frozenset({8, 9, 11, 15, 16, 19, 20, 26}),
        turn="white",
    ),
    concept=(
        "Position issue d'une partie 2015 : la prise majoritaire peut "
        "déclencher des combinaisons inattendues. Ne jamais négliger "
        "aucune piste."
    ),
    published_notation="27-21 (26x30) 35x2",
    final_move=Move(path=(35, 24, 13, 2), captures=(8, 19, 30)),
    explanation=(
        "27-21 sacrifice. (26x30) prise majoritaire (3 pions). "
        "Rafle 35x2 = 35→24→13→2 (3 captures, atteint la promotion)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p15_d02",
    crop_id="crops/page_015_d02.png",
    confidence="high",
)

BEG_CH05_005 = BeginnerPosition(
    id="BEG_CH05_005",
    theme="prise_majoritaire",
    title="Dubois ch4 D3 — Prise majoritaire avec très longue rafle",
    state=GameState(
        white_men=frozenset({25, 26, 30, 32, 35, 37, 38, 39, 49}),
        black_men=frozenset({12, 13, 14, 17, 19, 22, 23, 24, 34}),
        turn="white",
    ),
    concept=(
        "Une combinaison où la rafle finale traverse toute la longueur du "
        "damier — 6 pions capturés en une seule rafle blanche."
    ),
    published_notation="32-27 (22x44) 49x7",
    final_move=Move(
        path=(49, 40, 29, 20, 9, 18, 7),
        captures=(12, 13, 14, 24, 34, 44),
    ),
    explanation=(
        "32-27 sacrifice. (22x44) prise noire zigzagante 22→31→42→33→44 "
        "(4 captures). Rafle finale 49x7 = 49→40→29→20→9→18→7 "
        "(6 captures dont 44)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p15_d03",
    crop_id="crops/page_015_d03.png",
    confidence="high",
)

BEG_CH05_006 = BeginnerPosition(
    id="BEG_CH05_006",
    theme="prise_majoritaire",
    title="Dubois ch4 D5 — Coup royal variante",
    state=GameState(
        white_men=frozenset({33, 37, 38, 39, 40, 41}),
        black_men=frozenset({12, 13, 14, 18, 22, 23}),
        turn="white",
    ),
    concept=(
        "Variante de la formation en étoile menant à une rafle traversant "
        "la grande diagonale."
    ),
    published_notation="33-29 (23x32) 37x10",
    final_move=Move(
        path=(37, 28, 17, 8, 19, 10),
        captures=(12, 13, 14, 22, 32),
    ),
    explanation=(
        "33-29 sacrifice. (23x32) prise majoritaire (3 pions). "
        "Rafle 37x10 = 37→28→17→8→19→10 (5 captures)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p15_d05",
    crop_id="crops/page_015_d05.png",
    confidence="high",
)

BEG_CH05_007 = BeginnerPosition(
    id="BEG_CH05_007",
    theme="prise_majoritaire",
    title="Dubois ch4 D7 — Règle de la prise majoritaire décisive",
    state=GameState(
        white_men=frozenset({27, 28, 33, 34, 37, 38, 42}),
        black_men=frozenset({12, 13, 14, 16, 18, 21, 24}),
        turn="white",
    ),
    concept=(
        "Quand la prise majoritaire force le noir vers une case qui ouvre "
        "la rafle blanche, le résultat est imparable."
    ),
    published_notation="33-29 (24x31) 37x10",
    final_move=Move(
        path=(37, 26, 17, 8, 19, 10),
        captures=(12, 13, 14, 21, 31),
    ),
    explanation=(
        "33-29 sacrifice. (24x31) prise majoritaire. "
        "Rafle 37x10 = 37→26→17→8→19→10 (5 captures)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p15_d07",
    crop_id="crops/page_015_d07.png",
    confidence="high",
)

BEG_CH05_008 = BeginnerPosition(
    id="BEG_CH05_008",
    theme="envoi_a_dame",
    title="Dubois ch4 D8 — Envoi à dame avec double sacrifice",
    state=GameState(
        white_men=frozenset({27, 28, 32, 33, 35, 37, 38, 39, 42, 47}),
        black_men=frozenset({3, 6, 12, 13, 14, 16, 18, 24, 25, 26}),
        turn="white",
    ),
    concept=(
        "La rafle 28x10 se dessine clairement mais il manque un noir en 22. "
        "Le mécanisme d'envoi à dame permet de placer la pièce noire au bon "
        "endroit."
    ),
    published_notation="37-31 (26x48) 47-42 (48x22) 28x10",
    final_move=None,
    explanation=(
        "37-31 sacrifice. (26x48) le noir promeut sa dame en 48. "
        "47-42 deuxième sacrifice (la dame est forcée d'attaquer). "
        "(48x22) la dame noire prend et atterrit en 22 — exactement où "
        "il fallait. 28x10 rafle blanche finale qui capture la dame."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p15_d08",
    crop_id="crops/page_015_d08.png",
    confidence="high",
    claude_notes=(
        "⚠️ Solution contient une rafle de dame ((48x22)). final_move=None. "
        "Cf RESOLUTIONS §R007."
    ),
)

BEG_CH05_009 = BeginnerPosition(
    id="BEG_CH05_009",
    theme="envoi_a_dame",
    title="Dubois ch4 D9 — Envoi à dame côté noir (Navarro-Roozenburg 1956)",
    state=GameState(
        white_men=frozenset({24, 28, 29, 31, 33, 35, 36, 38, 39, 40, 42, 43, 48, 49}),
        black_men=frozenset({2, 3, 5, 6, 9, 10, 11, 12, 13, 15, 17, 20, 21, 22}),
        turn="black",
    ),
    concept=(
        "Position issue d'un championnat du monde 1956. Trait aux noirs. "
        "L'idée de base : une rafle aboutissant à 45. Pour y parvenir, "
        "envoyer un blanc à dame en 4, puis le forcer en 27 où il servira "
        "de point d'appui."
    ),
    published_notation="(13-19) 24x4 (11-16) 4x27 (21x45)",
    final_move=None,
    explanation=(
        "(13-19) le noir attaque le 24. 24x4 le blanc 24 doit prendre — "
        "rafle qui finit en 4 (promotion en dame blanche). "
        "(11-16) deuxième sacrifice noir. 4x27 la dame blanche doit prendre, "
        "atterrit en 27. (21x45) rafle noire finale qui capture la dame."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p15_d09",
    crop_id="crops/page_015_d09.png",
    confidence="high",
    claude_notes=(
        "⚠️ Trait aux noirs. Combinaison où c'est le BLANC qui est envoyé "
        "à dame puis ramené (par le noir). Contient une rafle de dame "
        "(4x27). final_move=None."
    ),
)

BEG_CH05_010 = BeginnerPosition(
    id="BEG_CH05_010",
    theme="envoi_a_dame",
    title="Dubois ch4 D10 — Envoi à dame côté noir (Bakker-Ivens 1976)",
    state=GameState(
        white_men=frozenset({18, 22, 23, 28, 29, 32, 36, 37, 39, 40, 41, 42, 43, 44, 46, 48}),
        black_men=frozenset({2, 3, 4, 6, 9, 10, 11, 13, 14, 15, 16, 17, 21, 25, 26, 35}),
        turn="black",
    ),
    concept=(
        "Position issue d'un championnat NLD 1976. Comme D9, trait aux noirs "
        "avec envoi à dame du blanc. La rafle finale aboutit à 45."
    ),
    published_notation="(14-19) 23x5 (4-10) 5x8 (3x45)",
    final_move=None,
    explanation=(
        "(14-19) sacrifice noir. 23x5 le blanc prend, atterrit en 5 "
        "(promotion en dame blanche). (4-10) deuxième sacrifice noir. "
        "5x8 la dame blanche doit reprendre, atterrit en 8. (3x45) rafle "
        "noire finale qui capture la dame."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p15_d10",
    crop_id="crops/page_015_d10.png",
    confidence="high",
    claude_notes=(
        "⚠️ Trait aux noirs. Envoi à dame du blanc avec rafle finale noire. "
        "Contient une rafle de dame (5x8). final_move=None."
    ),
)


# ============================================================================
# Chapitre 6 — La méthode des points de contact
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 5, pages 17-19.
#
# La méthode des points de contact est complémentaire de la méthode "rafle
# d'abord" enseignée dans les chapitres précédents. Au lieu de chercher
# l'arrivée de la rafle finale, on identifie les cases où pions blancs et
# noirs se touchent en diagonale (points de contact), on imagine
# mentalement chaque sacrifice possible à partir de ces points, et on
# laisse les conséquences révéler la combinaison.
#
# Les deux méthodes se complètent et ne s'excluent pas : un combinateur
# expérimenté passe constamment de l'une à l'autre.

BEG_CH06_001 = BeginnerPosition(
    id="BEG_CH06_001",
    theme="points_de_contact",
    title="Exemple narratif Dubois ch5 — La méthode des points de contact",
    state=GameState(
        white_men=frozenset({29, 31, 34, 35, 36, 37, 38, 39, 43, 44, 48, 49}),
        black_men=frozenset({3, 5, 11, 12, 13, 14, 16, 18, 21, 22, 25, 28}),
        turn="white",
    ),
    concept=(
        "Au lieu de chercher la rafle finale d'abord, on identifie les points "
        "de contact entre pions adverses (ici 34-30, 29-23, 37-32, 31-27) et "
        "on imagine chaque sacrifice. L'inattendu 31-27 révèle une prise "
        "majoritaire à 4 pions qui ouvre une rafle 39x6."
    ),
    published_notation="31-27 (22x24) 34-30 (25x34) 39x6",
    final_move=Move(
        path=(39, 30, 19, 8, 17, 6),
        captures=(11, 12, 13, 24, 34),
    ),
    explanation=(
        "31-27 premier sacrifice (point de contact 31-27 exploré). (22x24) "
        "prise noire majoritaire à 4 pions, forcée. 34-30 deuxième sacrifice "
        "(collage). (25x34) prise forcée. Rafle finale 39x6 = "
        "39→30→19→8→17→6 (5 captures dont 34). "
        "Les méthodes 'rafle d'abord' et 'points de contact' sont "
        "complémentaires."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p17_intro",
    crop_id="crops/page_017_d01.png",
    confidence="high",
    claude_notes=(
        "Exemple narratif ouvrant le chapitre 5 Dubois. Illustre la méthode "
        "alternative à la méthode 'rafle d'abord'."
    ),
)

BEG_CH06_002 = BeginnerPosition(
    id="BEG_CH06_002",
    theme="coup_philippe",
    title="Dubois ch5 D1 — Le coup Philippe sous sa forme la plus simple",
    state=GameState(
        white_men=frozenset({34, 40, 45}),
        black_men=frozenset({12, 23, 25}),
        turn="white",
    ),
    concept=(
        "Le « coup Philippe » est un motif tactique classique. Forme la plus "
        "épurée : 3 pions blancs contre 3 pions noirs, sacrifice central, "
        "puis rafle finissant en 7."
    ),
    published_notation="34-30 (25x34) 40x7",
    final_move=Move(path=(40, 29, 18, 7), captures=(12, 23, 34)),
    explanation=(
        "34-30 sacrifice. (25x34) prise forcée. Rafle 40x7 = 40→29→18→7 "
        "(3 captures : 12, 23, 34). Le coup Philippe est nommé dans la "
        "littérature et fait l'objet d'un détecteur dédié dans dilf "
        "(pedagogy/motifs/coup_philippe.py éventuel)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p18_d01",
    crop_id="crops/page_018_d01.png",
    confidence="high",
)

BEG_CH06_003 = BeginnerPosition(
    id="BEG_CH06_003",
    theme="prise_majoritaire",
    title="Dubois ch5 D2 — Prise majoritaire identifiée par les points de contact",
    state=GameState(
        white_men=frozenset({27, 31, 32, 33, 35, 43, 45, 48}),
        black_men=frozenset({9, 12, 13, 16, 17, 19, 24, 29}),
        turn="white",
    ),
    concept=(
        "La méthode des points de contact mène ici à reconnaître une prise "
        "majoritaire qui ouvre une longue rafle blanche."
    ),
    published_notation="27-21 (17x39) 43x3",
    final_move=Move(
        path=(43, 34, 23, 14, 3),
        captures=(9, 19, 29, 39),
    ),
    explanation=(
        "27-21 sacrifice. (17x39) prise noire 17→28→39 (zigzag 2 pions). "
        "Rafle 43x3 = 43→34→23→14→3 (4 captures sur la grande diagonale)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p18_d02",
    crop_id="crops/page_018_d02.png",
    confidence="high",
)

BEG_CH06_004 = BeginnerPosition(
    id="BEG_CH06_004",
    theme="collage",
    title="Dubois ch5 D3 — Collage identifié par les points de contact",
    state=GameState(
        white_men=frozenset({26, 30, 31, 33, 35, 38, 39}),
        black_men=frozenset({9, 16, 17, 18, 19, 24, 25}),
        turn="white",
    ),
    concept=(
        "Application de la méthode au mécanisme de collage : le point de "
        "contact 26-21 mène à un collage propre."
    ),
    published_notation="26-21 (25x32) 21x3",
    final_move=Move(path=(21, 12, 23, 14, 3), captures=(9, 17, 18, 19)),
    explanation=(
        "26-21 sacrifice. (25x32) prise majoritaire (3 pions). Rafle "
        "blanche 21x3 = 21→12→23→14→3 (4 captures sur la diagonale, "
        "coup turc par 23)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p18_d03",
    crop_id="crops/page_018_d03.png",
    confidence="high",
)

BEG_CH06_005 = BeginnerPosition(
    id="BEG_CH06_005",
    theme="gambit",
    title="Dubois ch5 D4 — Gambit identifié par les points de contact",
    state=GameState(
        white_men=frozenset({26, 29, 33, 35, 37, 38, 39, 47}),
        black_men=frozenset({11, 13, 14, 18, 22, 25, 27, 28}),
        turn="white",
    ),
    concept=(
        "La méthode des points de contact mène à un gambit, qui se termine "
        "sur un coup simple, pas une rafle."
    ),
    published_notation="26-21 (27x16) 38-32",
    final_move=None,
    explanation=(
        "26-21 premier sacrifice. (27x16) prise. Puis 38-32 — sacrifice "
        "non capture qui colle la position. Comme les autres gambits "
        "(voir BEG_CH04_003), pas de rafle finale, mais gain positionnel "
        "décisif."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p18_d04",
    crop_id="crops/page_018_d04.png",
    confidence="high",
    claude_notes=(
        "Combinaison se terminant par un coup simple (38-32). final_move=None."
    ),
)

BEG_CH06_006 = BeginnerPosition(
    id="BEG_CH06_006",
    theme="prise_majoritaire",
    title="Dubois ch5 D5 — Rafle longue (sans commentaire dans le livre)",
    state=GameState(
        white_men=frozenset({17, 22, 32, 33, 44}),
        black_men=frozenset({7, 8, 9, 10, 20, 39}),
        turn="white",
    ),
    concept=(
        "Un exemple où la rafle finale traverse pratiquement tout le damier. "
        "Dubois ne donne pas de commentaire — la beauté du coup parle d'elle-même."
    ),
    published_notation="17-12 (7x29) 44x2",
    final_move=Move(
        path=(44, 33, 24, 15, 4, 13, 2),
        captures=(8, 9, 10, 20, 29, 39),
    ),
    explanation=(
        "17-12 sacrifice. (7x29) prise majoritaire noire forcée (3 pions). "
        "Rafle blanche 44x2 = 44→33→24→15→4→13→2 — sept cases, six pions "
        "capturés, atteint la promotion. Coup turc par les cases 4 et 13."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p18_d05",
    crop_id="crops/page_018_d05.png",
    confidence="high",
)

BEG_CH06_007 = BeginnerPosition(
    id="BEG_CH06_007",
    theme="points_de_contact",
    title="Dubois ch5 D6 — Méthode noir gagnante (Laporta-Mostovoy 1970)",
    state=GameState(
        white_men=frozenset({20, 26, 29, 31, 34, 36, 37, 38, 39, 40, 41, 43, 49, 50}),
        black_men=frozenset({4, 6, 7, 9, 11, 12, 13, 14, 17, 22, 23, 25, 27, 28}),
        turn="black",
    ),
    concept=(
        "Partie historique 1970 : trait aux noirs qui gagnent par la méthode "
        "des points de contact. Le sacrifice (17-21) ouvre la rafle finale (4x35)."
    ),
    published_notation="(17-21) 26x10 (4x35)",
    final_move=Move(
        path=(4, 15, 24, 33, 44, 35),
        captures=(10, 20, 29, 39, 40),
    ),
    explanation=(
        "(17-21) sacrifice noir. 26x10 le blanc 26 prend (rafle 3 pions : "
        "21, 16, 7). (4x35) rafle finale noire = 4→15→24→33→44→35 "
        "(5 captures sur la grande diagonale)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p18_d06",
    crop_id="crops/page_018_d06.png",
    confidence="high",
    claude_notes=(
        "⚠️ Trait aux noirs. Partie historique Laporta-Mostovoy (Priva "
        "Ereklasse, 15-10-1970)."
    ),
)

BEG_CH06_008 = BeginnerPosition(
    id="BEG_CH06_008",
    theme="points_de_contact",
    title="Dubois ch5 D7 — 4 points de contact à analyser",
    state=GameState(
        white_men=frozenset({27, 31, 32, 33, 35, 36, 38, 40, 45}),
        black_men=frozenset({16, 17, 18, 19, 22, 23, 24, 29, 34}),
        turn="white",
    ),
    concept=(
        "Dubois identifie 4 points de contact (27-21, 32-28, 33-28, 35-30). "
        "L'exploration systématique de chacun mène à la solution : 35-30 "
        "déclenche une combinaison à 5 demi-coups."
    ),
    published_notation="35-30 (24x44) 33x13 (18x9) 27x49",
    final_move=Move(
        path=(27, 18, 29, 40, 49),
        captures=(22, 23, 34, 44),
    ),
    explanation=(
        "35-30 sacrifice. (24x44) prise majoritaire noire (zigzag à 4 cases). "
        "33x13 rafle blanche intermédiaire (3 captures). (18x9) prise noire. "
        "27x49 rafle finale = 27→18→29→40→49 (4 captures dont 44 — coup "
        "tactique très complexe à 5 demi-coups)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p18_d07",
    crop_id="crops/page_018_d07.png",
    confidence="high",
)

BEG_CH06_009 = BeginnerPosition(
    id="BEG_CH06_009",
    theme="points_de_contact",
    title="Dubois ch5 D8 — 5 points de contact (Bergsma-de Vries 1961)",
    state=GameState(
        white_men=frozenset({28, 32, 33, 34, 35, 36, 38, 39, 40, 42, 43, 44, 45, 47, 48}),
        black_men=frozenset({3, 5, 6, 7, 8, 9, 12, 13, 14, 15, 19, 21, 23, 24, 25}),
        turn="white",
    ),
    concept=(
        "Partie historique 1961 : Dubois recense 5 points de contact "
        "(35-30, 32-27, 33-29, 34-29, 34-30). Le sacrifice 33-29 (offrir "
        "2 pions) révèle une rafle aboutissant en 16."
    ),
    published_notation="33-29 (24x22) 34-30 (25x34) 40x16",
    final_move=Move(
        path=(40, 29, 18, 27, 16),
        captures=(21, 22, 23, 34),
    ),
    explanation=(
        "33-29 sacrifice de 2 pions. (24x22) prise. 34-30 deuxième sacrifice. "
        "(25x34) prise. Rafle 40x16 = 40→29→18→27→16 (4 captures)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p18_d08",
    crop_id="crops/page_018_d08.png",
    confidence="high",
    claude_notes=(
        "Partie historique Bergsma-de Vries (DC Leeuwarden - Workum, "
        "14-11-1961)."
    ),
)

BEG_CH06_010 = BeginnerPosition(
    id="BEG_CH06_010",
    theme="points_de_contact",
    title="Dubois ch5 D9 — Rafle 'cachée' révélée par les points de contact (Leclercq-Weiss 1903)",
    state=GameState(
        white_men=frozenset({18, 23, 28, 33, 34, 36, 37, 38, 39}),
        black_men=frozenset({1, 3, 11, 14, 15, 17, 19, 21, 26}),
        turn="black",
    ),
    concept=(
        "Partie historique 1903. Trait aux noirs. La rafle (1x41) semble "
        "vouée à l'échec à cause du pion 36, mais les points de contact "
        "révèlent qu'un coup intermédiaire (26-31) 36x7 fait disparaître "
        "le pion 36 et ouvre la rafle."
    ),
    published_notation="(14-20) 23x25 (26-31) 36x7 (1x41)",
    final_move=Move(
        path=(1, 12, 23, 32, 41),
        captures=(7, 18, 28, 37),
    ),
    explanation=(
        "(14-20) sacrifice noir. 23x25 le blanc 23 prend. (26-31) deuxième "
        "sacrifice noir au point de contact 26-31. 36x7 le blanc DOIT "
        "prendre (prise obligatoire), capturant 31 puis 22 puis 13. (1x41) "
        "rafle noire finale = 1→12→23→32→41 (4 captures : 7, 18, 28, 37)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p18_d09",
    crop_id="crops/page_018_d09.png",
    confidence="high",
    claude_notes=(
        "⚠️ Trait aux noirs. Partie historique Leclercq-Weiss (Damier "
        "Parisien div1, 12-03-1903). Exemple emblématique de la méthode "
        "des points de contact appliquée à une rafle 'cachée'."
    ),
)

BEG_CH06_011 = BeginnerPosition(
    id="BEG_CH06_011",
    theme="points_de_contact",
    title="Dubois ch5 D10 — Point d'appui alternatif",
    state=GameState(
        white_men=frozenset({23, 24, 28, 29, 34, 36, 39, 42, 44}),
        black_men=frozenset({11, 12, 13, 14, 15, 17, 21, 22, 35}),
        turn="white",
    ),
    concept=(
        "On s'attend à une rafle 36x20, mais l'analyse des points de contact "
        "révèle un autre point d'appui en 29, conduisant à une rafle 29x9 "
        "plus longue."
    ),
    published_notation="23-19 (14x32) 44-40 (35x33) 29x9",
    final_move=Move(
        path=(29, 38, 27, 16, 7, 18, 9),
        captures=(11, 12, 13, 21, 32, 33),
    ),
    explanation=(
        "23-19 sacrifice. (14x32) prise majoritaire noire. 44-40 collage. "
        "(35x33) prise. Rafle 29x9 = 29→38→27→16→7→18→9 (6 captures, "
        "trajectoire impressionnante avec coup turc par 18)."
    ),
    source=SourceType.CORPUS,
    source_ref="dubois_apprent_combin_p18_d10",
    crop_id="crops/page_018_d10.png",
    confidence="high",
)


# ============================================================================
# Chapitre 7 — Les temps de repos créés par une attaque
# Source : Dubois Apprentissage Combinaisons, chapitre 8, pages 26-28.
#
# Un « temps de repos » est l'opportunité, pour un joueur, de jouer un coup
# supplémentaire sans que l'adversaire puisse répliquer librement — parce
# que ce dernier est obligé de capturer (prise obligatoire). Ces temps de
# repos sont créés par une attaque préalable : l'adversaire a placé une
# menace que je suis forcé de neutraliser, mais en le faisant je crée la
# combinaison.

BEG_CH07_001 = BeginnerPosition(
    id="BEG_CH07_001",
    theme="temps_de_repos",
    title='Exemple narratif Dubois ch8 — Combinaison en 3 temps de repos',
    state=GameState(
        white_men=frozenset({32, 35, 38, 40, 42, 43, 45, 27, 28, 30}),
        black_men=frozenset({3, 8, 13, 15, 16, 17, 18, 19, 24, 25}),
        turn="white",
    ),
    concept="Le pion noir 25 menace le pion blanc 30 (attaque noire). Les blancs disposent d'un temps de repos : ils peuvent jouer un coup utile car le noir devra obligatoirement capturer ensuite. Cette obligation se chaîne trois fois dans la combinaison.",
    published_notation='42-37 (25x34) 40x20 (15x24) 28-22 (17x28) 32x14',
    final_move=Move(
        path=(32, 23, 14),
        captures=(19, 28),
    ),
    explanation="42-37 (silencieux). (25x34) noir capture forcé. 40x20 rafle 3 pions. (15x24) prise majoritaire noire. 28-22 attaque. (17x28) capture forcée. 32x14 rafle finale = 32→23→14 (2 pions). Chaque coup blanc bénéficie d'un temps de repos.",
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p26_intro1',
    crop_id='crops/page_026_d01.png',
    confidence="high",
    claude_notes='Exemple narratif ouvrant le chapitre 8 Dubois.',
)

BEG_CH07_002 = BeginnerPosition(
    id="BEG_CH07_002",
    theme="temps_de_repos",
    title='Exemple narratif Dubois ch8 — Combinaison en 3 phases (envoi à dame)',
    state=GameState(
        white_men=frozenset({48, 35, 23, 39, 42, 27, 29}),
        black_men=frozenset({19, 6, 8, 25, 26, 12, 14}),
        turn="white",
    ),
    concept='Combinaison longue exploitant les temps de repos (envoi à dame). ⚠️ La published_notation présente des incohérences de déroulé (cf claude_notes) — solution à vérifier au moteur. La position de départ est correcte : le pion noir 19 menace le pion blanc 23.',
    published_notation='42-37 (19x28) 29-23 (28x19) 37-31 (26x37) 48-42 (37x48) 39-34 (48x30) 35x2',
    final_move=None,
    explanation='⚠️ Solution publiée incohérente, en attente de vérification moteur (A_VERIFIER_MOTEUR.md §1). Problèmes relevés : (a) on ne peut pas "placer un pion en 19" car un pion noir y est déjà au départ ; (b) le sacrifice 39-34 censé réaliser l\'envoi à dame en 30 est impossible si le pion blanc 39 a déjà été capturé en amont ; (c) la rafle finale 35x2 suppose des pièces qui ont déjà quitté le plateau. La position de départ (W{23,27,29,35,39,42,48} B{6,8,12,14,19,25,26}, trait blancs) reste valide.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p26_intro2',
    crop_id='crops/page_026_d04.png',
    confidence="low",
    claude_notes='⚠️ SOLUTION SUSPECTE — published_notation probablement corrompue (transcription PDF ou coquille Dubois). Le déroulé ne tient pas : envoi à dame impossible (pion 39 capturé avant son sacrifice 39-34), rafle finale 35x2 incohérente (pièces absentes au moment voulu). NON corrigé par Claude (§4.7 : ne pas inventer de variante). À élucider au moteur Scan — cf A_VERIFIER_MOTEUR.md §1. final_move=None.',
)

BEG_CH07_003 = BeginnerPosition(
    id="BEG_CH07_003",
    theme="temps_de_repos",
    title='Dubois ch8 D1 — Trait aux noirs, attaque libère case 38',
    state=GameState(
        white_men=frozenset({32, 37, 39, 43, 48, 24, 25, 29}),
        black_men=frozenset({4, 8, 9, 13, 14, 16, 17, 28}),
        turn="black",
    ),
    concept="Trait aux noirs. L'attaque 14-20 sur le pion blanc 25 ouvre un coup de dame à 49.",
    published_notation='(14-20) 25x21 (16x49)',
    final_move=Move(
        path=(16, 27, 38, 49),
        captures=(21, 32, 43),
    ),
    explanation='(14-20) sacrifice noir : attaque le pion blanc 25. 25x21 le blanc DOIT prendre (prise majoritaire). (16x49) rafle noire finale = 16→27→38→49 (3 captures, promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p27_d01',
    crop_id='crops/page_027_d01.png',
    confidence="high",
)

BEG_CH07_004 = BeginnerPosition(
    id="BEG_CH07_004",
    theme="temps_de_repos",
    title='Dubois ch8 D2 — Collage et temps de repos (de Waard-Tjon A Ong 2013)',
    state=GameState(
        white_men=frozenset({32, 33, 35, 38, 40, 42, 43, 45, 25, 27, 28, 30, 31}),
        black_men=frozenset({3, 4, 8, 9, 13, 14, 16, 17, 18, 19, 24, 26, 29}),
        turn="white",
    ),
    concept="Partie historique 2013. L'attaque noire sur 3 pions laisse supposer un collage. La combinaison gagne 1 pion net.",
    published_notation='27-21 (26x39) 21x43',
    final_move=Move(
        path=(21, 12, 23, 34, 43),
        captures=(17, 18, 29, 39),
    ),
    explanation='27-21 sacrifice. (26x39) prise majoritaire noire. Rafle blanche 21x43 = 21→12→23→34→43 (4 captures : 17, 18, 29, 39). Bilan : +1 pion.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p27_d02',
    crop_id='crops/page_027_d02.png',
    confidence="high",
    claude_notes='Partie de Waard-Tjon A Ong (UTR-ch Hoofdklasse, 20-03-2013).',
)

BEG_CH07_005 = BeginnerPosition(
    id="BEG_CH07_005",
    theme="gambit",
    title='Dubois ch8 D3 — Gambit utilisant un temps de repos',
    state=GameState(
        white_men=frozenset({35, 36, 42, 27, 44, 29, 30}),
        black_men=frozenset({16, 17, 18, 19, 9, 28, 15}),
        turn="white",
    ),
    concept='Pas de combinaison rafle, mais un gambit gagnant — deux sacrifices successifs qui collent la position.',
    published_notation='27-22 (18x27) 29-23',
    final_move=None,
    explanation='27-22 premier sacrifice. (18x27) prise. Puis 29-23 — gambit qui colle. Pas de rafle finale, gain positionnel.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p27_d03',
    crop_id='crops/page_027_d03.png',
    confidence="high",
    claude_notes='Gambit : se termine par coup simple. final_move=None.',
)

BEG_CH07_006 = BeginnerPosition(
    id="BEG_CH07_006",
    theme="temps_de_repos",
    title='Dubois ch8 D4 — Coup de dame à 1',
    state=GameState(
        white_men=frozenset({32, 33, 35, 37, 38, 40, 43, 45, 48, 24, 27, 28}),
        black_men=frozenset({3, 7, 8, 9, 13, 15, 16, 17, 18, 20, 21, 26}),
        turn="white",
    ),
    concept='Un coup de dame sur la case 1 est vraisemblable — le mécanisme exploite les temps de repos pour ouvrir la voie.',
    published_notation='28-22 (17x39) 43x34 (20x29) 34x1',
    final_move=Move(
        path=(34, 23, 12, 1),
        captures=(7, 18, 29),
    ),
    explanation='28-22 sacrifice. (17x39) prise. 43x34 rafle intermédiaire (1 capture). (20x29) prise. Rafle finale 34x1 = 34→23→12→1 (3 captures, promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p27_d04',
    crop_id='crops/page_027_d04.png',
    confidence="high",
)

BEG_CH07_007 = BeginnerPosition(
    id="BEG_CH07_007",
    theme="temps_de_repos",
    title="Dubois ch8 D5 — Attaque et point d'appui mobile",
    state=GameState(
        white_men=frozenset({32, 34, 35, 26, 27, 28, 31}),
        black_men=frozenset({16, 17, 19, 23, 25, 11, 29}),
        turn="white",
    ),
    concept="Le pion blanc 34 devient un point d'appui mobile grâce à 2 prises majoritaires successives forcées.",
    published_notation='26-21 (17x37) 32x41 (23x21) 34x14',
    final_move=Move(
        path=(34, 23, 14),
        captures=(19, 29),
    ),
    explanation='26-21 sacrifice. (17x37) prise majoritaire noire. 32x41 rafle blanche. (23x21) prise majoritaire noire. Rafle finale 34x14 = 34→23→14 (2 captures).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p27_d05',
    crop_id='crops/page_027_d05.png',
    confidence="high",
)

BEG_CH07_008 = BeginnerPosition(
    id="BEG_CH07_008",
    theme="temps_de_repos",
    title='Dubois ch8 D6 — Coup de dame à 46 (Janssen-van Aalten 1995)',
    state=GameState(
        white_men=frozenset({23, 28, 29, 31, 32, 33, 34, 36, 38, 39, 41, 43, 44, 45, 47, 48, 49}),
        black_men=frozenset({1, 2, 4, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17, 20, 21, 25, 27, 30}),
        turn="black",
    ),
    concept="Partie historique 1995. Trait aux noirs. Idée d'un coup de dame à 46. Plan : éliminer le 28 et acheminer un pion en 13.",
    published_notation='(17-22) 28x26 (13-18) 31x13 (8x46)',
    final_move=Move(
        path=(8, 19, 28, 37, 46),
        captures=(13, 23, 32, 41),
    ),
    explanation='(17-22) sacrifice noir pour éliminer le 28. 28x26 le blanc prend forcé. (13-18) deuxième sacrifice noir. 31x13 le blanc prend forcé. (8x46) rafle noire finale = 8→19→28→37→46 (4 captures, promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p27_d06',
    crop_id='crops/page_027_d06.png',
    confidence="high",
    claude_notes='Partie Janssen-van Aalten (Huissen oc, 21-09-1995). Trait aux noirs.',
)

BEG_CH07_009 = BeginnerPosition(
    id="BEG_CH07_009",
    theme="envoi_a_dame",
    title='Dubois ch8 D7 — Envoi à dame noire et reprise (Carli-van Outheusden 1988)',
    state=GameState(
        white_men=frozenset({32, 33, 34, 41, 43, 25, 27, 28, 29, 31}),
        black_men=frozenset({2, 8, 9, 10, 13, 14, 16, 18, 19, 26}),
        turn="white",
    ),
    concept='Partie historique 1988. Mécanisme combiné : prise majoritaire + envoi à dame noire + reprise.',
    published_notation='28-23 (26x48) 23x3 (48x30) 25x34',
    final_move=None,
    explanation='28-23 sacrifice. (26x48) le noir promeut sa dame. 23x3 rafle blanche (avec promotion). (48x30) la dame noire rafle. 25x34 rafle finale blanche.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p27_d07',
    crop_id='crops/page_027_d07.png',
    confidence="high",
    claude_notes='⚠️ Contient une rafle de dame ((48x30)). final_move=None. Partie Carli-van Outheusden (Brunssum, 12-08-1988).',
)

BEG_CH07_010 = BeginnerPosition(
    id="BEG_CH07_010",
    theme="temps_de_repos",
    title='Dubois ch8 D8 — Coup de dame à 1',
    state=GameState(
        white_men=frozenset({33, 35, 36, 38, 39, 40, 42, 43, 45, 22, 26, 27, 29}),
        black_men=frozenset({3, 6, 7, 8, 9, 10, 11, 13, 15, 17, 18, 20, 25}),
        turn="white",
    ),
    concept='Un coup de dame à 1 ou 5 semble prévisible. Le temps de repos créé par les sacrifices ouvre la voie.',
    published_notation='39-34 (17x37) 29-24 (20x29) 34x1',
    final_move=Move(
        path=(34, 23, 12, 1),
        captures=(7, 18, 29),
    ),
    explanation='39-34 sacrifice. (17x37) prise. 29-24 collage. (20x29) prise. Rafle finale 34x1 = 34→23→12→1 (3 captures, promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p27_d08',
    crop_id='crops/page_027_d08.png',
    confidence="high",
)

BEG_CH07_011 = BeginnerPosition(
    id="BEG_CH07_011",
    theme="temps_de_repos",
    title='Dubois ch8 D9 — Collage noir (Veresjagin-Balajan 1965)',
    state=GameState(
        white_men=frozenset({22, 27, 28, 30, 32, 33, 35, 37, 38, 39, 44, 45, 46, 47, 48, 49}),
        black_men=frozenset({1, 2, 3, 4, 5, 6, 8, 9, 11, 13, 14, 19, 21, 23, 24, 26}),
        turn="black",
    ),
    concept="Partie URSS 1965. Trait aux noirs. L'attaque noire sur 2 pions laisse supposer un collage gagnant.",
    published_notation='(13-18) 27x7 (18x27) 32x21 (23x25)',
    final_move=Move(
        path=(23, 32, 43, 34, 25),
        captures=(28, 30, 38, 39),
    ),
    explanation='(13-18) sacrifice noir. 27x7 le blanc DOIT prendre (rafle 2 pions). (18x27) prise noire. 32x21 rafle blanche. (23x25) rafle finale noire = 23→32→43→34→25 (4 captures).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p27_d09',
    crop_id='crops/page_027_d09.png',
    confidence="high",
    claude_notes='Partie Veresjagin-Balajan (URS-ch sf Kalinigrad, sept 1965). Trait aux noirs.',
)

BEG_CH07_012 = BeginnerPosition(
    id="BEG_CH07_012",
    theme="temps_de_repos",
    title='Dubois ch8 D10 — Coups parallèles (formation 33-38-42-43)',
    state=GameState(
        white_men=frozenset({32, 33, 35, 38, 42, 43, 26, 28, 30}),
        black_men=frozenset({7, 12, 13, 14, 17, 19, 21, 22, 24}),
        turn="white",
    ),
    concept='La formation blanche 33-38-42-43 est propice aux coups parallèles. Après les sacrifices, le noir est en zugzwang : toutes ses captures forcées mènent à la même rafle gagnante.',
    published_notation='32-27 (21x23) 33-28 (ad lib) 38x29',
    final_move=Move(
        path=(38, 29, 18, 9, 20, 29),
        captures=(13, 14, 23, 24, 33),
    ),
    explanation='32-27 sacrifice. (21x23) prise. 33-28 deuxième sacrifice. (ad lib) le noir est forcé : (22x33) ou (23x32), deux captures obligatoires. 38x29 rafle finale = 38→29→18→9→20→29 (5 captures, trajectoire coup turc).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p27_d10',
    crop_id='crops/page_027_d10.png',
    confidence="high",
    claude_notes='Notation (ad lib) — le noir a 2 captures obligatoires équivalentes (cf RESOLUTIONS §R008). Branche stockée : (22x33).',
)


# ============================================================================
# Chapitre 8 — La création des temps de repos
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 9, pages 29-31.
#
# Quand l'adversaire n'attaque rien, on peut quand même CRÉER un temps de
# repos en sacrifiant un pion qui force une capture forcée adverse. Cette
# technique étend le champ des combinaisons à des positions silencieuses.

BEG_CH08_001 = BeginnerPosition(
    id="BEG_CH08_001",
    theme="creation_temps_de_repos",
    title='Exemple narratif Dubois ch9 — Créer un temps de repos en 2 sacrifices',
    state=GameState(
        white_men=frozenset({32, 35, 36, 37, 38, 39, 25, 27}),
        black_men=frozenset({9, 16, 18, 19, 21, 23, 24, 26}),
        turn="white",
    ),
    concept='On peut créer un temps de repos même sans attaque adverse, en sacrifiant pour forcer la reprise. Ici, deux sacrifices successifs (37-31 puis 38-33) créent les temps de repos nécessaires.',
    published_notation='37-31 (26x28) 38-33 (21x32) 33x4',
    final_move=Move(
        path=(33, 22, 13, 4),
        captures=(9, 18, 28),
    ),
    explanation='37-31 sacrifice volontaire. (26x28) prise majoritaire forcée. 38-33 deuxième sacrifice. (21x32) prise obligatoire. 33x4 rafle finale = 33→...→4 (4 captures, promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p29_intro1',
    crop_id='crops/page_029_d01.png',
    confidence="high",
    claude_notes='Exemple narratif ouvrant le chap 9 Dubois.',
)

BEG_CH08_002 = BeginnerPosition(
    id="BEG_CH08_002",
    theme="creation_temps_de_repos",
    title='Exemple narratif Dubois ch9 — Méthode en 3 phases',
    state=GameState(
        white_men=frozenset({32, 33, 34, 35, 38, 39, 41, 43, 22, 27}),
        black_men=frozenset({12, 13, 14, 15, 16, 18, 19, 23, 24, 26}),
        turn="white",
    ),
    concept='Méthode systématique : phase 1 créer un temps de repos, phase 2 en profiter, phase 3 dérouler les prises.',
    published_notation='32-28 (23x21) 34-29 (18x27) 29x7',
    final_move=Move(
        path=(29, 20, 9, 18, 7),
        captures=(12, 13, 14, 24),
    ),
    explanation='Phase 1 : 32-28 (23x21) — créer le temps de repos. Phase 2 : 34-29 — exploiter la prise forcée du noir. Phase 3 : (18x27) 29x7 — dérouler la rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p29_intro2',
    crop_id='crops/page_029_d04.png',
    confidence="high",
    claude_notes='Exemple narratif numéro 2 du chap 9 Dubois.',
)

BEG_CH08_003 = BeginnerPosition(
    id="BEG_CH08_003",
    theme="creation_temps_de_repos",
    title='Dubois ch9 D1 — Une seule rafle possible (Linssen-Bandstra 1982)',
    state=GameState(
        white_men=frozenset({32, 33, 35, 38, 42, 43, 45, 27, 28, 30}),
        black_men=frozenset({3, 11, 12, 13, 15, 16, 18, 19, 24, 25}),
        turn="white",
    ),
    concept='Partie historique 1982. Une seule rafle 30x6 fonctionne — ne pas hésiter à faire sauter le pion noir 19 par 28-23.',
    published_notation='28-23 (19x28) 30x6',
    final_move=Move(
        path=(30, 19, 8, 17, 6),
        captures=(11, 12, 13, 24),
    ),
    explanation='28-23 sacrifice forcé. (19x28) prise. Rafle 30x6 = trajectoire vers 6 (4-5 captures, promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p30_d01',
    crop_id='crops/page_030_d01.png',
    confidence="high",
    claude_notes='Partie Linssen-Bandstra (NLD-chT Hoofdklasse, 02-10-1982).',
)

BEG_CH08_004 = BeginnerPosition(
    id="BEG_CH08_004",
    theme="prise_majoritaire",
    title='Dubois ch9 D2 — Prise majoritaire ouvre la voie',
    state=GameState(
        white_men=frozenset({32, 33, 39, 40, 42, 27, 28, 31}),
        black_men=frozenset({35, 13, 14, 16, 17, 19, 23, 24}),
        turn="white",
    ),
    concept='Une combinaison basée sur le mécanisme de la prise majoritaire qui crée naturellement un temps de repos.',
    published_notation='33-29 (35x22) 29x29',
    final_move=Move(
        path=(29, 18, 9, 20, 29),
        captures=(13, 14, 23, 24),
    ),
    explanation='33-29 sacrifice. (35x22) prise majoritaire noire (zigzag long). Rafle 29x29 — la rafle revient sur sa case de départ (coup turc).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p30_d02',
    crop_id='crops/page_030_d02.png',
    confidence="high",
    claude_notes='Rafle revenant sur sa case de départ (29x29).',
)

BEG_CH08_005 = BeginnerPosition(
    id="BEG_CH08_005",
    theme="creation_temps_de_repos",
    title='Dubois ch9 D3 — Exploitation mignonne (Loenen-Hengefeld 1990)',
    state=GameState(
        white_men=frozenset({32, 33, 34, 39, 44, 28, 30, 31}),
        black_men=frozenset({35, 6, 7, 8, 14, 19, 23, 24}),
        turn="white",
    ),
    concept='Partie historique 1990. « Une mignonne exploitation des temps de repos » selon Dubois.',
    published_notation='33-29 (24x22) 32-27 (35x24) 27x9',
    final_move=Move(
        path=(27, 18, 29, 20, 9),
        captures=(14, 22, 23, 24),
    ),
    explanation='33-29 sacrifice. (24x22) prise. 32-27 deuxième sacrifice (création du 2e temps de repos). (35x24) prise majoritaire. 27x9 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p30_d03',
    crop_id='crops/page_030_d03.png',
    confidence="high",
    claude_notes='Partie Loenen-Hengefeld (Brunssum, 11-08-1990).',
)

BEG_CH08_006 = BeginnerPosition(
    id="BEG_CH08_006",
    theme="creation_temps_de_repos",
    title='Dubois ch9 D4 — Rafle rare 24x11 (Badal-Kemperman 1994)',
    state=GameState(
        white_men=frozenset({32, 36, 37, 38, 40, 45, 48, 25, 27, 28}),
        black_men=frozenset({6, 12, 13, 14, 15, 16, 23, 24, 26, 29}),
        turn="black",
    ),
    concept='Partie historique 1994. Trait aux noirs. La rafle 24x11 est très rare et inattendue. Démontre la valeur de la recherche systématique.',
    published_notation='(15-20) 28x17 (29-34) 40x29 (24x11)',
    final_move=Move(
        path=(24, 33, 42, 31, 22, 11),
        captures=(17, 27, 29, 37, 38),
    ),
    explanation='(15-20) sacrifice noir. 28x17 prise forcée. (29-34) deuxième sacrifice. 40x29 prise. (24x11) rafle noire rare finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p30_d04',
    crop_id='crops/page_030_d04.png',
    confidence="high",
    claude_notes="Trait aux noirs. Partie Badal-Kemperman (NLD-chJ, 13-07-1994). Illustre l'intérêt de la recherche systématique.",
)

BEG_CH08_007 = BeginnerPosition(
    id="BEG_CH08_007",
    theme="creation_temps_de_repos",
    title='Dubois ch9 D5 — Élimination ciblée (Schippers-Barten 2012)',
    state=GameState(
        white_men=frozenset({33, 34, 36, 39, 41, 42, 43, 45, 46, 48, 49, 24, 27, 29, 31}),
        black_men=frozenset({1, 2, 3, 7, 8, 10, 11, 13, 16, 17, 18, 19, 22, 23, 28}),
        turn="white",
    ),
    concept="Partie 2012. Beaucoup de trous dans le camp noir, peu de points d'appui blancs (41 et 43). En éliminant le pion 23 et en amenant un pion en 37, la rafle 41x5 s'impose.",
    published_notation='34-30 (23x25) 27-21 (17x37) 41x5',
    final_move=Move(
        path=(41, 32, 23, 14, 5),
        captures=(10, 19, 28, 37),
    ),
    explanation='34-30 sacrifice. (23x25) prise. 27-21 deuxième sacrifice. (17x37) prise. Rafle 41x5 (promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p30_d05',
    crop_id='crops/page_030_d05.png',
    confidence="high",
    claude_notes='Partie Schippers-Barten (NLD-chT 2e klasse E, 14-01-2012).',
)

BEG_CH08_008 = BeginnerPosition(
    id="BEG_CH08_008",
    theme="creation_temps_de_repos",
    title='Dubois ch9 D6 — Combinaison compliquée (van Leeuwen-de Jong 1968)',
    state=GameState(
        white_men=frozenset({32, 33, 34, 35, 36, 42, 43, 46, 49, 22, 26, 28, 30}),
        black_men=frozenset({1, 2, 3, 4, 5, 7, 8, 13, 19, 20, 21, 23, 25}),
        turn="black",
    ),
    concept='Partie 1968. Trait aux noirs. La rafle a comme point de départ la case 7. Seul le pion blanc 34 peut être acheminé sur cette case.',
    published_notation='(3-9) 26x17 (23-29) 34x12 (7x47)',
    final_move=Move(
        path=(7, 18, 27, 38, 47),
        captures=(12, 22, 32, 42),
    ),
    explanation='(3-9) sacrifice noir. 26x17 prise forcée. (23-29) deuxième sacrifice. 34x12 prise forcée. (7x47) rafle noire finale (promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p30_d06',
    crop_id='crops/page_030_d06.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie van Leeuwen-de Jong (NLD-ch sf Groep 2, 28-12-1968).',
)

BEG_CH08_009 = BeginnerPosition(
    id="BEG_CH08_009",
    theme="creation_temps_de_repos",
    title='Dubois ch9 D7 — Offre 22-17 crée un temps de repos',
    state=GameState(
        white_men=frozenset({33, 34, 35, 47, 21, 22, 27, 28}),
        black_men=frozenset({4, 11, 12, 13, 14, 16, 19, 24}),
        turn="white",
    ),
    concept="Beaucoup de trous dans le camp noir. L'offre 22-17 fournit aux blancs un temps de repos qu'ils peuvent utiliser pour la rafle finale.",
    published_notation='22-17 (11x31) 34-29 (16x27) 29x7',
    final_move=Move(
        path=(29, 20, 9, 18, 7),
        captures=(12, 13, 14, 24),
    ),
    explanation='22-17 sacrifice. (11x31) prise. 34-29 deuxième sacrifice. (16x27) prise. Rafle finale 29x7.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p30_d07',
    crop_id='crops/page_030_d07.png',
    confidence="high",
)

BEG_CH08_010 = BeginnerPosition(
    id="BEG_CH08_010",
    theme="creation_temps_de_repos",
    title='Dubois ch9 D8 — Offre classique de 3 pions',
    state=GameState(
        white_men=frozenset({32, 35, 36, 38, 39, 43, 44, 45, 48, 25, 26, 27, 31}),
        black_men=frozenset({2, 6, 8, 11, 12, 14, 16, 17, 18, 19, 20, 22, 23}),
        turn="white",
    ),
    concept="Les cases vides en 13 et 24 laissent entrevoir une rafle finissant en 15. L'offre classique de 3 pions par 26-21 livre le temps de repos qui ouvre la rafle 33x15.",
    published_notation='26-21 (17x28) 38-33 (22x31) 33x15',
    final_move=Move(
        path=(33, 22, 13, 24, 15),
        captures=(18, 19, 20, 28),
    ),
    explanation='26-21 sacrifice. (17x28) prise. 38-33 deuxième sacrifice (temps de repos). (22x31) prise. Rafle finale 33x15.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p30_d08',
    crop_id='crops/page_030_d08.png',
    confidence="high",
)

BEG_CH08_011 = BeginnerPosition(
    id="BEG_CH08_011",
    theme="coup_de_talon",
    title='Dubois ch9 D9 — Coup de talon (Toet-Luteijn 1977)',
    state=GameState(
        white_men=frozenset({36, 37, 38, 41, 46, 24, 25, 29, 30, 31}),
        black_men=frozenset({9, 13, 15, 16, 19, 21, 22, 26, 27, 28}),
        turn="white",
    ),
    concept='Partie 1977. La rafle 41x3 et la formation 31-36-37-41-46 sont caractéristiques du coup de talon — un coup nommé du répertoire combinatoire.',
    published_notation='24-20 (15x42) 37x48 (26x37) 41x3',
    final_move=Move(
        path=(41, 32, 23, 14, 3),
        captures=(9, 19, 28, 37),
    ),
    explanation='24-20 sacrifice. (15x42) prise majoritaire noire (longue rafle). 37x48 rafle blanche. (26x37) prise. Rafle finale 41x3 (promotion). Mécanisme du coup de talon.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p30_d09',
    crop_id='crops/page_030_d09.png',
    confidence="high",
    claude_notes='Partie Toet-Luteijn (Blokken RDG, 10-02-1977). Coup de talon, formation 31-36-37-41-46 caractéristique. Voir Dubois chap 19 pour le détail du coup nommé.',
)

BEG_CH08_012 = BeginnerPosition(
    id="BEG_CH08_012",
    theme="creation_temps_de_repos",
    title='Dubois ch9 D10 — Rafle aboutissant à 3',
    state=GameState(
        white_men=frozenset({32, 35, 36, 37, 38, 43, 45, 22, 27, 28}),
        black_men=frozenset({9, 13, 16, 19, 20, 21, 24, 26, 29, 30}),
        turn="white",
    ),
    concept="Une rafle finissant à la case 3 est la plus probable. Points d'appui possibles : 32 et 45. Le pion 32 est le meilleur candidat, à condition d'amener un pion en 28.",
    published_notation='28-23 (19x17) 27-22 (17x28) 32x3',
    final_move=Move(
        path=(32, 23, 34, 25, 14, 3),
        captures=(9, 20, 28, 29, 30),
    ),
    explanation='28-23 sacrifice. (19x17) prise. 27-22 deuxième sacrifice. (17x28) prise. Rafle finale 32x3 = 32→23→14→3 (3 captures, promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p30_d10',
    crop_id='crops/page_030_d10.png',
    confidence="high",
)



# ============================================================================
# Chapitre 9 — Le coup de l'Express
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 13, pages 42-44.
#
# Le coup de l'Express est le premier des coups nommés tactiques (suivront
# Ricochet, Rappel, Renversé, Napoléon, Trappe, Talon, Philippe). Il se
# caractérise par une suite de 4 sacrifices consécutifs qui acheminent les
# pions adverses par paires, suivie d'une rafle finale 33x2 ou 33x4
# (ou symétrique pour le noir).

BEG_CH09_001 = BeginnerPosition(
    id="BEG_CH09_001",
    theme="coup_express",
    title="Exemple narratif Dubois ch13 — Forme typique du coup de l'express",
    state=GameState(
        white_men=frozenset({33, 37, 38, 39, 27, 28}),
        black_men=frozenset({8, 9, 26, 16}),
        turn="white",
    ),
    concept="Le coup de l'express est un mécanisme combinatoire célèbre, caractérisé par une suite de 4 sacrifices consécutifs qui acheminent les pions noirs par paires successives, suivie d'une rafle finale 33x2 ou 33x4.",
    published_notation='37-31 (26x37) 27-21 (16x27) 28-22 (27x18) 38-32 (37x28) 33x2',
    final_move=Move(
        path=(33, 22, 13, 2),
        captures=(8, 18, 28),
    ),
    explanation='37-31 (26x37) 27-21 (16x27) 28-22 (27x18) 38-32 (37x28) 33x2. 4 sacrifices puis rafle finale (5 captures, promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p42_d02',
    crop_id='crops/page_042_d02.png',
    confidence="high",
    claude_notes="Position centrale du chap 13 Dubois : le coup de l'express dans sa forme canonique.",
)

BEG_CH09_002 = BeginnerPosition(
    id="BEG_CH09_002",
    theme="coup_express",
    title="Position finale du coup de l'express — Trait blanc après rafle 33x2",
    state=GameState(
        white_men=frozenset({33, 39}),
        black_men=frozenset({8, 9, 18, 28}),
        turn="white",
    ),
    concept="Position finale typique après un coup de l'express réussi. Le pion blanc 33 a balayé la grande diagonale et atteint la case 2 (promotion).",
    published_notation='33x2',
    final_move=Move(
        path=(33, 22, 13, 2),
        captures=(8, 18, 28),
    ),
    explanation="Cette position montre l'aboutissement caractéristique du coup de l'express : une rafle 33x2 (ou 33x4) après une suite de sacrifices consécutifs.",
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p42_d03',
    crop_id='crops/page_042_d03.png',
    confidence="high",
    claude_notes="Position finale après rafle d'express, montrée à titre illustratif (pas de combinaison à jouer).",
)

BEG_CH09_003 = BeginnerPosition(
    id="BEG_CH09_003",
    theme="coup_express",
    title='Dubois ch13 D1 — Acheminer un pion noir en 21',
    state=GameState(
        white_men=frozenset({34, 35, 36, 38, 39, 26, 31}),
        black_men=frozenset({16, 18, 23, 24, 12, 13, 14}),
        turn="white",
    ),
    concept='La rafle 26x10 semble la plus probable. Il reste à acheminer un pion noir en 21.',
    published_notation='34-29 (23x32) 31-27 (32x21) 26x10',
    final_move=Move(
        path=(26, 17, 8, 19, 10),
        captures=(12, 13, 14, 21),
    ),
    explanation='34-29 sacrifice. (23x32) prise. 31-27 deuxième sacrifice. (32x21) prise. Rafle 26x10 = trajectoire vers 10 (4 captures).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p43_d01',
    crop_id='crops/page_043_d01.png',
    confidence="high",
)

BEG_CH09_004 = BeginnerPosition(
    id="BEG_CH09_004",
    theme="coup_express",
    title="Dubois ch13 D2 — Position d'enchaînement noir (Grotenhuis ten Harkel-Stokkel 1977)",
    state=GameState(
        white_men=frozenset({32, 33, 35, 36, 37, 38, 39, 40, 23, 27, 28, 29}),
        black_men=frozenset({2, 6, 8, 12, 14, 15, 17, 18, 19, 20, 24, 25, 26}),
        turn="white",
    ),
    concept="Partie historique 1977. Trait aux noirs. Position d'enchaînement où les noirs gagnent par coup d'express.",
    published_notation='(17-22) 28x17 (19x28) 33x13 (24x11)',
    final_move=Move(
        path=(33, 22, 13),
        captures=(18, 28),
    ),
    explanation='(17-22) sacrifice. 28x17 prise. (19x28) deuxième sacrifice. 33x13 prise. (24x11) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p43_d02',
    crop_id='crops/page_043_d02.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Grotenhuis ten Harkel-Stokkel (NLD-chJ, 10-04-1977).',
)

BEG_CH09_005 = BeginnerPosition(
    id="BEG_CH09_005",
    theme="coup_express",
    title="Dubois ch13 D3 — Coup d'express avec pion à 16 (Perot-Mostovoy 1968)",
    state=GameState(
        white_men=frozenset({32, 33, 35, 37, 38, 39, 45, 16, 30}),
        black_men=frozenset({4, 7, 12, 14, 17, 18, 20, 22, 23, 26}),
        turn="white",
    ),
    concept="Partie historique 1968. Trait aux noirs. Combinaison très usuelle en présence d'un pion noir à 16.",
    published_notation='(23-29) 33x15 (17-21) 16x27 (22x44)',
    final_move=Move(
        path=(16, 27),
        captures=(21,),
    ),
    explanation='(23-29) sacrifice. 33x15 prise. (17-21) deuxième sacrifice. 16x27 prise. (22x44) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p43_d03',
    crop_id='crops/page_043_d03.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Perot-Mostovoy (FRA-ch, 05-08-1968).',
)

BEG_CH09_006 = BeginnerPosition(
    id="BEG_CH09_006",
    theme="coup_express",
    title='Dubois ch13 D4 — Méthode points de contact (Ketelaars-Kalsbeek 1997)',
    state=GameState(
        white_men=frozenset({32, 36, 38, 39, 40, 41, 43, 20, 25, 30}),
        black_men=frozenset({3, 4, 9, 14, 16, 19, 21, 22, 23, 27}),
        turn="white",
    ),
    concept='Partie historique 1997. Trait aux noirs. La méthode des points de contact mène à la solution.',
    published_notation='(27-31) 36x29 (19-24) 30x10 (4x35)',
    final_move=Move(
        path=(30, 19, 10),
        captures=(14, 24),
    ),
    explanation='(27-31) sacrifice noir. 36x29 prise. (19-24) deuxième sacrifice. 30x10 prise. (4x35) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p43_d04',
    crop_id='crops/page_043_d04.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Ketelaars-Kalsbeek (Vriendenkring oc, 21-01-1997).',
)

BEG_CH09_007 = BeginnerPosition(
    id="BEG_CH09_007",
    theme="coup_express",
    title='Dubois ch13 D5 — Acheminer un pion noir en 40 (coquille PDF corrigée)',
    state=GameState(
        white_men=frozenset({32, 33, 35, 36, 38, 39, 42, 43, 44, 45, 26, 28}),
        black_men=frozenset({9, 12, 13, 16, 17, 18, 19, 20, 23, 24, 29, 30}),
        turn="white",
    ),
    concept="Rafle 45x3 visible. Le défi : amener un pion noir en 40, en sacrifiant 38 pour ouvrir la diagonale qui forcera la rafle noire 29→38→49→40.",
    published_notation='32-27 (23x21) 38-32 (29x40) 45x3',
    final_move=Move(
        path=(45, 34, 25, 14, 3),
        captures=(9, 20, 30, 40),
    ),
    explanation="32-27 sacrifice blanc. (23x21) prise noire forcée (rafle 23→32→21, capture 27 et 28). 38-32 deuxième sacrifice. (29x40) prise noire forcée — rafle 29→38→49→40 capturant 33, 43, 44 (passe la rangée 46-50 sans promotion grâce à la règle de non-soufflage). 45x3 rafle finale blanche, 45→34→25→14→3 capturant 9, 20, 30, 40 (promotion en dame).",
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p43_d05',
    crop_id='crops/page_043_d05.png',
    confidence="high",
    claude_notes="✅ Coquille PDF Dubois corrigée. Le livre imprime '32-27 (23x21) 43-38 (29x40) 45x3' mais le pion blanc 43 ne peut pas aller en 38 (38 est déjà occupé par un blanc). Le vrai coup est '38-32' (le pion 38 descend en 32, libérant la diagonale pour que le noir 29 prenne 33, 43, 44 jusqu'en 40). Validé par recherche exhaustive (1 solution unique) et confirmation utilisateur. Cf RESOLUTIONS §R009.",
)

BEG_CH09_008 = BeginnerPosition(
    id="BEG_CH09_008",
    theme="coup_express",
    title='Dubois ch13 D6 — Rafle 39x10 ouverte',
    state=GameState(
        white_men=frozenset({32, 37, 38, 39, 42, 44, 47, 24, 29}),
        black_men=frozenset({12, 13, 14, 15, 16, 18, 25, 26, 31}),
        turn="white",
    ),
    concept='2 méthodes pour trouver la solution : tout essayer ou penser à la rafle 39x10.',
    published_notation='32-27 (31x22) 24-20 (15x33) 39x10',
    final_move=Move(
        path=(39, 28, 17, 8, 19, 10),
        captures=(12, 13, 14, 22, 33),
    ),
    explanation='32-27 sacrifice. (31x22) prise. 24-20 deuxième sacrifice. (15x33) prise. Rafle 39x10.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p43_d06',
    crop_id='crops/page_043_d06.png',
    confidence="high",
)

BEG_CH09_009 = BeginnerPosition(
    id="BEG_CH09_009",
    theme="coup_express",
    title='Dubois ch13 D7 — Position noire compacte mais cassable',
    state=GameState(
        white_men=frozenset({32, 33, 35, 36, 37, 38, 39, 43, 49, 26, 28, 29}),
        black_men=frozenset({2, 4, 11, 12, 13, 15, 17, 18, 19, 21, 22, 25}),
        turn="white",
    ),
    concept='La position des noirs semble compacte. Pourtant, tout explose après 29-23.',
    published_notation='29-23 (18x29) 33x24 (22x31) 36x9',
    final_move=Move(
        path=(36, 27, 16, 7, 18, 9),
        captures=(11, 12, 13, 21, 31),
    ),
    explanation='29-23 sacrifice. (18x29) prise. 33x24 rafle. (22x31) prise. 36x9 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p43_d07',
    crop_id='crops/page_043_d07.png',
    confidence="high",
)

BEG_CH09_010 = BeginnerPosition(
    id="BEG_CH09_010",
    theme="coup_express",
    title='Dubois ch13 D8 — Acheminer un pion noir en 37',
    state=GameState(
        white_men=frozenset({33, 34, 36, 38, 39, 41, 42, 43, 45, 46, 49, 26}),
        black_men=frozenset({6, 8, 13, 14, 17, 18, 19, 22, 23, 24, 27, 28}),
        turn="white",
    ),
    concept='La rafle 41x3 est présumée. Reste à amener un pion noir en 37.',
    published_notation='34-29 (23x34) 39x30 (28x37) 41x3',
    final_move=Move(
        path=(41, 32, 21, 12, 3),
        captures=(8, 17, 27, 37),
    ),
    explanation='34-29 sacrifice. (23x34) prise. 39x30 rafle. (28x37) prise. Rafle 41x3 (promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p43_d08',
    crop_id='crops/page_043_d08.png',
    confidence="high",
)

BEG_CH09_011 = BeginnerPosition(
    id="BEG_CH09_011",
    theme="coup_express",
    title="Dubois ch13 D9 — Schéma typique du coup de l'express",
    state=GameState(
        white_men=frozenset({32, 33, 37, 38, 39, 43, 24, 27, 29}),
        black_men=frozenset({8, 9, 12, 13, 15, 16, 17, 18, 26}),
        turn="white",
    ),
    concept="On retrouve ici le schéma classique : enlever le pion 13 et amener un pion noir en 28, puis le coup de l'express déroule la rafle 33x2.",
    published_notation='24-19 (13x24) 29x20 (15x24) 37-31 (26x28) 33x2',
    final_move=Move(
        path=(33, 22, 13, 2),
        captures=(8, 18, 28),
    ),
    explanation="24-19 (13x24) 29x20 (15x24) 37-31 (26x28) 33x2 — 3 sacrifices + rafle finale typique du coup de l'express.",
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p43_d09',
    crop_id='crops/page_043_d09.png',
    confidence="high",
    claude_notes="Schéma canonique du coup de l'express.",
)

BEG_CH09_012 = BeginnerPosition(
    id="BEG_CH09_012",
    theme="coup_express",
    title="Dubois ch13 D10 — Coup de l'express caché",
    state=GameState(
        white_men=frozenset({33, 35, 37, 38, 39, 43, 23, 27, 29}),
        black_men=frozenset({6, 9, 12, 14, 15, 16, 19, 20, 26}),
        turn="white",
    ),
    concept="Le coup de l'express est plus dissimulé ici, mais le mécanisme reste le même : sacrifices en cascade puis rafle 33x4.",
    published_notation='29-24 (20x18) 37-31 (26x37) 38-32 (37x28) 33x4',
    final_move=Move(
        path=(33, 22, 13, 4),
        captures=(9, 18, 28),
    ),
    explanation="29-24 (20x18) 37-31 (26x37) 38-32 (37x28) 33x4 — coup de l'express avec rafle finale 33x4 (au lieu de 33x2).",
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p43_d10',
    crop_id='crops/page_043_d10.png',
    confidence="high",
    claude_notes="Variante du coup de l'express finissant en 4 plutôt qu'en 2.",
)



# ============================================================================
# Chapitre 10 — Le coup de Ricochet
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 14, pages 45-47.
#
# Le coup de Ricochet est caractérisé par une rafle qui revient sur la
# case de départ après avoir traversé une zone clé. C'est une variante
# du coup de l'Express qui exploite mieux l'aile gauche encombrée.

BEG_CH10_001 = BeginnerPosition(
    id="BEG_CH10_001",
    theme="coup_ricochet",
    title='Exemple narratif Dubois ch14 — Schéma de base du Ricochet',
    state=GameState(
        white_men=frozenset({32, 33, 34, 35, 40, 28, 45}),
        black_men=frozenset({16, 19, 21, 23, 9, 13, 25}),
        turn="white",
    ),
    concept='Le coup de Ricochet repose sur une rafle qui revient sur la case de départ (« ricoche ») après avoir traversé une zone clé. Schéma de base : sacrifices 34-30 et 40x18, puis le pion blanc 28 ricoche sur 26 après la prise (13x22).',
    published_notation='34-30 (25x34) 40x18 (13x22) 28x26',
    final_move=Move(
        path=(28, 17, 26),
        captures=(21, 22),
    ),
    explanation="34-30 sacrifice (le noir 25 capture forcé). (25x34) prise. 40x18 rafle blanche traversante. (13x22) prise noire forcée. 28x26 — le pion blanc 28 RICOCHE sur la case 26 en sautant 22. Cette case 26 est où le pion noir était initialement, d'où le nom.",
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p45_d01',
    crop_id='crops/page_045_d01.png',
    confidence="high",
    claude_notes='Schéma canonique du coup de ricochet.',
)

BEG_CH10_002 = BeginnerPosition(
    id="BEG_CH10_002",
    theme="coup_ricochet",
    title='Exemple narratif Dubois ch14 — Application en partie',
    state=GameState(
        white_men=frozenset({27, 28, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 48, 50}),
        black_men=frozenset({1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 13, 14, 15, 16, 18, 19, 21, 23, 25}),
        turn="white",
    ),
    concept="Application pratique du Ricochet : les blancs exploitent leur aile gauche encombrée et la présence d'un pion noir en 25 par un sacrifice 27-22 préalable, suivi du schéma classique.",
    published_notation='27-22 (18x27) 31x22 12-18 46-41 (18x27) 34-30 (25x34) 40x18 (13x22) 28x26',
    final_move=None,
    explanation='Combinaison à 6 demi-coups : 27-22 (18x27) 31x22 (sacrifice initial) ; 12-18 (réponse noire forcée) ; 46-41 (coup silencieux) (18x27) ; puis schéma standard 34-30 (25x34) 40x18 (13x22) 28x26.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p45_d04',
    crop_id='crops/page_045_d04.png',
    confidence="high",
    claude_notes='Combinaison longue avec coup silencieux 46-41. final_move=None car notation à plusieurs phases.',
)

BEG_CH10_003 = BeginnerPosition(
    id="BEG_CH10_003",
    theme="coup_ricochet",
    title='Dubois ch14 D1 — Collage et coup de dame en 5',
    state=GameState(
        white_men=frozenset({33, 34, 35, 38, 40, 41, 43, 47, 48, 49, 28, 29}),
        black_men=frozenset({2, 3, 8, 10, 12, 13, 15, 16, 17, 18, 20, 24}),
        turn="white",
    ),
    concept='Un coup de dame sur la case 5 utilisant le mécanisme de collage combiné au ricochet.',
    published_notation='28-22 (17x30) 40-34 (24x42) 34x5',
    final_move=Move(
        path=(34, 25, 14, 5),
        captures=(10, 20, 30),
    ),
    explanation='28-22 sacrifice. (17x30) prise. 40-34 collage. (24x42) prise. 34x5 rafle finale (promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p46_d01',
    crop_id='crops/page_046_d01.png',
    confidence="high",
)

BEG_CH10_004 = BeginnerPosition(
    id="BEG_CH10_004",
    theme="coup_ricochet",
    title='Dubois ch14 D2 — Coup de dame en 4',
    state=GameState(
        white_men=frozenset({32, 33, 35, 36, 37, 39, 40, 43, 45, 49, 26, 28, 29, 31}),
        black_men=frozenset({2, 3, 6, 8, 9, 12, 14, 15, 16, 17, 18, 19, 20, 22}),
        turn="white",
    ),
    concept='Les trous 4 et 13 dans la position noire font penser à un coup de dame en 4.',
    published_notation='29-24 (20x27) 49-44 (22x33) 31x4',
    final_move=Move(
        path=(31, 22, 13, 4),
        captures=(9, 18, 27),
    ),
    explanation='29-24 sacrifice. (20x27) prise. 49-44 collage. (22x33) prise. 31x4 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p46_d02',
    crop_id='crops/page_046_d02.png',
    confidence="high",
)

BEG_CH10_005 = BeginnerPosition(
    id="BEG_CH10_005",
    theme="coup_ricochet",
    title='Dubois ch14 D3 — Combinaison ultra classique',
    state=GameState(
        white_men=frozenset({32, 35, 37, 39, 42, 47, 48, 49, 25, 27, 28}),
        black_men=frozenset({2, 3, 8, 12, 14, 15, 16, 17, 18, 19, 23}),
        turn="white",
    ),
    concept='Une combinaison ultra classique qui se présente fréquemment en partie. Le coup de ricochet caractéristique 42x24.',
    published_notation='28-22 (17x28) 27-21 (16x38) 42x24',
    final_move=Move(
        path=(42, 33, 22, 13, 24),
        captures=(18, 19, 28, 38),
    ),
    explanation='28-22 sacrifice. (17x28) prise. 27-21 deuxième sacrifice. (16x38) prise noire majoritaire. 42x24 rafle ricochet.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p46_d03',
    crop_id='crops/page_046_d03.png',
    confidence="high",
)

BEG_CH10_006 = BeginnerPosition(
    id="BEG_CH10_006",
    theme="coup_ricochet",
    title='Dubois ch14 D4 — Coup de dame 31x4 (Kloot-Kuipers 1939)',
    state=GameState(
        white_men=frozenset({32, 35, 36, 37, 38, 40, 42, 43, 45, 49, 27, 28}),
        black_men=frozenset({2, 3, 7, 8, 9, 10, 12, 13, 16, 19, 20, 23, 26}),
        turn="white",
    ),
    concept="Partie historique 1939. Un coup de dame 31x4. Il suffit d'acheminer un pion noir en 30.",
    published_notation='37-31 (26x39) 40-34 (39x30) 35x4',
    final_move=Move(
        path=(35, 24, 15, 4),
        captures=(10, 20, 30),
    ),
    explanation='37-31 sacrifice. (26x39) prise. 40-34 collage. (39x30) prise. 35x4 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p46_d04',
    crop_id='crops/page_046_d04.png',
    confidence="high",
    claude_notes='Partie Kloot-Kuipers (Ibis, 20-01-1939).',
)

BEG_CH10_007 = BeginnerPosition(
    id="BEG_CH10_007",
    theme="coup_ricochet",
    title='Dubois ch14 D5 — Coup de dame en 1',
    state=GameState(
        white_men=frozenset({33, 35, 37, 39, 42, 43, 44, 47, 49, 26, 29}),
        black_men=frozenset({36, 7, 9, 11, 13, 14, 15, 17, 18, 19, 22}),
        turn="white",
    ),
    concept='Un coup de dame en 1 avec une rafle 43x1.',
    published_notation='37-31 (36x27) 29-23 (18x38) 43x1',
    final_move=Move(
        path=(43, 32, 21, 12, 1),
        captures=(7, 17, 27, 38),
    ),
    explanation='37-31 sacrifice. (36x27) prise. 29-23 deuxième sacrifice. (18x38) prise. 43x1 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p46_d05',
    crop_id='crops/page_046_d05.png',
    confidence="high",
)

BEG_CH10_008 = BeginnerPosition(
    id="BEG_CH10_008",
    theme="coup_ricochet",
    title='Dubois ch14 D6 — Rafle 44x2 (coquille PDF corrigée)',
    state=GameState(
        white_men=frozenset({32, 50, 38, 40, 27, 44, 31}),
        black_men=frozenset({16, 17, 18, 23, 8, 25, 30}),
        turn="white",
    ),
    concept='Un coup de dame à 2 avec une case de départ de la rafle en 44.',
    published_notation='27-21 (17x28) 40-34 (30x39) 44x2',
    final_move=Move(
        path=(44, 33, 22, 13, 2),
        captures=(8, 18, 28, 39),
    ),
    explanation="27-21 sacrifice blanc. (17x28) prise majoritaire noire forcée (rafle 17→26→37→28 capturant 21, 31, 32). 40-34 deuxième sacrifice. (30x39) prise forcée. 44x2 rafle finale 44→33→22→13→2 capturant 8, 18, 28, 39 (promotion en dame).",
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p46_d06',
    crop_id='crops/page_046_d06.png',
    confidence="high",
    claude_notes="✅ Coquille PDF Dubois corrigée. Le livre imprime '37-31 (26x28) 40-34 (30x39) 44x2' mais ni le pion blanc 37 ni le pion noir 26 n'existent dans la position. La vraie séquence est '27-21 (17x28)' (probable double inversion typographique : 37↔27, 31↔21, 26↔17). Validé par recherche exhaustive (1 unique solution) et confirmation utilisateur. Cf RESOLUTIONS §R010.",
)

BEG_CH10_009 = BeginnerPosition(
    id="BEG_CH10_009",
    theme="coup_napoleon",
    title='Dubois ch14 D7 — Coup Napoléon (préview)',
    state=GameState(
        white_men=frozenset({32, 35, 36, 37, 38, 39, 25, 26, 27, 28, 31}),
        black_men=frozenset({6, 12, 13, 14, 15, 16, 17, 18, 19, 23, 29}),
        turn="white",
    ),
    concept='Bien que le chapitre traite du Ricochet, cette fixture introduit un autre coup nommé : le coup Napoléon, caractérisé par sa rafle finale 31x24.',
    published_notation='28-22 (17x28) 27-21 (16x27) 31x24',
    final_move=Move(
        path=(31, 22, 33, 24),
        captures=(27, 28, 29),
    ),
    explanation='28-22 (17x28) 27-21 (16x27) 31x24 — schéma typique du coup Napoléon (voir chap 13 manuel).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p46_d07',
    crop_id='crops/page_046_d07.png',
    confidence="high",
    claude_notes='Coup Napoléon — préview du chap 13 manuel.',
)

BEG_CH10_010 = BeginnerPosition(
    id="BEG_CH10_010",
    theme="coup_ricochet",
    title='Dubois ch14 D8 — Ricochet dissimulé (Coenen-van Ingen 1990)',
    state=GameState(
        white_men=frozenset({32, 33, 34, 35, 36, 37, 38, 40, 45, 46, 22, 27, 30}),
        black_men=frozenset({4, 6, 7, 8, 12, 14, 18, 19, 20, 23, 24, 25, 26}),
        turn="black",
    ),
    concept='Partie 1990. Trait aux noirs. Combinaison très complexe à 7 demi-coups, le ricochet est bien dissimulé.',
    published_notation='(23-28) 22x11 (28x39) 34x43 (25x34) 40x29 (24x22)',
    final_move=Move(
        path=(24, 33, 42, 31, 22),
        captures=(27, 29, 37, 38),
    ),
    explanation='(23-28) sacrifice noir. 22x11 rafle blanche. (28x39) prise. 34x43 rafle blanche. (25x34) prise. 40x29 rafle blanche. (24x22) rafle finale noire.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p46_d08',
    crop_id='crops/page_046_d08.png',
    confidence="high",
    claude_notes="Trait aux noirs. Partie Coenen-van Ingen (Nijmegen, 25-07-1990). 7 demi-coups, l'une des plus complexes du chapitre.",
)

BEG_CH10_011 = BeginnerPosition(
    id="BEG_CH10_011",
    theme="coup_ricochet",
    title='Dubois ch14 D9 — Coup de dame à 4 via ricochet',
    state=GameState(
        white_men=frozenset({26, 31, 33, 34, 35, 36, 38, 39, 40, 41, 43, 44, 45, 46, 48, 49}),
        black_men=frozenset({2, 6, 8, 9, 10, 11, 12, 13, 14, 17, 18, 20, 22, 24, 27, 28}),
        turn="white",
    ),
    concept='Un coup de dame à 4 utilisant le mécanisme du ricochet pour faire sauter le pion noir 24 et amener un pion noir en 29.',
    published_notation='35-30 (24x35) 26-21 (17x37) 41x23 (18x29) 33x4',
    final_move=Move(
        path=(33, 24, 15, 4),
        captures=(10, 20, 29),
    ),
    explanation='35-30 sacrifice. (24x35) prise. 26-21 deuxième sacrifice. (17x37) prise. 41x23 rafle ricochet. (18x29) prise. 33x4 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p46_d09',
    crop_id='crops/page_046_d09.png',
    confidence="high",
)

BEG_CH10_012 = BeginnerPosition(
    id="BEG_CH10_012",
    theme="coup_ricochet",
    title='Dubois ch14 D10 — Rafle cachée (Le Goff-Molimard 1909)',
    state=GameState(
        white_men=frozenset({32, 34, 35, 36, 37, 38, 39, 40, 42, 47, 48, 24, 25, 29, 30}),
        black_men=frozenset({3, 4, 6, 8, 9, 11, 13, 14, 15, 16, 19, 21, 22, 23, 26}),
        turn="black",
    ),
    concept='Partie historique 1909. Trait aux noirs. La rafle finale (21x45) est très bien cachée. Méthode des points de contact essentielle.',
    published_notation='(15-20) 29x27 (20x29) 34x23 (19x28) 32x23 (21x45)',
    final_move=Move(
        path=(21, 32, 43, 34, 45),
        captures=(27, 38, 39, 40),
    ),
    explanation='(15-20) sacrifice noir. 29x27 rafle blanche. (20x29) prise. 34x23 rafle blanche. (19x28) prise. 32x23 rafle ricochet blanche. (21x45) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p46_d10',
    crop_id='crops/page_046_d10.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Le Goff-Molimard (1909). 7 demi-coups, ricochet dissimulé.',
)



# ============================================================================
# Chapitre 11 — Le coup de Rappel
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 15, pages 48-50.
#
# Le coup de Rappel exploite une rafle adverse qui descend trop bas (en 39
# par ex) : un nouveau sacrifice force le pion à remonter (« rappel »)
# pour le capturer définitivement avec la rafle finale.

BEG_CH11_001 = BeginnerPosition(
    id="BEG_CH11_001",
    theme="coup_rappel",
    title='Exemple narratif Dubois ch15 — Schéma 1 du coup de Rappel',
    state=GameState(
        white_men=frozenset({32, 33, 37, 38, 28}),
        black_men=frozenset({8, 18, 19}),
        turn="white",
    ),
    concept="Le coup de Rappel est caractérisé par un pion noir qui descend par sa prise jusqu'à la 4e ou 5e ligne, puis est « rappelé » vers le haut par un nouveau sacrifice qui force sa capture pour la rafle finale.",
    published_notation='28-23 (19x39) 38-33 (39x28) 32x3',
    final_move=Move(
        path=(32, 23, 12, 3),
        captures=(8, 18, 28),
    ),
    explanation='28-23 sacrifice. (19x39) prise noire qui descend. 38-33 RAPPEL — sacrifice qui force le noir 39 à remonter. (39x28) prise. 32x3 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p48_d01',
    crop_id='crops/page_048_d01.png',
    confidence="high",
    claude_notes='Schéma 1 du coup de Rappel.',
)

BEG_CH11_002 = BeginnerPosition(
    id="BEG_CH11_002",
    theme="coup_rappel",
    title='Exemple narratif Dubois ch15 — Schéma 2 du coup de Rappel',
    state=GameState(
        white_men=frozenset({40, 34, 35, 30}),
        black_men=frozenset({10, 19, 20}),
        turn="white",
    ),
    concept="Variante du coup de Rappel : la rafle finale aboutit en 4 plutôt qu'en 3.",
    published_notation='30-24 (19x39) 40-34 (39x30) 35x4',
    final_move=Move(
        path=(35, 24, 15, 4),
        captures=(10, 20, 30),
    ),
    explanation='30-24 sacrifice. (19x39) prise. 40-34 rappel. (39x30) prise. 35x4 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p48_d02',
    crop_id='crops/page_048_d02.png',
    confidence="high",
    claude_notes='Schéma 2 du coup de Rappel.',
)

BEG_CH11_003 = BeginnerPosition(
    id="BEG_CH11_003",
    theme="coup_rappel",
    title='Exemple narratif Dubois ch15 — Schéma 3 du coup de Rappel',
    state=GameState(
        white_men=frozenset({32, 33, 38, 39, 28}),
        black_men=frozenset({9, 18, 17}),
        turn="white",
    ),
    concept='Variante 3 : le rappel se fait via la case 32, et la rafle finale en 4.',
    published_notation='28-22 (17x37) 38-32 (37x28) 33x4',
    final_move=Move(
        path=(33, 22, 13, 4),
        captures=(9, 18, 28),
    ),
    explanation='28-22 sacrifice. (17x37) prise. 38-32 rappel. (37x28) prise. 33x4 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p48_d03',
    crop_id='crops/page_048_d03.png',
    confidence="high",
    claude_notes='Schéma 3 du coup de Rappel.',
)

BEG_CH11_004 = BeginnerPosition(
    id="BEG_CH11_004",
    theme="coup_rappel",
    title='Dubois ch15 D1 — Rafle finissant en 7 via pion de base 49',
    state=GameState(
        white_men=frozenset({32, 33, 37, 38, 39, 42, 44, 45, 49, 27}),
        black_men=frozenset({35, 8, 12, 13, 14, 16, 19, 23, 24, 26}),
        turn="white",
    ),
    concept='Le pion de base 49 peut aboutir en 7. Il manque seulement un pion en 34.',
    published_notation='32-28 (23x34) 44-40 (35x44) 49x7',
    final_move=Move(
        path=(49, 40, 29, 20, 9, 18, 7),
        captures=(12, 13, 14, 24, 34, 44),
    ),
    explanation='32-28 sacrifice. (23x34) prise. 44-40 rappel. (35x44) prise. 49x7 rafle finale longue.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p49_d01',
    crop_id='crops/page_049_d01.png',
    confidence="high",
)

BEG_CH11_005 = BeginnerPosition(
    id="BEG_CH11_005",
    theme="coup_rappel",
    title='Dubois ch15 D2 — Acheminer pion noir en 22',
    state=GameState(
        white_men=frozenset({32, 33, 34, 37, 38, 39, 42, 44, 22, 27, 28}),
        black_men=frozenset({9, 11, 12, 13, 14, 16, 18, 24, 25, 26, 30}),
        turn="white",
    ),
    concept="Rafle se terminant en 10. Le coup de Rappel force un pion noir à revenir capturer sur la case 22 (le sacrifice 32-27 puis la reprise 31x22), ce qui le ramène sur la trajectoire de la rafle blanche finale 28x10.",
    published_notation='22-17 (11x31) 32-27 (31x22) 28x10',
    final_move=Move(
        path=(28, 17, 8, 19, 10),
        captures=(12, 13, 14, 22),
    ),
    explanation='22-17 sacrifice. (11x31) prise. 32-27 rappel. (31x22) prise. 28x10 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p49_d02',
    crop_id='crops/page_049_d02.png',
    confidence="high",
)

BEG_CH11_006 = BeginnerPosition(
    id="BEG_CH11_006",
    theme="coup_rappel",
    title='Dubois ch15 D3 — Acheminer pion noir en 33',
    state=GameState(
        white_men=frozenset({34, 36, 38, 39, 43, 44, 26, 29}),
        black_men=frozenset({35, 11, 12, 13, 18, 20, 23, 27}),
        turn="white",
    ),
    concept='Rafle en 6 visible. Il faut amener un pion noir en 33 par le rappel.',
    published_notation='34-30 (35x42) 43-38 (42x33) 39x6',
    final_move=Move(
        path=(39, 28, 19, 8, 17, 6),
        captures=(11, 12, 13, 23, 33),
    ),
    explanation='34-30 sacrifice. (35x42) prise. 43-38 rappel. (42x33) prise. 39x6 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p49_d03',
    crop_id='crops/page_049_d03.png',
    confidence="high",
)

BEG_CH11_007 = BeginnerPosition(
    id="BEG_CH11_007",
    theme="coup_rappel",
    title='Dubois ch15 D4 — Combinaison + fin de partie',
    state=GameState(
        white_men=frozenset({32, 33, 37, 24, 41, 29, 30}),
        black_men=frozenset({16, 22, 9, 12, 13, 14, 15}),
        turn="white",
    ),
    concept='Combinaison qui mène à une finale gagnante. Si les noirs échangent, ils perdent par opposition.',
    published_notation='24-20 (14x23) 32-28 (23x32) 37x19',
    final_move=Move(
        path=(37, 28, 17, 8, 19),
        captures=(12, 13, 22, 32),
    ),
    explanation='24-20 sacrifice. (14x23) prise. 32-28 deuxième sacrifice. (23x32) prise. 37x19 rafle finale. La position est gagnante par opposition (théorie des fins de partie).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p49_d04',
    crop_id='crops/page_049_d04.png',
    confidence="high",
    claude_notes='Combinaison + fin de partie. Sur (15-20), la lunette 19-14 est décisive.',
)

BEG_CH11_008 = BeginnerPosition(
    id="BEG_CH11_008",
    theme="coup_de_trappe",
    title='Dubois ch15 D5 — Coup de la Trappe (Michiels-Marini 1986)',
    state=GameState(
        white_men=frozenset({32, 33, 36, 37, 38, 40, 44, 15, 48, 50, 26, 27}),
        black_men=frozenset({2, 35, 4, 6, 7, 8, 12, 13, 14, 16, 23, 24}),
        turn="white",
    ),
    concept='Partie historique 1986. Bien que ce chapitre traite du Rappel, cette fixture introduit le coup de la Trappe (chap 18 manuel) — rafle très efficace via 50x10.',
    published_notation='44-39 (35x44) 32-28 (23x34) 50x10',
    final_move=Move(
        path=(50, 39, 30, 19, 10),
        captures=(14, 24, 34, 44),
    ),
    explanation='44-39 sacrifice. (35x44) prise. 32-28 rappel-trappe. (23x34) prise. 50x10 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p49_d05',
    crop_id='crops/page_049_d05.png',
    confidence="high",
    claude_notes='Préview coup de la Trappe (chap 18 manuel). Partie Michiels-Marini (BEL-ch, 1986).',
)

BEG_CH11_009 = BeginnerPosition(
    id="BEG_CH11_009",
    theme="coup_de_trappe",
    title='Dubois ch15 D6 — Autre coup de la Trappe',
    state=GameState(
        white_men=frozenset({33, 34, 37, 38, 44, 50, 27, 28}),
        black_men=frozenset({18, 19, 8, 25, 11, 12, 30}),
        turn="white",
    ),
    concept='Joli petit coup de la Trappe. Mécanisme proche du Rappel mais avec rafle finale différente.',
    published_notation='38-32 (30x39) 27-22 (18x29) 44x2',
    final_move=Move(
        path=(44, 33, 24, 13, 2),
        captures=(8, 19, 29, 39),
    ),
    explanation='38-32 sacrifice. (30x39) prise. 27-22 deuxième sacrifice. (18x29) prise. 44x2 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p49_d06',
    crop_id='crops/page_049_d06.png',
    confidence="high",
    claude_notes='Préview coup de la Trappe (chap 18 manuel).',
)

BEG_CH11_010 = BeginnerPosition(
    id="BEG_CH11_010",
    theme="coup_rappel",
    title='Dubois ch15 D7 — Rappel à 4 demi-coups (Rapopport-Gertsenzon 1963)',
    state=GameState(
        white_men=frozenset({34, 35, 38, 47, 48, 25, 26, 27, 29, 30}),
        black_men=frozenset({3, 9, 11, 12, 13, 14, 15, 16, 18, 28}),
        turn="white",
    ),
    concept="Partie 1963. 2 rafles plausibles. La rafle 30x6 demande d'amener le pion 15 en 24 via le rappel.",
    published_notation='38-32 (28x37) 25-20 (15x33) 34-29 (33x24) 30x6',
    final_move=Move(
        path=(30, 19, 8, 17, 6),
        captures=(11, 12, 13, 24),
    ),
    explanation='38-32 sacrifice. (28x37) prise. 25-20 deuxième sacrifice. (15x33) prise. 34-29 rappel. (33x24) prise. 30x6 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p49_d07',
    crop_id='crops/page_049_d07.png',
    confidence="high",
    claude_notes='Partie Rapopport-Gertsenzon (URS-chT, 03-06-1963). 4 demi-coups, plus complexe.',
)

BEG_CH11_011 = BeginnerPosition(
    id="BEG_CH11_011",
    theme="coup_rappel",
    title='Dubois ch15 D8 — Coup de dame à 50 noir (van Aalten-Clerc 1976)',
    state=GameState(
        white_men=frozenset({32, 33, 34, 36, 37, 38, 40, 43, 44, 45, 47, 24, 29}),
        black_men=frozenset({2, 4, 8, 10, 11, 12, 13, 15, 17, 18, 22, 23, 25}),
        turn="black",
    ),
    concept='Partie 1976. Trait aux noirs. Coup de dame à 48 ou 50. Mécanisme du coup de rappel.',
    published_notation='(23-28) 32x23 (22-28) 23x32 (13-19) 24x22 (17x50)',
    final_move=Move(
        path=(17, 28, 39, 50),
        captures=(22, 33, 44),
    ),
    explanation='(23-28) sacrifice noir. 32x23 prise forcée. (22-28) deuxième sacrifice. 23x32 prise. (13-19) troisième sacrifice. 24x22 prise. (17x50) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p49_d08',
    crop_id='crops/page_049_d08.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie van Aalten-Clerc (Tournoi Heijting 1976). 7 demi-coups.',
)

BEG_CH11_012 = BeginnerPosition(
    id="BEG_CH11_012",
    theme="coup_rappel",
    title='Dubois ch15 D9 — Rafle en 44 (trait noir)',
    state=GameState(
        white_men=frozenset({34, 35, 37, 38, 39, 41, 16, 21, 29, 30}),
        black_men=frozenset({7, 9, 12, 13, 15, 18, 19, 22, 23, 25}),
        turn="black",
    ),
    concept='Trait aux noirs. Rafle finale en 44. Case de départ : 13. Il faut amener un blanc en 27 et un autre en 18.',
    published_notation='(22-27) 21x32 (18-22) 29x27 (7-11) 16x18 (13x44)',
    final_move=Move(
        path=(13, 22, 31, 42, 33, 44),
        captures=(18, 27, 37, 38, 39),
    ),
    explanation='(22-27) sacrifice noir. 21x32 prise. (18-22) sacrifice. 29x27 prise. (7-11) sacrifice. 16x18 prise. (13x44) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p49_d09',
    crop_id='crops/page_049_d09.png',
    confidence="high",
    claude_notes='Trait aux noirs. 7 demi-coups, structure complexe.',
)



# ============================================================================
# Chapitre 12 — Le coup Renversé
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 16, pages 51-53.
#
# Le coup renversé est un mécanisme moins courant mais utile car il se
# marie avec des coups de mazette, coups Philippe et coups de ricochet.
# Il inclut une variante notable, le « coup de chevron » (D2 Datel-
# Schwarzman 1977).

BEG_CH12_001 = BeginnerPosition(
    id="BEG_CH12_001",
    theme="coup_renverse",
    title='Dubois ch16 D1 — Combinaison à la case 4',
    state=GameState(
        white_men=frozenset({32, 33, 35, 38, 39, 42, 44, 47, 48, 26, 29, 31}),
        black_men=frozenset({2, 6, 8, 10, 12, 14, 16, 17, 18, 19, 20, 24}),
        turn="white",
    ),
    concept='Combinaison aboutissant à la case 4 par coup renversé.',
    published_notation='35-30 (24x35) 26-21 (17x28) 33x4',
    final_move=Move(
        path=(33, 22, 13, 24, 15, 4),
        captures=(10, 18, 19, 20, 28),
    ),
    explanation='35-30 sacrifice. (24x35) prise. 26-21 deuxième sacrifice. (17x28) prise. 33x4 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p52_d01',
    crop_id='crops/page_052_d01.png',
    confidence="high",
)

BEG_CH12_002 = BeginnerPosition(
    id="BEG_CH12_002",
    theme="coup_renverse",
    title='Dubois ch16 D2 — Coup de chevron (Datel-Schwarzman 1977)',
    state=GameState(
        white_men=frozenset({22, 27, 28, 30, 31, 32, 33, 35, 37, 38, 39, 41, 45, 46, 47, 48, 49}),
        black_men=frozenset({1, 3, 7, 8, 9, 10, 11, 13, 14, 16, 17, 18, 19, 21, 26}),
        turn="black",
    ),
    concept='Partie 1977. Trait aux noirs. Variante du coup renversé connue sous le nom de « coup de chevron » à cause de la rafle finale 21x25.',
    published_notation='(19-23) 28x19 (17x28) 32x12 (21x25)',
    final_move=Move(
        path=(21, 32, 43, 34, 25),
        captures=(27, 30, 38, 39),
    ),
    explanation='(19-23) sacrifice noir. 28x19 prise. (17x28) deuxième sacrifice. 32x12 prise. (21x25) rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p52_d02',
    crop_id='crops/page_052_d02.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Datel-Schwarzman (ISR-ch 1977). Coup de chevron — variante du renversé.',
)

BEG_CH12_003 = BeginnerPosition(
    id="BEG_CH12_003",
    theme="coup_renverse",
    title='Dubois ch16 D3 — Coup de dame à 2 via éliminations',
    state=GameState(
        white_men=frozenset({32, 33, 34, 35, 36, 37, 38, 48, 25, 27}),
        black_men=frozenset({7, 10, 12, 16, 17, 18, 19, 23, 24, 26}),
        turn="white",
    ),
    concept="Coup de dame à 2 partant de la case 35. Élimination du 24 et acheminement d'un noir en 30.",
    published_notation='25-20 (24x15) 37-31 (26x30) 35x2',
    final_move=Move(
        path=(35, 24, 13, 22, 11, 2),
        captures=(7, 17, 18, 19, 30),
    ),
    explanation='25-20 sacrifice. (24x15) prise. 37-31 deuxième sacrifice. (26x30) prise. 35x2 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p52_d03',
    crop_id='crops/page_052_d03.png',
    confidence="high",
)

BEG_CH12_004 = BeginnerPosition(
    id="BEG_CH12_004",
    theme="coup_renverse",
    title='Dubois ch16 D4 — Exploitation pion de bande 35 (Gordijn-den Hartogh 1952)',
    state=GameState(
        white_men=frozenset({32, 33, 34, 36, 38, 39, 42, 44, 45, 48, 26, 31}),
        black_men=frozenset({2, 35, 6, 7, 8, 12, 13, 14, 15, 16, 19, 22}),
        turn="white",
    ),
    concept='Partie 1952. Exploitation du pion de bande 35 pour le coup renversé.',
    published_notation='34-30 (35x24) 33-28 (22x33) 38x18',
    final_move=Move(
        path=(38, 29, 20, 9, 18),
        captures=(13, 14, 24, 33),
    ),
    explanation='34-30 sacrifice. (35x24) prise majoritaire noire. 33-28 deuxième sacrifice. (22x33) prise. 38x18 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p52_d04',
    crop_id='crops/page_052_d04.png',
    confidence="high",
    claude_notes='Partie Gordijn-den Hartogh (Damas, 1952).',
)

BEG_CH12_005 = BeginnerPosition(
    id="BEG_CH12_005",
    theme="coup_de_trappe",
    title='Dubois ch16 D5 — Coup de la Trappe (Clasquin-van Es 1981)',
    state=GameState(
        white_men=frozenset({32, 33, 35, 37, 39, 41, 42, 44, 47, 24, 25, 28, 29, 30}),
        black_men=frozenset({2, 36, 5, 8, 10, 11, 12, 13, 14, 15, 17, 18, 21, 26}),
        turn="white",
    ),
    concept='Partie 1981. Préview coup de la Trappe (chap 14 manuel).',
    published_notation='28-22 (18x38) 24-20 (15x24) 29x27',
    final_move=Move(
        path=(29, 20, 9, 18, 7, 16, 27),
        captures=(11, 12, 13, 14, 21, 24),
    ),
    explanation='28-22 sacrifice. (18x38) prise. 24-20 deuxième sacrifice. (15x24) prise. 29x27 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p52_d05',
    crop_id='crops/page_052_d05.png',
    confidence="high",
    claude_notes='Préview coup de la Trappe. Partie Clasquin-van Es (Alblasserdam 1981).',
)

BEG_CH12_006 = BeginnerPosition(
    id="BEG_CH12_006",
    theme="coup_renverse",
    title='Dubois ch16 D6 — Coup renversé pur',
    state=GameState(
        white_men=frozenset({32, 33, 35, 37, 38, 39, 43, 22, 27}),
        black_men=frozenset({12, 13, 16, 18, 19, 20, 23, 25, 26}),
        turn="white",
    ),
    concept='Un coup renversé canonique avec rafle finale 32x25.',
    published_notation='33-29 (23x34) 39x30 (25x34) 27-21 (26x28) 32x25',
    final_move=Move(
        path=(32, 23, 14, 25),
        captures=(19, 20, 28),
    ),
    explanation='33-29 sacrifice. (23x34) prise. 39x30 rafle. (25x34) prise. 27-21 sacrifice. (26x28) prise. 32x25 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p52_d06',
    crop_id='crops/page_052_d06.png',
    confidence="high",
)

BEG_CH12_007 = BeginnerPosition(
    id="BEG_CH12_007",
    theme="coup_renverse",
    title='Dubois ch16 D7 — Combinaison avec temps de repos',
    state=GameState(
        white_men=frozenset({32, 33, 34, 37, 38, 39, 24, 27, 28, 29}),
        black_men=frozenset({7, 9, 12, 13, 15, 16, 18, 19, 25, 26}),
        turn="white",
    ),
    concept='Pendant le temps de repos, les blancs adoptent la position caractéristique du coup renversé.',
    published_notation='28-22 (19x30) 29-24 (30x19) 27-21 (26x28) 32x3',
    final_move=Move(
        path=(32, 23, 14, 3),
        captures=(9, 19, 28),
    ),
    explanation='28-22 sacrifice. (19x30) prise. 29-24 temps de repos. (30x19) prise. 27-21 sacrifice. (26x28) prise. 32x3 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p52_d07',
    crop_id='crops/page_052_d07.png',
    confidence="high",
)

BEG_CH12_008 = BeginnerPosition(
    id="BEG_CH12_008",
    theme="coup_parallele",
    title='Dubois ch16 D8 — Coup parallèle (Bergsma-Spoelstra 1952)',
    state=GameState(
        white_men=frozenset({25, 26, 29, 31, 32, 36, 39, 42, 43, 44, 45, 46, 47, 48, 49, 50}),
        black_men=frozenset({1, 2, 3, 4, 6, 7, 8, 9, 10, 13, 15, 16, 17, 18, 19, 22}),
        turn="white",
    ),
    concept='Partie 1952. Mécanisme final connu sous le nom de coup parallèle. Notation (ad lib) — captures forcées équivalentes (cf §R008).',
    published_notation='26-21 (17x28) 29-23 (18x29) 39-33 43x5',
    final_move=None,
    explanation='26-21 sacrifice. (17x28) prise. 29-23 deuxième sacrifice. (18x29) prise. 39-33 troisième sacrifice. (ad lib) captures forcées. 43x5 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p52_d08',
    crop_id='crops/page_052_d08.png',
    confidence="high",
    claude_notes='Partie Bergsma-Spoelstra (Gezellig Samenzijn Paas, 14-04-1952). Contient un (ad lib), final_move=None pour cause de branches multiples.',
)

BEG_CH12_009 = BeginnerPosition(
    id="BEG_CH12_009",
    theme="coup_renverse",
    title='Dubois ch16 D9 — Coup renversé avec envoi à dame (Spoelstra-Bergsma 1972)',
    state=GameState(
        white_men=frozenset({36, 38, 39, 40, 42, 43, 44, 48, 50, 24, 28, 29, 31}),
        black_men=frozenset({2, 3, 4, 5, 6, 8, 12, 14, 15, 16, 17, 18, 21}),
        turn="black",
    ),
    concept='Partie 1972. Trait aux noirs. Combine coup renversé et envoi à dame du blanc.',
    published_notation='(15-20) 24x15 (4-10) 15x4 (18-22) 4x27 (21x45)',
    final_move=None,
    explanation='(15-20) sacrifice noir. 24x15 prise. (4-10) deuxième sacrifice. 15x4 prise (promotion blanche). (18-22) sacrifice. 4x27 rafle de dame blanche. (21x45) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p52_d09',
    crop_id='crops/page_052_d09.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Spoelstra-Bergsma (FRI-ch, 26-08-1972). Envoi à dame → final_move=None (R007).',
)

BEG_CH12_010 = BeginnerPosition(
    id="BEG_CH12_010",
    theme="coup_renverse",
    title='Dubois ch16 D10 — Combinaison fulgurante',
    state=GameState(
        white_men=frozenset({32, 33, 34, 38, 39, 47, 24, 27, 28}),
        black_men=frozenset({8, 9, 10, 13, 16, 17, 18, 19, 21}),
        turn="white",
    ),
    concept='Une combinaison traîtresse aboutissant à la dame en 5. Demande imagination pour identifier prise majoritaire + collage + renversé.',
    published_notation='28-22 (17x37) 47-41 (21x43) 39x48 (19x28) 41x5',
    final_move=Move(
        path=(41, 32, 23, 12, 3, 14, 5),
        captures=(8, 9, 10, 18, 28, 37),
    ),
    explanation='28-22 sacrifice. (17x37) prise. 47-41 deuxième sacrifice. (21x43) prise. 39x48 rafle. (19x28) prise. 41x5 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p52_d10',
    crop_id='crops/page_052_d10.png',
    confidence="high",
    claude_notes='Combinaison fulgurante à 5 demi-coups.',
)



# ============================================================================
# Chapitre 13 — Le coup Napoléon
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 17, pages 54-56.
#
# Le coup Napoléon est une combinaison à 4 sacrifices acheminant les pions
# adverses pour une rafle finale en 31x4, 39x8, 40x16 ou variantes.
# Il se rencontre sous différentes formes (D7 et D9 montrent les plus pures).

BEG_CH13_001 = BeginnerPosition(
    id="BEG_CH13_001",
    theme="coup_napoleon",
    title='Dubois ch17 D1 — Envoi à dame surprenant',
    state=GameState(
        white_men=frozenset({34, 36, 37, 38, 40, 42, 43, 45, 47, 30, 31}),
        black_men=frozenset({11, 13, 14, 15, 16, 17, 19, 22, 23, 26, 29}),
        turn="white",
    ),
    concept="L'envoi à dame intentionnel ouvre des perspectives surprenantes pour le coup Napoléon.",
    published_notation='38-33 (29x49) 31-27 (49x24) 27x18',
    final_move=None,
    explanation='38-33 sacrifice. (29x49) le noir promeut. 31-27 deuxième sacrifice. (49x24) la dame doit prendre. 27x18 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p55_d01',
    crop_id='crops/page_055_d01.png',
    confidence="high",
    claude_notes='⚠️ Envoi à dame du noir (rafle 49x24). final_move=None (R007).',
)

BEG_CH13_002 = BeginnerPosition(
    id="BEG_CH13_002",
    theme="coup_napoleon",
    title='Dubois ch17 D2 — Rafle 22x44 (Bom-van Dijk 1963)',
    state=GameState(
        white_men=frozenset({34, 35, 37, 38, 39, 40, 45, 47, 16, 49, 26}),
        black_men=frozenset({9, 11, 12, 13, 14, 15, 17, 19, 22, 23, 29}),
        turn="black",
    ),
    concept='Partie 1963. Trait aux noirs. Combinaison finissant en 44, exploitant prise majoritaire et collage.',
    published_notation='(23-28) 16x27 (17-22) 34x32 (22x44)',
    final_move=Move(
        path=(22, 31, 42, 33, 44),
        captures=(27, 37, 38, 39),
    ),
    explanation='(23-28) sacrifice noir. 16x27 prise. (17-22) deuxième sacrifice. 34x32 prise. (22x44) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p55_d02',
    crop_id='crops/page_055_d02.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Bom-van Dijk (NLD-ch, 1963).',
)

BEG_CH13_003 = BeginnerPosition(
    id="BEG_CH13_003",
    theme="coup_napoleon",
    title='Dubois ch17 D3 — Coup de dame en 46 (Baerends-Stoop 1984)',
    state=GameState(
        white_men=frozenset({26, 29, 31, 32, 33, 34, 35, 36, 38, 39, 40, 41, 42, 44, 45, 48, 49}),
        black_men=frozenset({2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 15, 16, 18, 19, 20, 22, 24}),
        turn="black",
    ),
    concept='Partie 1984. Trait aux noirs. Coup de dame en 46 par Napoléon.',
    published_notation='(24-30) 34x23 (22-27) 31x13 (8x46)',
    final_move=Move(
        path=(8, 19, 28, 37, 46),
        captures=(13, 23, 32, 41),
    ),
    explanation='(24-30) sacrifice noir. 34x23 prise. (22-27) deuxième sacrifice. 31x13 prise. (8x46) rafle noire finale (promotion).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p55_d03',
    crop_id='crops/page_055_d03.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Baerends-Stoop (Brunssum, 1984).',
)

BEG_CH13_004 = BeginnerPosition(
    id="BEG_CH13_004",
    theme="coup_express",
    title="Dubois ch17 D4 — Coup de l'Express (coquille PDF corrigée)",
    state=GameState(
        white_men=frozenset({32, 33, 34, 35, 37, 38, 39, 28, 30}),
        black_men=frozenset({9, 14, 15, 16, 17, 20, 21, 26, 27}),
        turn="white",
    ),
    concept="Coup de l'Express dans le chapitre Napoléon — illustre la parenté entre les mécanismes.",
    published_notation='28-22 (27x18) 37-31 (26x28) 33x4',
    final_move=Move(
        path=(33, 22, 13, 4),
        captures=(9, 18, 28),
    ),
    explanation="28-22 sacrifice blanc. (27x18) prise noire forcée 27→18 capturant 22. 37-31 deuxième sacrifice. (26x28) prise majoritaire noire 26→37→28 capturant 31 et 32. 33x4 rafle finale 33→22→13→4 capturant 9, 18, 28 (promotion en dame).",
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p55_d04',
    crop_id='crops/page_055_d04.png',
    confidence="high",
    claude_notes="✅ Coquille PDF Dubois corrigée. Le livre imprime '(18x27)' (les opérandes inversés) mais 18 est vide dans la position : c'est bien le pion noir en 27 qui prend le sacrifice en 22 et atterrit en 18, donc '(27x18)'. Inversion typographique départ↔arrivée. Validé par recherche exhaustive (1 unique solution) et confirmation utilisateur. Cf RESOLUTIONS §R011.",
)

BEG_CH13_005 = BeginnerPosition(
    id="BEG_CH13_005",
    theme="coup_napoleon",
    title='Dubois ch17 D5 — Schéma Napoléon (Haijtink-Scholte Lubberink 1994)',
    state=GameState(
        white_men=frozenset({34, 36, 37, 38, 39, 40, 44, 23, 24, 29}),
        black_men=frozenset({8, 9, 10, 11, 13, 14, 15, 17, 21, 27}),
        turn="white",
    ),
    concept='Partie 1994. La rafle finale dessine le schéma typique du coup Napoléon.',
    published_notation='38-32 (27x38) 23-18 (13x22) 24-19 (14x23) 29x7',
    final_move=Move(
        path=(29, 18, 27, 16, 7),
        captures=(11, 21, 22, 23),
    ),
    explanation='38-32 sacrifice. (27x38) prise. 23-18 deuxième sacrifice. (13x22) prise. 24-19 troisième sacrifice. (14x23) prise. 29x7 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p55_d05',
    crop_id='crops/page_055_d05.png',
    confidence="high",
    claude_notes='Partie Haijtink-Scholte Lubberink (NLD-chT Hoofdklasse, 1994).',
)

BEG_CH13_006 = BeginnerPosition(
    id="BEG_CH13_006",
    theme="coup_napoleon",
    title='Dubois ch17 D6 — Rappel + Napoléon (van Leijen-Schunselaar 1971)',
    state=GameState(
        white_men=frozenset({33, 35, 37, 38, 39, 42, 43, 47, 48, 49, 23, 25, 29, 30}),
        black_men=frozenset({2, 3, 4, 9, 11, 12, 13, 14, 15, 18, 21, 22, 26, 27}),
        turn="white",
    ),
    concept='Partie 1971. Combine coup de rappel et coup Napoléon.',
    published_notation='23-19 (14x34) 33-29 (34x23) 25-20 (15x24) 30x19',
    final_move=Move(
        path=(30, 19, 8, 17, 28, 19),
        captures=(12, 13, 22, 23, 24),
    ),
    explanation='23-19 sacrifice. (14x34) prise. 33-29 rappel. (34x23) prise. 25-20 sacrifice. (15x24) prise. 30x19 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p55_d06',
    crop_id='crops/page_055_d06.png',
    confidence="high",
    claude_notes='Partie van Leijen-Schunselaar (NLD-chT Hoofdklasse 1971).',
)

BEG_CH13_007 = BeginnerPosition(
    id="BEG_CH13_007",
    theme="coup_napoleon",
    title='Dubois ch17 D7 — Coup Napoléon pur',
    state=GameState(
        white_men=frozenset({32, 34, 35, 39, 44, 47, 22, 27}),
        black_men=frozenset({12, 13, 16, 19, 21, 23, 24, 25}),
        turn="white",
    ),
    concept='Un coup Napoléon canonique en 4 sacrifices puis rafle 39x8.',
    published_notation='22-18 (13x31) 32-28 (23x32) 34-29 (24x33) 39x8',
    final_move=Move(
        path=(39, 28, 37, 26, 17, 8),
        captures=(12, 21, 31, 32, 33),
    ),
    explanation='22-18 sacrifice. (13x31) prise. 32-28 deuxième sacrifice. (23x32) prise. 34-29 troisième sacrifice. (24x33) prise. 39x8 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p55_d07',
    crop_id='crops/page_055_d07.png',
    confidence="high",
    claude_notes='Coup Napoléon pur.',
)

BEG_CH13_008 = BeginnerPosition(
    id="BEG_CH13_008",
    theme="coup_napoleon",
    title='Dubois ch17 D8 — Coup Napoléon (Kolodiev-Weytsman 1973)',
    state=GameState(
        white_men=frozenset({32, 34, 29, 40, 24, 42, 45}),
        black_men=frozenset({18, 21, 23, 8, 25, 10, 13}),
        turn="white",
    ),
    concept='Partie URSS 1973. Coup Napoléon en 4 sacrifices.',
    published_notation='32-28 (23x32) 24-19 (13x33) 34-30 (25x34) 40x16',
    final_move=Move(
        path=(40, 29, 38, 27, 16),
        captures=(21, 32, 33, 34),
    ),
    explanation='32-28 sacrifice. (23x32) prise. 24-19 deuxième sacrifice. (13x33) prise. 34-30 troisième sacrifice. (25x34) prise. 40x16 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p55_d08',
    crop_id='crops/page_055_d08.png',
    confidence="high",
    claude_notes='Partie Kolodiev-Weytsman (URS-ch, 1973).',
)

BEG_CH13_009 = BeginnerPosition(
    id="BEG_CH13_009",
    theme="coup_napoleon",
    title='Dubois ch17 D9 — Pur coup Napoléon',
    state=GameState(
        white_men=frozenset({32, 33, 35, 36, 37, 39, 44, 45, 25, 26, 27, 28, 31}),
        black_men=frozenset({6, 8, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 23}),
        turn="white",
    ),
    concept='« Un pur coup Napoléon » selon Dubois — 4 sacrifices puis rafle 31x4.',
    published_notation='27-22 (18x29) 28-22 (17x28) 26-21 (16x27) 31x4',
    final_move=Move(
        path=(31, 22, 33, 24, 15, 4),
        captures=(10, 20, 27, 28, 29),
    ),
    explanation='27-22 sacrifice. (18x29) prise. 28-22 deuxième sacrifice. (17x28) prise. 26-21 troisième sacrifice. (16x27) prise. 31x4 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p55_d09',
    crop_id='crops/page_055_d09.png',
    confidence="high",
    claude_notes='Forme canonique du coup Napoléon.',
)

BEG_CH13_010 = BeginnerPosition(
    id="BEG_CH13_010",
    theme="coup_napoleon",
    title='Dubois ch17 D10 — Rafle 48x6 (Papinski-Lewandowski 1979)',
    state=GameState(
        white_men=frozenset({32, 34, 35, 37, 38, 41, 42, 45, 47, 48, 49, 27, 28}),
        black_men=frozenset({2, 7, 9, 11, 12, 13, 15, 16, 17, 18, 21, 24, 25}),
        turn="white",
    ),
    concept='Partie 1979. Une rafle 48x6 ouverte par sacrifices successifs.',
    published_notation='34-30 (25x34) 28-22 (17x28) 32x23 (21x43) 48x6',
    final_move=Move(
        path=(48, 39, 30, 19, 8, 17, 6),
        captures=(11, 12, 13, 24, 34, 43),
    ),
    explanation='34-30 sacrifice. (25x34) prise. 28-22 sacrifice. (17x28) prise. 32x23 rafle. (21x43) prise. 48x6 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p55_d10',
    crop_id='crops/page_055_d10.png',
    confidence="high",
    claude_notes='Partie Papinski-Lewandowski (Poczesna, 1979).',
)



# ============================================================================
# Chapitre 14 — Le coup de la Trappe
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 18, pages 57-59.
#
# Le coup de la Trappe est un mécanisme sophistiqué : un sacrifice
# préliminaire « piège » un pion adverse, qui se trouve dans une position
# où sa capture forcée par un sacrifice subséquent ouvre la rafle finale.
# Demande une grande vigilance pour le voir venir.

BEG_CH14_001 = BeginnerPosition(
    id="BEG_CH14_001",
    theme="coup_de_trappe",
    title='Dubois ch18 D1 — Rafle 30x6',
    state=GameState(
        white_men=frozenset({32, 34, 35, 36, 37, 38, 40, 45, 48, 26, 29, 30}),
        black_men=frozenset({9, 11, 12, 13, 14, 15, 17, 18, 20, 22, 23, 25}),
        turn="white",
    ),
    concept='Une rafle se terminant en 6 avec le pion 30 pour le départ.',
    published_notation='26-21 (17x26) 32-27 (22x24) 30x6',
    final_move=Move(
        path=(30, 19, 8, 17, 6),
        captures=(11, 12, 13, 24),
    ),
    explanation='26-21 sacrifice. (17x26) prise. 32-27 deuxième sacrifice. (22x24) prise. 30x6 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p58_d01',
    crop_id='crops/page_058_d01.png',
    confidence="high",
)

BEG_CH14_002 = BeginnerPosition(
    id="BEG_CH14_002",
    theme="coup_rappel",
    title='Dubois ch18 D2 — Coup de Rappel (révision)',
    state=GameState(
        white_men=frozenset({32, 33, 35, 37, 38, 49, 27, 28}),
        black_men=frozenset({8, 9, 13, 16, 18, 19, 24, 26}),
        turn="white",
    ),
    concept='Révision du coup de Rappel dans le chapitre Trappe.',
    published_notation='28-23 (19x39) 38-33 (39x28) 32x14',
    final_move=Move(
        path=(32, 23, 12, 3, 14),
        captures=(8, 9, 18, 28),
    ),
    explanation='28-23 (19x39) 38-33 (39x28) 32x14 — schéma typique Rappel.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p58_d02',
    crop_id='crops/page_058_d02.png',
    confidence="high",
    claude_notes='Révision du coup de Rappel.',
)

BEG_CH14_003 = BeginnerPosition(
    id="BEG_CH14_003",
    theme="coup_de_trappe",
    title='Dubois ch18 D3 — Rafle finale en 9',
    state=GameState(
        white_men=frozenset({33, 36, 37, 38, 39, 44, 22, 28, 29}),
        black_men=frozenset({6, 11, 12, 13, 15, 17, 20, 21, 24}),
        turn="white",
    ),
    concept="La rafle ne peut aboutir qu'en 9. Case de départ : 36.",
    published_notation='28-23 (17x19) 33-28 (24x31) 36x9',
    final_move=Move(
        path=(36, 27, 16, 7, 18, 9),
        captures=(11, 12, 13, 21, 31),
    ),
    explanation='28-23 sacrifice. (17x19) prise. 33-28 deuxième sacrifice. (24x31) prise. 36x9 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p58_d03',
    crop_id='crops/page_058_d03.png',
    confidence="high",
)

BEG_CH14_004 = BeginnerPosition(
    id="BEG_CH14_004",
    theme="coup_de_trappe",
    title='Dubois ch18 D4 — Trappe avec rafle 23x45 (Kocken-Doomernik 1971)',
    state=GameState(
        white_men=frozenset({32, 35, 37, 38, 39, 40, 46, 48, 22, 25, 27, 28, 30}),
        black_men=frozenset({8, 11, 12, 13, 14, 15, 16, 18, 19, 23, 24, 26, 29}),
        turn="black",
    ),
    concept='Partie 1971. Trait aux noirs. Un genre de coup de la trappe terminé par 23x45.',
    published_notation='(16-21) 27x7 (18x27) 7x20 (8-12) 32x21 (23x45)',
    final_move=Move(
        path=(23, 32, 43, 34, 45),
        captures=(28, 38, 39, 40),
    ),
    explanation='(16-21) sacrifice. 27x7 prise. (18x27) deuxième sacrifice. 7x20 rafle blanche. (8-12) sacrifice. 32x21 prise. (23x45) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p58_d04',
    crop_id='crops/page_058_d04.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Kocken-Doomernik (Archief Kocken, 1971). 7 demi-coups.',
)

BEG_CH14_005 = BeginnerPosition(
    id="BEG_CH14_005",
    theme="coup_de_trappe",
    title='Dubois ch18 D5 — Coup de dame à 4 (Hoogland-van den Broek 1912)',
    state=GameState(
        white_men=frozenset({33, 34, 35, 38, 41, 42, 43, 47, 48, 25, 26, 28, 29, 30}),
        black_men=frozenset({5, 8, 10, 11, 12, 13, 14, 17, 18, 19, 20, 22, 24, 27}),
        turn="white",
    ),
    concept='Partie 1912. Coup de dame à 4 via trappe (case vide en 39).',
    published_notation='28-23 (19x39) 30x19 (13x33) 38x29 (39x30) 35x4',
    final_move=Move(
        path=(35, 24, 15, 4),
        captures=(10, 20, 30),
    ),
    explanation='28-23 sacrifice. (19x39) prise. 30x19 rafle. (13x33) prise. 38x29 rafle. (39x30) prise. 35x4 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p58_d05',
    crop_id='crops/page_058_d05.png',
    confidence="high",
    claude_notes='Partie Hoogland-van den Broek (Wch, 1912). 7 demi-coups.',
)

BEG_CH14_006 = BeginnerPosition(
    id="BEG_CH14_006",
    theme="coup_de_trappe",
    title='Dubois ch18 D6 — Pur coup de la Trappe',
    state=GameState(
        white_men=frozenset({32, 34, 35, 37, 38, 39, 42, 48, 25, 26, 30, 31}),
        black_men=frozenset({9, 11, 12, 14, 15, 16, 18, 19, 22, 23, 24, 28}),
        turn="white",
    ),
    concept='Un pur coup de la Trappe avec rafle finale 42x4.',
    published_notation='31-27 (22x31) 26-21 (16x27) 37x26 (28x37) 42x4',
    final_move=Move(
        path=(42, 31, 22, 13, 4),
        captures=(9, 18, 27, 37),
    ),
    explanation='31-27 sacrifice. (22x31) prise. 26-21 sacrifice. (16x27) prise. 37x26 rafle. (28x37) prise. 42x4 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p58_d06',
    crop_id='crops/page_058_d06.png',
    confidence="high",
    claude_notes='Forme canonique du coup de la Trappe.',
)

BEG_CH14_007 = BeginnerPosition(
    id="BEG_CH14_007",
    theme="coup_de_trappe",
    title='Dubois ch18 D7 — Trappe à 5 (Maertzdorf-Alofs 1997)',
    state=GameState(
        white_men=frozenset({27, 28, 29, 31, 32, 33, 35, 36, 39, 41, 43, 44, 45, 46, 47, 48, 49, 50}),
        black_men=frozenset({2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 22}),
        turn="white",
    ),
    concept='Partie 1997. Coup de dame à 5 par trappe (cases vides 37, 38).',
    published_notation='29-24 (20x38) 39-34 (22x33) 27-21 (17x28) 43x5',
    final_move=Move(
        path=(43, 32, 23, 14, 5),
        captures=(10, 19, 28, 38),
    ),
    explanation='29-24 sacrifice. (20x38) prise. 39-34 sacrifice. (22x33) prise. 27-21 sacrifice. (17x28) prise. 43x5 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p58_d07',
    crop_id='crops/page_058_d07.png',
    confidence="high",
    claude_notes='Partie Maertzdorf-Alofs (NLD-chT 2e klasse D, 1997).',
)

BEG_CH14_008 = BeginnerPosition(
    id="BEG_CH14_008",
    theme="coup_de_trappe",
    title='Dubois ch18 D8 — Trappe noire (Bronstring-Holstvoogd 2005)',
    state=GameState(
        white_men=frozenset({33, 34, 36, 37, 38, 40, 42, 22, 27, 28, 29}),
        black_men=frozenset({1, 4, 11, 13, 14, 16, 18, 19, 20, 25, 26}),
        turn="black",
    ),
    concept='Partie 2005. Trait aux noirs. Le pion 50 sert de base à la rafle. Case vide 42 autorise une trappe.',
    published_notation='(20-24) 29x9 (16-21) 27x7 (18x27) 9x18 (1x43)',
    final_move=Move(
        path=(1, 12, 23, 32, 43),
        captures=(7, 18, 28, 38),
    ),
    explanation='(20-24) sacrifice. 29x9 prise. (16-21) deuxième sacrifice. 27x7 prise. (18x27) sacrifice. 9x18 rafle. (1x43) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p58_d08',
    crop_id='crops/page_058_d08.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Bronstring-Holstvoogd (Den Haag, 2005). 7 demi-coups.',
)

BEG_CH14_009 = BeginnerPosition(
    id="BEG_CH14_009",
    theme="coup_de_trappe",
    title='Dubois ch18 D9 — Mécanisme inattendu (van Dijk)',
    state=GameState(
        white_men=frozenset({33, 34, 38, 39, 43, 47, 28, 29, 31}),
        black_men=frozenset({11, 12, 13, 15, 17, 18, 20, 21, 25}),
        turn="white",
    ),
    concept='Combinaison envisagée en partie par Jan van Dijk. Mécanisme inattendu, rafle finale en 9, départ obligé en 38.',
    published_notation='28-22 (18x36) 34-30 (25x23) 33-28 (23x32) 38x9',
    final_move=Move(
        path=(38, 27, 16, 7, 18, 9),
        captures=(11, 12, 13, 21, 32),
    ),
    explanation='28-22 sacrifice. (18x36) prise. 34-30 deuxième sacrifice. (25x23) prise. 33-28 troisième sacrifice. (23x32) prise. 38x9 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p58_d09',
    crop_id='crops/page_058_d09.png',
    confidence="high",
)

BEG_CH14_010 = BeginnerPosition(
    id="BEG_CH14_010",
    theme="coup_de_trappe",
    title='Dubois ch18 D10 — Envoi à dame + ricochet (Kats-Agafonov 1965)',
    state=GameState(
        white_men=frozenset({36, 37, 38, 39, 40, 42, 44, 45, 23, 27, 28}),
        black_men=frozenset({4, 9, 12, 13, 14, 16, 17, 19, 24, 25, 26}),
        turn="black",
    ),
    concept='Partie URSS 1965. Trait aux noirs. Combine envoi à dame et coup de ricochet.',
    published_notation='(14-20) 23x3 (17-21) 3x17 (21x34) 40x29 (24x11)',
    final_move=None,
    explanation='(14-20) sacrifice. 23x3 prise (promotion blanche). (17-21) sacrifice. 3x17 rafle dame. (21x34) prise. 40x29 rafle. (24x11) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p58_d10',
    crop_id='crops/page_058_d10.png',
    confidence="high",
    claude_notes='Trait aux noirs. Contient une rafle de dame (3x17). final_move=None (R007). Partie Kats-Agafonov (URS-ch, 1965).',
)



# ============================================================================
# Chapitre 15 — Le coup de Talon
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 19, pages 60-62.
#
# Le coup de Talon est un mécanisme surprenant qui ne dévoile le point
# d'appui de la rafle qu'au dernier moment. Il se combine fréquemment
# avec le coup de la Trappe (D6, D7, D8, D9 dans Dubois).

BEG_CH15_001 = BeginnerPosition(
    id="BEG_CH15_001",
    theme="coup_de_talon",
    title='Dubois ch19 D1 — Coup de mazette dans le coup de Talon',
    state=GameState(
        white_men=frozenset({32, 33, 34, 36, 37, 38, 40, 44, 24, 27, 28, 29}),
        black_men=frozenset({2, 8, 10, 13, 15, 16, 17, 19, 20, 21, 25, 26}),
        turn="white",
    ),
    concept="Combinaison inattendue à mécanisme de coup de mazette. Coup de talon dévoile le point d'appui en dernier.",
    published_notation='28-23 (19x19) 27-22 (17x28) 32x5',
    final_move=Move(
        path=(32, 23, 14, 5),
        captures=(10, 19, 28),
    ),
    explanation='28-23 sacrifice. (19x?) prise. 27-22 deuxième sacrifice. (17x28) prise. 32x5 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p61_d01',
    crop_id='crops/page_061_d01.png',
    confidence="high",
    claude_notes='Coup de mazette + talon. Note : la notation Dubois indique (19x19) — probable typo PDF.',
)

BEG_CH15_002 = BeginnerPosition(
    id="BEG_CH15_002",
    theme="coup_de_talon",
    title='Dubois ch19 D2 — Rafle aboutissant en 7',
    state=GameState(
        white_men=frozenset({33, 34, 36, 38, 39, 41, 23, 24, 29}),
        black_men=frozenset({8, 9, 11, 15, 17, 20, 21, 22, 25}),
        turn="white",
    ),
    concept='Combinaison aboutissant sur la case 7.',
    published_notation='34-30 (25x32) 33-28 (22x33) 29x7',
    final_move=Move(
        path=(29, 38, 27, 16, 7),
        captures=(11, 21, 32, 33),
    ),
    explanation='34-30 sacrifice. (25x32) prise. 33-28 deuxième sacrifice. (22x33) prise. 29x7 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p61_d02',
    crop_id='crops/page_061_d02.png',
    confidence="high",
)

BEG_CH15_003 = BeginnerPosition(
    id="BEG_CH15_003",
    theme="coup_de_talon",
    title='Dubois ch19 D3 — Rafle 50x8 (Lewkowicz-Blokland 1998)',
    state=GameState(
        white_men=frozenset({32, 33, 34, 41, 44, 48, 50, 26, 27, 29}),
        black_men=frozenset({35, 6, 9, 13, 15, 16, 18, 20, 23, 24}),
        turn="white",
    ),
    concept='Partie 1998. La rafle 50x8 est la plus vraisemblable. Le pion 24 est amené en 33 par le coup de talon.',
    published_notation='27-21 (16x38) 33x42 (24x33) 44-40 (35x44) 50x8',
    final_move=Move(
        path=(50, 39, 28, 19, 8),
        captures=(13, 23, 33, 44),
    ),
    explanation='27-21 sacrifice. (16x38) prise. 33x42 rafle. (24x33) prise. 44-40 sacrifice. (35x44) prise. 50x8 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p61_d03',
    crop_id='crops/page_061_d03.png',
    confidence="high",
    claude_notes='Partie Lewkowicz-Blokland (NLD-chT 2e klasse D - 1998).',
)

BEG_CH15_004 = BeginnerPosition(
    id="BEG_CH15_004",
    theme="coup_de_talon",
    title='Dubois ch19 D4 — Coup de dame à 3 par talon pur',
    state=GameState(
        white_men=frozenset({32, 33, 34, 35, 37, 39, 44, 22, 27, 28}),
        black_men=frozenset({8, 11, 13, 16, 17, 18, 19, 23, 24, 25}),
        turn="white",
    ),
    concept='Coup de dame à 3 reposant sur un pur coup de talon.',
    published_notation='34-29 (23x43) 33-29 (24x33) 28x48 (17x28) 32x3',
    final_move=Move(
        path=(32, 23, 12, 3),
        captures=(8, 18, 28),
    ),
    explanation='34-29 sacrifice. (23x43) prise. 33-29 deuxième sacrifice. (24x33) prise. 28x48 rafle. (17x28) prise. 32x3 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p61_d04',
    crop_id='crops/page_061_d04.png',
    confidence="high",
    claude_notes='Pur coup de talon.',
)

BEG_CH15_005 = BeginnerPosition(
    id="BEG_CH15_005",
    theme="coup_de_talon",
    title='Dubois ch19 D5 — Coup de dame à 1 par talon pur',
    state=GameState(
        white_men=frozenset({32, 33, 34, 36, 38, 40, 45, 47, 24, 29}),
        black_men=frozenset({7, 13, 15, 16, 18, 20, 21, 22, 23, 25}),
        turn="white",
    ),
    concept='Coup de dame à 1 reposant sur un pur coup de talon.',
    published_notation='32-28 (23x43) 33-28 (22x33) 29x49 (20x29) 34x1',
    final_move=Move(
        path=(34, 23, 12, 1),
        captures=(7, 18, 29),
    ),
    explanation='32-28 sacrifice. (23x43) prise. 33-28 deuxième sacrifice. (22x33) prise. 29x49 rafle. (20x29) prise. 34x1 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p61_d05',
    crop_id='crops/page_061_d05.png',
    confidence="high",
    claude_notes='Pur coup de talon, symétrique du D4.',
)

BEG_CH15_006 = BeginnerPosition(
    id="BEG_CH15_006",
    theme="coup_de_talon",
    title='Dubois ch19 D6 — Talon + Trappe (Vatutin-Steijlen 2007)',
    state=GameState(
        white_men=frozenset({33, 38, 40, 44, 48, 50, 21, 23, 26, 28}),
        black_men=frozenset({2, 35, 7, 9, 12, 14, 15, 17, 24, 25}),
        turn="white",
    ),
    concept='Partie 2007. Coup de dame à 1 par rafle préalable 50x10 + trappe.',
    published_notation='44-39 (35x44) 23-18 (12x34) 50x10 (15x4) 21x1',
    final_move=Move(
        path=(21, 12, 1),
        captures=(7, 17),
    ),
    explanation='44-39 sacrifice. (35x44) prise. 23-18 deuxième sacrifice. (12x34) prise. 50x10 rafle. (15x4) prise. 21x1 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p61_d06',
    crop_id='crops/page_061_d06.png',
    confidence="high",
    claude_notes='Partie Vatutin-Steijlen (NLD-chT Ereklasse, 2007).',
)

BEG_CH15_007 = BeginnerPosition(
    id="BEG_CH15_007",
    theme="coup_de_talon",
    title='Dubois ch19 D7 — Trappe cachée (Wiering-Sier 2008)',
    state=GameState(
        white_men=frozenset({34, 37, 38, 43, 16, 22, 27, 28}),
        black_men=frozenset({1, 35, 7, 11, 13, 17, 18, 19}),
        turn="black",
    ),
    concept='Partie 2008. Trait aux noirs. La rafle 1x41 saute aux yeux mais le coup de la trappe qui y mène est dissimulé.',
    published_notation='(7-12) 16x7 (19-23) 28x8 (17x28) 8x17 (1x41)',
    final_move=Move(
        path=(1, 12, 21, 32, 41),
        captures=(7, 17, 27, 37),
    ),
    explanation='(7-12) sacrifice. 16x7 prise. (19-23) deuxième sacrifice. 28x8 rafle. (17x28) prise. 8x17 rafle. (1x41) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p61_d07',
    crop_id='crops/page_061_d07.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Wiering-Sier (NLD-chT Ereklasse, 2008). 7 demi-coups.',
)

BEG_CH15_008 = BeginnerPosition(
    id="BEG_CH15_008",
    theme="coup_de_talon",
    title='Dubois ch19 D8 — Combinaison cachée (Depaepe-Groenendijk 2014)',
    state=GameState(
        white_men=frozenset({33, 35, 37, 40, 42, 43, 47, 16, 48, 49, 25, 27, 30}),
        black_men=frozenset({1, 3, 36, 7, 9, 11, 13, 14, 15, 18, 19, 23, 24}),
        turn="black",
    ),
    concept="Partie 2014. Trait aux noirs. La rafle 1x41 et le moyen d'amener un pion en 17 reposent sur trappe + prise majoritaire.",
    published_notation='(7-12) 16x7 (14-20) 25x14 (19x10) 30x17 (1x41)',
    final_move=Move(
        path=(1, 12, 21, 32, 41),
        captures=(7, 17, 27, 37),
    ),
    explanation='(7-12) sacrifice. 16x7 prise. (14-20) deuxième sacrifice. 25x14 prise. (19x10) rafle. 30x17 prise. (1x41) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p61_d08',
    crop_id='crops/page_061_d08.png',
    confidence="high",
    claude_notes='Trait aux noirs. Partie Depaepe-Groenendijk (Hoogeveen open, 2014). 7 demi-coups.',
)

BEG_CH15_009 = BeginnerPosition(
    id="BEG_CH15_009",
    theme="coup_de_talon",
    title='Dubois ch19 D9 — Pur coup de la Trappe',
    state=GameState(
        white_men=frozenset({32, 37, 38, 39, 42, 47, 23, 24, 29}),
        black_men=frozenset({36, 12, 13, 14, 15, 16, 17, 21, 25}),
        turn="white",
    ),
    concept='Un pur coup de la Trappe avec rafle 29x7.',
    published_notation='37-31 (36x27) 38-33 (27x38) 24-20 (15x24) 29x7',
    final_move=Move(
        path=(29, 20, 9, 18, 7),
        captures=(12, 13, 14, 24),
    ),
    explanation='37-31 sacrifice. (36x27) prise. 38-33 deuxième sacrifice. (27x38) prise. 24-20 troisième sacrifice. (15x24) prise. 29x7 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p61_d09',
    crop_id='crops/page_061_d09.png',
    confidence="high",
)

BEG_CH15_010 = BeginnerPosition(
    id="BEG_CH15_010",
    theme="coup_de_talon",
    title='Dubois ch19 D10 — Coup de Talon final (de Jongh-Bizot 1927)',
    state=GameState(
        white_men=frozenset({32, 35, 36, 38, 39, 40, 42, 45, 48, 49, 25, 31}),
        black_men=frozenset({3, 6, 9, 11, 12, 13, 14, 16, 21, 23, 24, 29}),
        turn="white",
    ),
    concept='Partie 1927. Combinaison inattendue. La bonne case de départ est 26, par mécanisme de la trappe.',
    published_notation='35-30 (24x33) 42-37 (33x42) 31-26 (42x31) 26x10',
    final_move=Move(
        path=(26, 17, 8, 19, 10),
        captures=(12, 13, 14, 21),
    ),
    explanation='35-30 sacrifice. (24x33) prise. 42-37 deuxième sacrifice. (33x42) prise. 31-26 troisième sacrifice. (42x31) prise. 26x10 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p61_d10',
    crop_id='crops/page_061_d10.png',
    confidence="high",
    claude_notes='Partie de Jongh-Bizot (Parijs, 1927).',
)



# ============================================================================
# Chapitre 16 — Le coup Philippe
# ============================================================================
# Source : Dubois Apprentissage Combinaisons, chapitre 20, pages 63-65.
#
# Le coup Philippe est l'un des mécanismes les plus simples et les mieux
# connus de la littérature combinatoire. Il a déjà été abordé en passant
# (chap 6 D1 du manuel = forme la plus élémentaire). Ce chapitre final
# l'étudie sous ses formes plus complètes, avec partenariats fréquents
# avec d'autres coups nommés (coup de mazette D7, coup turc D1).

BEG_CH16_001 = BeginnerPosition(
    id="BEG_CH16_001",
    theme="coup_philippe",
    title='Dubois ch20 D1 — Coup turc avec envoi à dame',
    state=GameState(
        white_men=frozenset({32, 37, 38, 39, 42, 44, 47, 25, 27, 28}),
        black_men=frozenset({8, 12, 13, 14, 16, 17, 19, 23, 24, 26}),
        turn="white",
    ),
    concept='La dernière combinaison à 3 temps. Un coup turc combiné à un envoi à dame.',
    published_notation='37-31 (26x48) 47-41 (48x33) 38x29',
    final_move=None,
    explanation='37-31 sacrifice. (26x48) envoi à dame noir. 47-41 sacrifice. (48x33) rafle de dame forcée. 38x29 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p64_d01',
    crop_id='crops/page_064_d01.png',
    confidence="high",
    claude_notes='⚠️ Contient un envoi à dame du noir avec rafle de dame (48x33). final_move=None (R007).',
)

BEG_CH16_002 = BeginnerPosition(
    id="BEG_CH16_002",
    theme="coup_philippe",
    title='Dubois ch20 D2 — Coup Philippe (Dartelen-Ligthart 1938)',
    state=GameState(
        white_men=frozenset({29, 31, 33, 34, 35, 36, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49}),
        black_men=frozenset({1, 2, 3, 4, 6, 8, 9, 10, 11, 12, 13, 14, 15, 18, 20, 22, 23, 25, 27}),
        turn="white",
    ),
    concept='Partie historique 1938. Avec 2 pions noirs en 23 et 25, on pense au coup Philippe. Il faut faire sauter le pion 18 pour la rafle 40x16.',
    published_notation='33-28 (22x24) 31x22 (18x27) 34-30 (25x34) 40x16',
    final_move=Move(
        path=(40, 29, 18, 7, 16),
        captures=(11, 12, 23, 34),
    ),
    explanation='33-28 sacrifice. (22x24) prise. 31x22 rafle. (18x27) prise. 34-30 sacrifice. (25x34) prise. 40x16 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p64_d02',
    crop_id='crops/page_064_d02.png',
    confidence="high",
    claude_notes='Partie Dartelen-Ligthart (NLD-ch, 1938).',
)

BEG_CH16_003 = BeginnerPosition(
    id="BEG_CH16_003",
    theme="coup_philippe",
    title='Dubois ch20 D3 — Variante coup Philippe',
    state=GameState(
        white_men=frozenset({32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 45, 48}),
        black_men=frozenset({3, 6, 8, 11, 12, 13, 15, 18, 19, 23, 24, 25, 26}),
        turn="white",
    ),
    concept='Même schéma que D2 avec sacrifice initial 37-31 au lieu de 33-28. Présence simultanée des pions 23 et 25.',
    published_notation='37-31 (26x28) 33x22 (18x27) 34-30 (25x34) 40x16',
    final_move=Move(
        path=(40, 29, 18, 7, 16),
        captures=(11, 12, 23, 34),
    ),
    explanation='37-31 sacrifice. (26x28) prise. 33x22 rafle. (18x27) prise. 34-30 sacrifice. (25x34) prise. 40x16 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p64_d03',
    crop_id='crops/page_064_d03.png',
    confidence="high",
)

BEG_CH16_004 = BeginnerPosition(
    id="BEG_CH16_004",
    theme="coup_philippe",
    title='Dubois ch20 D4 — Schéma Philippe via attaque noire (Davidov-Romanov 1963)',
    state=GameState(
        white_men=frozenset({27, 28, 31, 34, 35, 36, 37, 38, 39, 40, 41, 43, 44, 45, 47, 48, 49}),
        black_men=frozenset({1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15, 16, 19, 21, 24, 25}),
        turn="white",
    ),
    concept="Partie URSS 1963. L'attaque noire permet de retrouver le schéma du coup Philippe.",
    published_notation='31-26 (21x23) 26-21 (16x27) 34-30 (25x34) 40x16',
    final_move=Move(
        path=(40, 29, 18, 7, 16),
        captures=(11, 12, 23, 34),
    ),
    explanation='31-26 sacrifice. (21x23) prise. 26-21 deuxième sacrifice. (16x27) prise. 34-30 sacrifice. (25x34) prise. 40x16 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p64_d04',
    crop_id='crops/page_064_d04.png',
    confidence="high",
    claude_notes='Partie Davidov-Romanov (URS-chT, 1963).',
)

BEG_CH16_005 = BeginnerPosition(
    id="BEG_CH16_005",
    theme="coup_philippe",
    title='Dubois ch20 D5 — Coup Philippe avec ruse',
    state=GameState(
        white_men=frozenset({32, 33, 38, 39, 42, 43, 44, 48, 26, 28, 29}),
        black_men=frozenset({35, 8, 12, 13, 14, 15, 16, 17, 19, 21, 22}),
        turn="white",
    ),
    concept='La rafle se termine sur la case 7 avec départ en 38. Piège : 29-24 (19x30) 32-27 (21x23) 33-28 (ad lib) ne marche pas (4 pions en 20). Il faut trouver une autre idée.',
    published_notation='32-27 (21x34) 39x30 (35x24) 33-28 (22x33) 38x7',
    final_move=Move(
        path=(38, 29, 20, 9, 18, 7),
        captures=(12, 13, 14, 24, 33),
    ),
    explanation='32-27 sacrifice. (21x34) prise. 39x30 rafle. (35x24) prise. 33-28 sacrifice. (22x33) prise. 38x7 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p64_d05',
    crop_id='crops/page_064_d05.png',
    confidence="high",
    claude_notes='Combinaison piégeuse — la voie évidente échoue.',
)

BEG_CH16_006 = BeginnerPosition(
    id="BEG_CH16_006",
    theme="coup_philippe",
    title='Dubois ch20 D6 — Rafle 48x26 (Leijenaar-Romanskaia 2003)',
    state=GameState(
        white_men=frozenset({32, 33, 34, 35, 36, 38, 41, 42, 44, 47, 48, 49, 50, 29}),
        black_men=frozenset({1, 2, 3, 4, 6, 12, 13, 15, 18, 21, 22, 23, 25, 27}),
        turn="white",
    ),
    concept='Partie Olympiade junior 2003. Avec tous les trous, il existe forcément un moyen de tourner.',
    published_notation='33-28 (22x24) 34-30 (25x34) 32-28 (23x43) 48x26',
    final_move=Move(
        path=(48, 39, 30, 19, 8, 17, 26),
        captures=(12, 13, 21, 24, 34, 43),
    ),
    explanation='33-28 sacrifice. (22x24) prise. 34-30 sacrifice. (25x34) prise. 32-28 sacrifice. (23x43) prise. 48x26 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p64_d06',
    crop_id='crops/page_064_d06.png',
    confidence="high",
    claude_notes='Partie Leijenaar-Romanskaia (Olympiade jr, 2003).',
)

BEG_CH16_007 = BeginnerPosition(
    id="BEG_CH16_007",
    theme="coup_de_mazette",
    title='Dubois ch20 D7 — Coup de Mazette classique',
    state=GameState(
        white_men=frozenset({32, 35, 36, 37, 38, 39, 40, 42, 43, 45, 48, 25, 27, 28, 30}),
        black_men=frozenset({2, 3, 6, 7, 9, 10, 12, 13, 14, 16, 17, 19, 23, 24, 26}),
        turn="white",
    ),
    concept='Coup de mazette classique. À retenir : la prise forcée (13x31) libère la rafle 32x5.',
    published_notation='28-22 (17x28) 25-20 (14x34) 40x18 (13x31) 32x5',
    final_move=Move(
        path=(32, 23, 14, 5),
        captures=(10, 19, 28),
    ),
    explanation='28-22 sacrifice. (17x28) prise. 25-20 sacrifice. (14x34) prise majoritaire. 40x18 rafle. (13x31) prise forcée. 32x5 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p64_d07',
    crop_id='crops/page_064_d07.png',
    confidence="high",
    claude_notes='Coup de mazette — autre coup nommé que Dubois introduit ici.',
)

BEG_CH16_008 = BeginnerPosition(
    id="BEG_CH16_008",
    theme="coup_philippe",
    title='Dubois ch20 D8 — Envoi à dame avec temps de réserve (Merin-Agafonow 1975)',
    state=GameState(
        white_men=frozenset({36, 38, 39, 40, 42, 44, 45, 49, 24, 27, 29, 31}),
        black_men=frozenset({2, 8, 9, 10, 13, 14, 15, 16, 17, 20, 22, 25}),
        turn="black",
    ),
    concept='Partie URSS 1975. Trait aux noirs. Solution : envoi à dame qui procure un temps de réserve. (12x32) ou (21x23) sont les seules rafles utilisables.',
    published_notation='(14-19) 27x18 (13x22) 24x4 (17-21) 4x27 (21x23)',
    final_move=None,
    explanation='(14-19) sacrifice noir. 27x18 prise. (13x22) deuxième sacrifice. 24x4 rafle (promotion blanche). (17-21) sacrifice. 4x27 rafle de dame blanche. (21x23) rafle noire finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p64_d08',
    crop_id='crops/page_064_d08.png',
    confidence="high",
    claude_notes='Trait aux noirs. Envoi à dame blanc avec rafle de dame (4x27). final_move=None (R007). Partie Merin-Agafonow (URS-ch, 1975).',
)

BEG_CH16_009 = BeginnerPosition(
    id="BEG_CH16_009",
    theme="coup_philippe",
    title='Dubois ch20 D9 — Visualisation 32-28',
    state=GameState(
        white_men=frozenset({32, 33, 34, 35, 36, 38, 40, 43, 45, 25, 26, 30}),
        black_men=frozenset({3, 6, 12, 13, 14, 16, 18, 19, 22, 23, 24, 29}),
        turn="white",
    ),
    concept='Pas de vraie méthode pour trouver la solution. Il faut visualiser mentalement les conséquences de 32-28.',
    published_notation='34x23 (19x48) 30x37 (48x31) 36x27',
    final_move=None,
    explanation='34x23 sacrifice. (19x48) envoi à dame noir. 30x37 rafle. (48x31) rafle de dame forcée. 36x27 rafle finale.',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p64_d09',
    crop_id='crops/page_064_d09.png',
    confidence="high",
    claude_notes='⚠️ Envoi à dame noir avec rafle de dame (48x31). final_move=None (R007).',
)

BEG_CH16_010 = BeginnerPosition(
    id="BEG_CH16_010",
    theme="coup_philippe",
    title='Dubois ch20 D10 — Rafle 30x6 ou 48x6 (Aliar-Huijzer 2010)',
    state=GameState(
        white_men=frozenset({32, 33, 34, 35, 36, 40, 42, 45, 47, 48, 49, 27, 28, 30}),
        black_men=frozenset({1, 3, 5, 9, 11, 12, 13, 16, 18, 19, 20, 23, 24, 25}),
        turn="white",
    ),
    concept="Partie 2010. Rafle se terminant en 6, départ 30 ou 48. La notation publiée contient une anomalie '30.48x6' (probable typo).",
    published_notation='27-21 (16x29) 42-38 (23x43) 34x14 (25x34) 30x6',
    final_move=None,
    explanation='27-21 sacrifice. (16x29) prise. 42-38 sacrifice. (23x43) prise. 34x14 rafle. (25x34) prise. 30x6 rafle finale (variante choisie).',
    source=SourceType.CORPUS,
    source_ref='dubois_apprent_combin_p64_d10',
    crop_id='crops/page_064_d10.png',
    confidence="high",
    claude_notes="Partie Aliar-Huijzer (Arnhem-ch, 2010). Notation Dubois '30.48x6' anomalie — variante 30x6 testée.",
)



# ============================================================================
# Index
# ============================================================================

ALL_BEGINNER_POSITIONS: list[BeginnerPosition] = [
    # Chapitre 1 — Notation
    BEG_CH01_001, BEG_CH01_002,
    # Chapitre 2 — Les règles du jeu
    BEG_CH02_001, BEG_CH02_002, BEG_CH02_003, BEG_CH02_004, BEG_CH02_005,
    BEG_CH02_006, BEG_CH02_007, BEG_CH02_008, BEG_CH02_009, BEG_CH02_010,
    BEG_CH02_011, BEG_CH02_012,
    # Chapitre 3 — Combinaisons en 2 temps
    BEG_CH03_001, BEG_CH03_002, BEG_CH03_003, BEG_CH03_004, BEG_CH03_005,
    BEG_CH03_006, BEG_CH03_007, BEG_CH03_008, BEG_CH03_009, BEG_CH03_010,
    # Chapitre 4 — Le collage et l'envoi à dame
    BEG_CH04_001, BEG_CH04_002, BEG_CH04_003, BEG_CH04_004, BEG_CH04_005,
    BEG_CH04_006, BEG_CH04_007, BEG_CH04_008, BEG_CH04_009, BEG_CH04_010,
    BEG_CH04_011,
    # Chapitre 5 — L'envoi à dame
    BEG_CH05_001, BEG_CH05_002, BEG_CH05_003, BEG_CH05_004, BEG_CH05_005,
    BEG_CH05_006, BEG_CH05_007, BEG_CH05_008, BEG_CH05_009, BEG_CH05_010,
    # Chapitre 6 — La méthode des points de contact
    BEG_CH06_001, BEG_CH06_002, BEG_CH06_003, BEG_CH06_004, BEG_CH06_005,
    BEG_CH06_006, BEG_CH06_007, BEG_CH06_008, BEG_CH06_009, BEG_CH06_010,
    BEG_CH06_011,
    # Chapitre 7 — Les temps de repos créés par une attaque
    BEG_CH07_001, BEG_CH07_002, BEG_CH07_003, BEG_CH07_004, BEG_CH07_005,
    BEG_CH07_006, BEG_CH07_007, BEG_CH07_008, BEG_CH07_009, BEG_CH07_010,
    BEG_CH07_011, BEG_CH07_012,
    # Chapitre 8 — La création des temps de repos
    BEG_CH08_001, BEG_CH08_002, BEG_CH08_003, BEG_CH08_004, BEG_CH08_005,
    BEG_CH08_006, BEG_CH08_007, BEG_CH08_008, BEG_CH08_009, BEG_CH08_010,
    BEG_CH08_011, BEG_CH08_012,
    # Chapitre 9 — Le coup de l'Express
    BEG_CH09_001, BEG_CH09_002, BEG_CH09_003, BEG_CH09_004, BEG_CH09_005,
    BEG_CH09_006, BEG_CH09_007, BEG_CH09_008, BEG_CH09_009, BEG_CH09_010,
    BEG_CH09_011, BEG_CH09_012,
    # Chapitre 10 — Le coup de Ricochet
    BEG_CH10_001, BEG_CH10_002, BEG_CH10_003, BEG_CH10_004, BEG_CH10_005,
    BEG_CH10_006, BEG_CH10_007, BEG_CH10_008, BEG_CH10_009, BEG_CH10_010,
    BEG_CH10_011, BEG_CH10_012,
    # Chapitre 11 — Le coup de Rappel
    BEG_CH11_001, BEG_CH11_002, BEG_CH11_003, BEG_CH11_004, BEG_CH11_005,
    BEG_CH11_006, BEG_CH11_007, BEG_CH11_008, BEG_CH11_009, BEG_CH11_010,
    BEG_CH11_011, BEG_CH11_012,
    # Chapitre 12 — Le coup Renversé
    BEG_CH12_001, BEG_CH12_002, BEG_CH12_003, BEG_CH12_004, BEG_CH12_005,
    BEG_CH12_006, BEG_CH12_007, BEG_CH12_008, BEG_CH12_009, BEG_CH12_010,
    # Chapitre 13 — Le coup Napoléon
    BEG_CH13_001, BEG_CH13_002, BEG_CH13_003, BEG_CH13_004, BEG_CH13_005,
    BEG_CH13_006, BEG_CH13_007, BEG_CH13_008, BEG_CH13_009, BEG_CH13_010,
    # Chapitre 14 — Le coup de la Trappe
    BEG_CH14_001, BEG_CH14_002, BEG_CH14_003, BEG_CH14_004, BEG_CH14_005,
    BEG_CH14_006, BEG_CH14_007, BEG_CH14_008, BEG_CH14_009, BEG_CH14_010,
    # Chapitre 15 — Le coup de Talon
    BEG_CH15_001, BEG_CH15_002, BEG_CH15_003, BEG_CH15_004, BEG_CH15_005,
    BEG_CH15_006, BEG_CH15_007, BEG_CH15_008, BEG_CH15_009, BEG_CH15_010,
    # Chapitre 16 — Le coup Philippe
    BEG_CH16_001, BEG_CH16_002, BEG_CH16_003, BEG_CH16_004, BEG_CH16_005,
    BEG_CH16_006, BEG_CH16_007, BEG_CH16_008, BEG_CH16_009, BEG_CH16_010,
]
