"""Pydantic models for /api/strategy/*."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TopicOut(BaseModel):
    key: str
    label_fr: str
    label_en: str
    description_fr: str
    # Number of passages matching this topic's filter spec, after
    # corpus load. Lets the frontend disable buttons whose centroid
    # is empty (e.g., a `phase=finale` topic on a corpus indexed
    # without phase tags).
    available: bool


class StrategyPassageOut(BaseModel):
    """One sourced passage in a strategy search result."""

    passage_id: str
    score: float          # cosine similarity in [-1, 1]
    text: str
    source: str           # uppercase code, e.g. "SIJBRANDS"
    book: str             # slug, e.g. "classique"
    page: int             # 1-based page in the PDF
    systems: list[str]
    phase: Optional[str] = None
    nature: Optional[str] = None


class StrategySearchResponse(BaseModel):
    topic_key: str
    top_k: int
    passages: list[StrategyPassageOut]
