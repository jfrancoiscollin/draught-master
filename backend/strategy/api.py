"""FastAPI router for /api/strategy/*."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from .models import (
    StrategyPassageOut,
    StrategySearchResponse,
    TopicOut,
)
from .topics import TOPICS, get_topic, topic_centroid

log = logging.getLogger(__name__)

_PAGES_DIR = Path(__file__).resolve().parent / "pages"

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


@lru_cache(maxsize=8)
def _load_diagram_manifest(source: str) -> dict[tuple[int, int], str]:
    """Return ``{(page, number): crop_filename}`` for a source, or {} if no
    manifest is bundled. Cached — manifests are small (<50 KB) and immutable
    at runtime."""
    manifest_path = _PAGES_DIR / source.lower() / "diagrams_manifest.json"
    if not manifest_path.is_file():
        return {}
    with manifest_path.open() as f:
        data = json.load(f)
    return {(e["page"], e["number"]): e["crop"] for e in data.get("entries", [])}


@lru_cache(maxsize=8)
def _load_diagram_fens(source: str) -> dict[tuple[int, int], str]:
    """Return ``{(page, number): fen}`` for a source's manually annotated
    positions, or {} if the file is missing/empty. The FEN file is the
    foundation of Lane C (interactive board) — see
    ``docs/STRATEGIE_DIAGRAMS_PLAN.md`` §5. Format::

        {
          "source": "SIJBRANDS",
          "entries": [
            {"page": 48, "number": 6, "fen": "W:W31,32,...:B1,2,..."}
          ]
        }

    Annotation is manual right now (one entry per diagram added by hand
    after reading the crop). Future tooling could pre-fill via piece
    classification + human review.
    """
    fens_path = _PAGES_DIR / source.lower() / "diagrams_fens.json"
    if not fens_path.is_file():
        return {}
    with fens_path.open() as f:
        data = json.load(f)
    return {(e["page"], e["number"]): e["fen"] for e in data.get("entries", [])}


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


@router.get("/page-image")
def page_image(
    source: str = Query(..., description="Source code, e.g. 'SIJBRANDS'"),
    page: int = Query(..., ge=1, description="1-based PDF page number"),
) -> FileResponse:
    """Return the rendered page from a corpus PDF as a JPEG.

    Lets the frontend show the diagram referenced by a passage when the
    prose says e.g. « Mettez la position du DIAGRAMME 6 sur le damier ».
    """
    source_dir = _PAGES_DIR / source.lower()
    if not source_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"no page images bundled for source {source!r}",
        )
    img_path = source_dir / f"page_{page:04d}.jpg"
    if not img_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"page {page} not bundled for {source!r}",
        )
    return FileResponse(img_path, media_type="image/jpeg")


@router.get("/diagram")
def diagram(
    source: str = Query(..., description="Source code, e.g. 'SIJBRANDS'"),
    page: int = Query(..., ge=1, description="Page where the diagram is referenced"),
    number: int = Query(..., ge=1, description="Diagram number as printed in the book"),
) -> FileResponse:
    """Return an isolated diagram crop (JPEG), or 404 if not extracted.

    Sijbrands numbering restarts at 1 per chapter, so a global
    ``(source, number)`` key wouldn't be unique — we key by
    ``(page, number)`` and the frontend passes the passage's page.
    The texture-variance detector + caption proximity matching covers
    ~70% of Sijbrands pages; the rest fall back to the full-page modal
    via ``/page-image``.  See ``docs/STRATEGIE_DIAGRAMS_PLAN.md`` §4.
    """
    manifest = _load_diagram_manifest(source)
    if not manifest:
        raise HTTPException(
            status_code=404,
            detail=f"no diagram crops bundled for source {source!r}",
        )
    crop_name = manifest.get((page, number))
    if crop_name is None:
        raise HTTPException(
            status_code=404,
            detail=f"diagram {number} on page {page} not extracted for {source!r}",
        )
    crop_path = _PAGES_DIR / source.lower() / "diagrams" / crop_name
    if not crop_path.is_file():
        # Manifest entry without backing file — corruption / partial bundle.
        log.warning("manifest entry %s missing on disk", crop_path)
        raise HTTPException(status_code=404, detail="crop file missing")
    return FileResponse(crop_path, media_type="image/jpeg")


@router.get("/diagram-index")
def diagram_index(
    source: str = Query(..., description="Source code, e.g. 'SIJBRANDS'"),
) -> dict[int, list[int]]:
    """Return ``{page: [number, ...]}`` for every crop in the manifest.

    Powers the jump-to-diagram dropdown in the strategy panel: once the
    operator picks a (source, page), the frontend can show the exact list
    of diagram numbers that have a backing crop, instead of letting them
    type a number that 404s and falls back to the full-page image.
    """
    manifest = _load_diagram_manifest(source)
    index: dict[int, list[int]] = {}
    for page, number in manifest.keys():
        index.setdefault(page, []).append(number)
    for nums in index.values():
        nums.sort()
    return index


@router.get("/diagram-suggest-fen")
def diagram_suggest_fen(
    source: str = Query(..., description="Source code, e.g. 'SIJBRANDS'"),
    page: int = Query(..., ge=1, description="Page where the diagram is referenced"),
    number: int = Query(..., ge=1, description="Diagram number as printed in the book"),
) -> dict:
    """Return ``{"fen": "..."}`` predicted by the rules-based detector.

    Pre-fills the in-app annotation editor with a guess based on the
    printed crop, so the operator validates with a few clicks instead
    of placing every piece from scratch.  On Sijbrands the detector
    hits 99.86% per-square accuracy — most boards come out exact, the
    rare misses are 1–2 squares the operator fixes manually.

    404 if the crop isn't bundled (same condition as ``/diagram``) —
    nothing to detect from.  The caller distinguishes "no suggestion"
    (404, show a blank board) from "suggestion ready" (200, seed the
    editor).
    """
    manifest = _load_diagram_manifest(source)
    crop_name = manifest.get((page, number))
    if crop_name is None:
        raise HTTPException(
            status_code=404,
            detail=f"no crop for ({source!r}, p.{page}, #{number}) — nothing to detect",
        )
    crop_path = _PAGES_DIR / source.lower() / "diagrams" / crop_name
    if not crop_path.is_file():
        raise HTTPException(status_code=404, detail="crop file missing")
    from .fen_detector import detect_fen

    return {"fen": detect_fen(crop_path)}


@router.get("/diagram-fen")
def diagram_fen(
    source: str = Query(..., description="Source code, e.g. 'SIJBRANDS'"),
    page: int = Query(..., ge=1, description="Page where the diagram is referenced"),
    number: int = Query(..., ge=1, description="Diagram number as printed in the book"),
) -> dict:
    """Return ``{"fen": "..."}`` for a manually annotated diagram, or 404.

    Lane C foundation — the FEN file is filled by hand
    (``backend/strategy/pages/<source>/diagrams_fens.json``). When an
    entry exists, the frontend renders an interactive ``<Board>`` next
    to the crop image; otherwise it just shows the crop with no Board.
    """
    # Distinguish "source has no FEN file at all" from "source has the file
    # but this (page, number) isn't annotated yet" — different action for
    # the user (bundle the file vs annotate that specific entry).
    fens_path = _PAGES_DIR / source.lower() / "diagrams_fens.json"
    if not fens_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"no FEN file bundled for source {source!r}",
        )
    fen = _load_diagram_fens(source).get((page, number))
    if fen is None:
        raise HTTPException(
            status_code=404,
            detail=f"diagram {number} on page {page} not yet annotated for {source!r}",
        )
    return {"fen": fen, "source": source, "page": page, "number": number}

