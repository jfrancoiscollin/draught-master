"""FastAPI router for /api/strategy/*."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .models import (
    StrategyPassageOut,
    StrategySearchResponse,
    TopicOut,
)
from .topics import TOPICS, get_topic, topic_centroid

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


@router.get("/topics", response_model=list[TopicOut])
def list_topics() -> list[TopicOut]:
    """Enumerate the curated topic buttons + whether each has a
    non-empty centroid (i.e. matched at least one passage)."""
    return [
        TopicOut(
            key=t.key,
            label_fr=t.label_fr,
            label_en=t.label_en,
            description_fr=t.description_fr,
            available=topic_centroid(t.key) is not None,
        )
        for t in TOPICS
    ]


@router.get("/search", response_model=StrategySearchResponse)
def search(
    topic: str = Query(..., description="Topic key, e.g. 'roozenburg'"),
    top_k: int = Query(10, ge=1, le=50),
) -> StrategySearchResponse:
    """Return the top-K passages most similar to the topic's centroid.

    The centroid is the mean of every passage matching the topic's
    filter spec (see ``strategy.topics``). When restricting search
    to the same source(s) as the filter, results read like
    "most representative passages of this book".
    """
    spec = get_topic(topic)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"unknown topic: {topic!r}")

    centroid = topic_centroid(topic)
    if centroid is None:
        raise HTTPException(
            status_code=503,
            detail=f"topic {topic!r} has no embedded passages — corpus not indexed",
        )

    # Lazy import to keep the module load cheap.
    from pedagogy.prose.retrieval import search_with_vector  # noqa: PLC0415

    sources_filter: Optional[tuple[str, ...]] = (
        spec.source_filter if spec.source_filter else None
    )
    results = search_with_vector(centroid, k=top_k, sources=sources_filter)

    return StrategySearchResponse(
        topic_key=topic,
        top_k=top_k,
        passages=[
            StrategyPassageOut(
                passage_id=p.passage_id,
                score=float(score),
                text=p.text,
                source=p.source,
                book=p.book,
                page=p.page,
                systems=list(p.systems),
                phase=p.phase,
                nature=p.nature,
            )
            for score, p in results
        ],
    )
