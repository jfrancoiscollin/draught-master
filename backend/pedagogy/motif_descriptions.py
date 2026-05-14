"""Static descriptions for the tactical motifs detected by dilf.

Maintained here (Draught Master) because this is editorial content, not
detection logic. If dilf ever exposes an official MOTIF_METADATA dict
in pedagogy.motifs, import from there instead.

Each entry mirrors the detector's ``name`` class attribute (10 motifs total).
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
}


def get_motif(slug: str) -> dict[str, str] | None:
    """Return motif info dict or None if unknown."""
    return MOTIFS.get(slug)


ALL_SLUGS: list[str] = list(MOTIFS.keys())
