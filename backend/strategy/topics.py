"""Topic definitions for the strategy panel.

Each topic is a curated entry point — a label the user clicks. The
backend maps it to a filter spec (which corpus passages count as
"representative" of the topic) and computes a centroid of those
passages' embedding vectors at startup. Querying with that centroid
ranks the most prototypical passages.

Adding a topic: append a `Topic` to ``TOPICS`` and pick a stable
`key` (matches the frontend button id). The filter spec is evaluated
lazily on first call — the centroid cache rebuilds when the
underlying corpus changes (e.g. after `sync_dilf_corpus.py`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

# Cosine-similarity score lives in [-1, 1]; bundle the centroid's
# dtype to match dilf's sidecars (float32).
_DTYPE = np.float32


@dataclass(frozen=True)
class Topic:
    """A user-facing entry point into the strategy corpus."""

    key: str
    label_fr: str
    label_en: str
    description_fr: str
    # Filter spec used to pick passages whose centroid defines the topic.
    # Empty tuple = no filter on that field.
    source_filter: Tuple[str, ...] = field(default_factory=tuple)
    phase_filter: Optional[str] = None
    systems_filter: Tuple[str, ...] = field(default_factory=tuple)
    nature_filter: Tuple[str, ...] = field(default_factory=tuple)


# Order matches the rendering order in the frontend. Keep it short:
# every additional button costs a centroid computation at startup and
# a slot in the UI.
TOPICS: Tuple[Topic, ...] = (
    Topic(
        key="classique",
        label_fr="Système classique",
        label_en="Classical system",
        description_fr="Principes fondamentaux : centre, ailes, équilibre.",
        source_filter=("SIJBRANDS",),
    ),
    Topic(
        key="roozenburg",
        label_fr="Système Roozenburg",
        label_en="Roozenburg system",
        description_fr="Position de tour, contrôle du centre, attaque.",
        source_filter=("ROOZENBURG",),
    ),
    Topic(
        key="keller",
        label_fr="Système Keller",
        label_en="Keller system",
        description_fr="Pion 2, contre-jeu, structure typique.",
        source_filter=("KELLER",),
    ),
    Topic(
        key="milieu",
        label_fr="Plans de milieu de partie",
        label_en="Middlegame plans",
        description_fr="Manœuvres, plans typiques, idées générales.",
        source_filter=("SPRINGER",),
    ),
    Topic(
        key="goedemoed",
        label_fr="Cours Goedemoed",
        label_en="Goedemoed course",
        description_fr="« A Course in Draughts » : jugement de position et méthode.",
        source_filter=("GOEDEMOED",),
    ),
    Topic(
        key="finales",
        label_fr="Finales stratégiques",
        label_en="Endgame strategy",
        description_fr="Phase finale tous corpus (opposition, percée).",
        phase_filter="finale",
    ),
    # ---- Transversal reading chapters (all sources) ----
    # These build their centroid from the annotated prose (nature/phase) so
    # every scanned manual surfaces several themed chapters, not just its one
    # system chapter. Each source's manual view then shows the passages it has
    # closest to each theme — turning the "best extracts" view into a fuller,
    # multi-chapter read.
    Topic(
        key="ouverture",
        label_fr="L'ouverture",
        label_en="The opening",
        description_fr="Débuts de partie : plans d'approche et choix d'ouverture.",
        phase_filter="ouverture",
    ),
    Topic(
        key="plans",
        label_fr="Plans et manœuvres",
        label_en="Plans and manoeuvres",
        description_fr="Plans typiques de milieu de partie tirés des analyses.",
        nature_filter=("plan",),
    ),
    Topic(
        key="principes",
        label_fr="Principes stratégiques",
        label_en="Strategic principles",
        description_fr="Les règles de fond énoncées par les maîtres.",
        nature_filter=("principe",),
    ),
    Topic(
        key="pieges",
        label_fr="Pièges et avertissements",
        label_en="Pitfalls and warnings",
        description_fr="Erreurs fréquentes et coups à éviter.",
        nature_filter=("avertissement",),
    ),
)


@lru_cache(maxsize=1)
def _topics_by_key() -> dict[str, Topic]:
    return {t.key: t for t in TOPICS}


def get_topic(key: str) -> Optional[Topic]:
    return _topics_by_key().get(key)


@lru_cache(maxsize=None)
def topic_centroid(key: str) -> Optional[np.ndarray]:
    """Return the unit-norm centroid of the topic's passages.

    Lazy + memoized: computed once on first request, then cached for
    the process lifetime. Returns ``None`` if the topic key is
    unknown OR if no passage matches the filter spec OR if the
    matching passages have no embeddings (corpus indexed without the
    embed step). The caller treats ``None`` as "topic temporarily
    unavailable" and returns 503 rather than 500.
    """
    topic = get_topic(key)
    if topic is None:
        return None

    # Lazy import — dilf is a runtime dep, but we don't want to
    # pay the import cost (numpy + sidecar loads) at module load.
    # `_discover_shards` is private to retrieval; we reach in because
    # there's no public enumeration API yet. If dilf ever exposes one,
    # swap here.
    from pedagogy.prose.retrieval import _discover_shards  # noqa: PLC0415

    matching_rows: list[np.ndarray] = []
    for shard in _discover_shards():
        if topic.source_filter and shard.source not in topic.source_filter:
            continue
        for idx, passage in enumerate(shard.passages):
            if topic.phase_filter and passage.phase != topic.phase_filter:
                continue
            if topic.systems_filter and not any(
                s in passage.systems for s in topic.systems_filter
            ):
                continue
            if topic.nature_filter and passage.nature not in topic.nature_filter:
                continue
            matching_rows.append(shard.matrix[idx])

    if not matching_rows:
        log.info(
            "topic_centroid(%s): no passages matched filter spec — topic dormant",
            key,
        )
        return None

    centroid = np.mean(np.stack(matching_rows, axis=0), axis=0).astype(_DTYPE)
    norm = float(np.linalg.norm(centroid))
    if norm == 0.0:
        log.warning("topic_centroid(%s): centroid has zero norm — degenerate", key)
        return None
    return centroid / norm
