"""Static descriptions for the tactical motifs detected by dilf.

Maintained here (Draught Master) because this is editorial content, not
detection logic. If dilf ever exposes an official MOTIF_METADATA dict
in pedagogy.motifs, import from there instead.

Each entry mirrors the detector's ``name`` class attribute.
"""

from __future__ import annotations

MOTIFS: dict[str, dict[str, str]] = {
    "coup_royal": {
        "slug": "coup_royal",
        "name_fr": "Coup royal",
        "name_en": "Royal shot",
        "description_fr": (
            "Le coup royal est une combinaison qui cible ou implique la dame adverse. "
            "En exploitant sa mobilité réduite ou sa position exposée, le joueur force "
            "une séquence de captures qui supprime la dame ou obtient un avantage décisif. "
            "Reconnaître les cases où la dame adverse est vulnérable est la clé de ce motif."
        ),
        "description_en": (
            "The royal shot is a combination targeting the opponent's king. "
            "By exploiting its reduced mobility or exposed position, the player forces "
            "a capture sequence that wins the king or achieves a decisive advantage."
        ),
    },
    "coup_turc": {
        "slug": "coup_turc",
        "name_fr": "Coup turc",
        "name_en": "Turkish shot",
        "description_fr": (
            "Le coup turc est une combinaison spectaculaire dans laquelle une pièce "
            "effectue plusieurs prises en zigzag sur des lignes différentes du plateau. "
            "Il requiert une lecture rigoureuse sur plusieurs coups et survient souvent "
            "de manière inattendue lorsque les pièces adverses sont alignées sur des "
            "diagonales voisines."
        ),
        "description_en": (
            "The Turkish shot is a spectacular combination where a piece makes multiple "
            "captures in a zigzag pattern across different board lines. "
            "It requires deep calculation and often occurs unexpectedly."
        ),
    },
    "coup_de_talon": {
        "slug": "coup_de_talon",
        "name_fr": "Coup du talon",
        "name_en": "Heel shot",
        "description_fr": (
            "Le coup du talon est une attaque surprise en retraite : une pièce recule "
            "en diagonale pour capturer une pièce adverse qui semblait hors de danger. "
            "Ce coup est particulièrement difficile à anticiper car il va à l'encontre "
            "du réflexe naturel d'avancer. La case de départ de l'attaquant, apparemment "
            "sans intérêt, se révèle être le pivot d'une prise forcée."
        ),
        "description_en": (
            "The heel shot is a surprise backward attack: a piece retreats diagonally "
            "to capture an opponent's piece that seemed safe. It's especially hard to "
            "spot because it goes against the natural instinct to advance forward."
        ),
    },
    "envoi_a_dame": {
        "slug": "envoi_a_dame",
        "name_fr": "Envoi à dame",
        "name_en": "King promotion",
        "description_fr": (
            "L'envoi à dame est une combinaison qui force la promotion d'une pièce en "
            "dame. Le joueur crée un couloir ou contraint l'adversaire à ouvrir une "
            "ligne vers la rangée du fond, transformant une pièce ordinaire en dame avec "
            "un gain tactique ou positionnel immédiat. La dame ainsi obtenue crée souvent "
            "une menace imparable."
        ),
        "description_en": (
            "King promotion is a combination that forces a piece to be crowned. "
            "The player opens a corridor or forces the opponent to clear a path to the "
            "back rank, converting a man into a king with immediate tactical gain."
        ),
    },
    "sacrifice": {
        "slug": "sacrifice",
        "name_fr": "Sacrifice",
        "name_en": "Sacrifice",
        "description_fr": (
            "Le sacrifice consiste à offrir délibérément une ou plusieurs pièces pour "
            "obtenir un avantage positionnel ou tactique. Un sacrifice bien calculé "
            "peut déséquilibrer la position adverse, ouvrir des diagonales décisives "
            "ou déclencher une attaque gagnante. La contrepartie matérielle doit être "
            "compensée par un gain clair à court ou moyen terme."
        ),
        "description_en": (
            "A sacrifice involves deliberately offering one or more pieces to gain a "
            "positional or tactical advantage. A well-calculated sacrifice can open "
            "diagonals or launch a decisive attack."
        ),
    },
    "prise_max_ratee": {
        "slug": "prise_max_ratee",
        "name_fr": "Prise maximale ratée",
        "name_en": "Missed maximum capture",
        "description_fr": (
            "Au jeu de dames international, le règlement impose de prendre le maximum "
            "de pièces possible (règle de la prise majoritaire). Une prise maximale ratée "
            "signifie qu'une variante de capture différente aurait pris davantage de pièces "
            "que le coup joué. C'est une infraction aux règles du jeu — maîtriser ce "
            "décompte est fondamental pour jouer légalement et efficacement."
        ),
        "description_en": (
            "In international draughts, the rules require taking the maximum number of "
            "pieces possible. A missed maximum capture means an alternative move would "
            "have captured more pieces. This is a fundamental rule to master."
        ),
    },
    "coup_philippe": {
        "slug": "coup_philippe",
        "name_fr": "Coup Philippe",
        "name_en": "Philippe's shot",
        "description_fr": (
            "Le coup Philippe est une combinaison classique nommée d'après un joueur "
            "historique. Il s'agit d'une configuration spécifique où une pièce avancée "
            "en position apparemment forte se révèle être une cible : une séquence de "
            "captures force un échange défavorable ou une perte matérielle nette sur "
            "les colonnes centrales."
        ),
        "description_en": (
            "Philippe's shot is a classical named combination where an apparently strong "
            "advanced piece becomes a target in a forced capture sequence."
        ),
    },
    "coup_raphael": {
        "slug": "coup_raphael",
        "name_fr": "Coup Raphaël",
        "name_en": "Raphaël's shot",
        "description_fr": (
            "Le coup Raphaël est une combinaison classique caractérisée par une séquence "
            "de captures sur les ailes du plateau. Une pièce avancée sert d'appât pour "
            "déclencher une prise en chaîne qui dépasse le simple échange matériel et "
            "débouche sur une position gagnante par supériorité numérique ou positionnelle."
        ),
        "description_en": (
            "Raphaël's shot is a classical combination with a wing capture sequence. "
            "An advanced piece serves as bait to trigger a chain capture resulting "
            "in material or positional advantage."
        ),
    },
    "coup_express": {
        "slug": "coup_express",
        "name_fr": "Coup express",
        "name_en": "Express shot",
        "description_fr": (
            "Le coup express est une combinaison rapide et directe qui exploite une "
            "faiblesse immédiate dans la position adverse. Sans séquence longue, "
            "il s'agit de frapper au bon moment — souvent en un ou deux coups — avant "
            "que l'adversaire n'ait le temps de consolider sa défense ou de combler "
            "la brèche tactique."
        ),
        "description_en": (
            "The express shot is a fast, direct combination that exploits an immediate "
            "weakness. It strikes quickly — often in one or two moves — before the "
            "opponent can consolidate their defense."
        ),
    },
    "coup_bonnard": {
        "slug": "coup_bonnard",
        "name_fr": "Coup Bonnard",
        "name_en": "Bonnard's shot",
        "description_fr": (
            "Le coup Bonnard est une combinaison subtile impliquant un sacrifice de "
            "pièce sur une case clé. L'idée centrale est de bloquer temporairement "
            "une pièce adverse ou d'ouvrir une diagonale décisive, créant ainsi une "
            "menace imparable sur les coups suivants. La subtilité réside dans le fait "
            "que la case de sacrifice semble initialement neutre."
        ),
        "description_en": (
            "Bonnard's shot is a subtle combination involving a piece sacrifice on a "
            "key square to block an opponent's piece or open a decisive diagonal, "
            "creating an unstoppable threat."
        ),
    },
    "coup_napoleon": {
        "slug": "coup_napoleon",
        "name_fr": "Coup Napoléon",
        "name_en": "Napoleon shot",
        "description_fr": (
            "Le coup Napoléon enchaîne trois demi-coups : un sacrifice, une "
            "prise adverse forcée qui éloigne une pièce-clé d'une diagonale "
            "défensive, puis un envoi à dame. Ce qui distingue Napoléon d'un "
            "envoi à dame ordinaire, c'est la déflexion explicite : la "
            "réponse de l'adversaire doit être une capture qui dégage le "
            "couloir de promotion."
        ),
        "description_en": (
            "The Napoleon shot chains three half-moves: a sacrifice, a "
            "forced opponent capture that deflects a key piece away from a "
            "defensive diagonal, and a promotion landing. What sets it apart "
            "from a plain king promotion is the explicit deflection — the "
            "opponent's reply must be a capture that clears the promotion "
            "corridor."
        ),
    },
    "coup_manoury": {
        "slug": "coup_manoury",
        "name_fr": "Coup Manoury",
        "name_en": "Manoury shot",
        "description_fr": (
            "Le coup Manoury est l'archétype de la combinaison « à profit » "
            "enseignée dans les clubs français : un premier sacrifice (parfois "
            "deux) force l'adversaire dans une configuration où les diagonales "
            "s'alignent, et la riposte du joueur est une rafle qui capture au "
            "moins quatre pions adverses d'un seul coup. La force du motif "
            "tient à la profondeur du calcul nécessaire pour le voir venir."
        ),
        "description_en": (
            "The Manoury shot is the archetypal long-gain combination taught "
            "in French clubs: a first sacrifice (sometimes two) forces the "
            "opponent into a configuration where the diagonals align, and "
            "the player's follow-up rafle captures four or more opponent men "
            "in a single move. The motif rewards deep calculation."
        ),
    },
    "coup_enfilade": {
        "slug": "coup_enfilade",
        "name_fr": "Coup d'enfilade",
        "name_en": "In-line rafle",
        "description_fr": (
            "L'enfilade est la rafle la plus simple : la pièce attaquante "
            "traverse une diagonale unique sans jamais changer de direction, "
            "et capture trois ou quatre pions adverses alignés sur cette "
            "diagonale. Distincte du coup du talon (qui inverse le sens) et "
            "du coup express (rafle de 5+ captures), elle reste le pain "
            "quotidien des combinaisons de club."
        ),
        "description_en": (
            "The in-line rafle is the simplest long capture: the attacking "
            "piece travels along a single diagonal without ever changing "
            "direction, taking three or four opponent men aligned on it. "
            "Distinct from the heel shot (which reverses direction) and the "
            "express shot (5+ captures), it's the everyday club-level "
            "combination."
        ),
    },
    "coup_du_bruleur": {
        "slug": "coup_du_bruleur",
        "name_fr": "Coup du brûleur",
        "name_en": "Burner shot",
        "description_fr": (
            "Le coup du brûleur est un motif positionnel : un coup tranquille "
            "(non-capture) qui « brûle » plusieurs pions adverses en leur "
            "bloquant simultanément leurs deux diagonales avant. Les pions "
            "ainsi gelés ne peuvent plus avancer ; ils attendent qu'une autre "
            "pièce libère un passage. Souvent sous-estimé parce qu'il ne "
            "capture rien immédiatement, c'est pourtant un outil stratégique "
            "redoutable en milieu de partie."
        ),
        "description_en": (
            "The burner shot is a positional motif: a quiet (non-capturing) "
            "move that simultaneously blocks both forward diagonals of two or "
            "more opponent men at once. The frozen men can no longer advance — "
            "they wait for another piece to clear a path. Often underrated "
            "because no immediate material change happens, it's a formidable "
            "middlegame tool."
        ),
    },
    "combinaison_2_temps": {
        "slug": "combinaison_2_temps",
        "name_fr": "Combinaison en 2 temps",
        "name_en": "2-move combination",
        "description_fr": (
            "Combinaison forcée en deux coups d'attaque : on offre une pièce, l'adversaire "
            "est contraint de capturer (souvent par la règle de la prise majoritaire), puis "
            "on réplique par une seconde frappe qui récupère plus de matériel qu'on en a "
            "donné. Le motif générique des combinaisons courtes : pas de nom particulier, "
            "juste une séquence où chaque réponse adverse est forcée et le bilan matériel "
            "final est positif."
        ),
        "description_en": (
            "A forced combination with two attacker moves: offer a piece, the opponent "
            "is compelled to capture (often under the maximum-capture rule), then strike "
            "back with a second move that nets more material than was given up. The "
            "generic short-combination pattern — every opponent reply is forced and the "
            "final material balance is positive."
        ),
    },
    "combinaison_3_temps": {
        "slug": "combinaison_3_temps",
        "name_fr": "Combinaison en 3 temps",
        "name_en": "3-move combination",
        "description_fr": (
            "Combinaison forcée en trois coups d'attaque, avec deux répliques adverses "
            "forcées en chaîne. Plus profonde qu'une combinaison en 2 temps, elle exige "
            "de visualiser une séquence où chaque demi-coup de l'adversaire est imposé "
            "par la position, et où le gain matériel net apparaît seulement au troisième "
            "coup attaquant. Reconnaître ces chaînes plus longues distingue les joueurs "
            "tactiquement aguerris."
        ),
        "description_en": (
            "A forced combination with three attacker moves and two forced opponent "
            "replies chained between them. Deeper than a 2-move combination — requires "
            "visualising a sequence where every opponent half-move is forced and the "
            "material gain only materialises on the third attacker move."
        ),
    },
    "combinaison_4_temps": {
        "slug": "combinaison_4_temps",
        "name_fr": "Combinaison en 4 temps",
        "name_en": "4-move combination",
        "description_fr": (
            "Combinaison forcée en quatre coups d'attaque, avec trois répliques adverses "
            "forcées. Calcul profond : on enchaîne sacrifices et frappes successives en "
            "vérifiant que l'adversaire n'a aucune échappatoire à chaque demi-coup. Ces "
            "combinaisons spectaculaires ne se laissent voir qu'aux joueurs qui calculent "
            "loin et précisément."
        ),
        "description_en": (
            "A forced combination with four attacker moves and three forced opponent "
            "replies. Deep calculation territory: stacking sacrifices and strikes while "
            "verifying the opponent has no escape at every half-move."
        ),
    },
    "combinaison_5_temps": {
        "slug": "combinaison_5_temps",
        "name_fr": "Combinaison en 5 temps ou plus",
        "name_en": "5-move (or deeper) combination",
        "description_fr": (
            "Combinaison forcée en au moins cinq coups d'attaque, le seau le plus profond "
            "détecté. Très rare en partie pratique — quand elle survient, c'est souvent "
            "le couronnement d'une préparation positionnelle minutieuse. Le simple fait "
            "de la voir à l'œuvre vaut le détour."
        ),
        "description_en": (
            "A forced combination with five or more attacker moves — the deepest detection "
            "bucket. Rare in practical play; when it occurs it typically caps a careful "
            "positional build-up."
        ),
    },
}


def get_motif(slug: str) -> dict[str, str] | None:
    """Return motif info dict or None if unknown."""
    return MOTIFS.get(slug)


ALL_SLUGS: list[str] = list(MOTIFS.keys())
