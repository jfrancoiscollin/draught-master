"""FastAPI router for /api/strategy/*."""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

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
def _load_diagram_manifest(source: str) -> dict[tuple[int, int], dict]:
    """Return ``{(page, number): entry_dict}`` for a source, or {} if no
    manifest is bundled. Cached — manifests are small (<100 KB) and
    immutable at runtime.

    Two manifest schemas are supported:
      - ``{"crop": "diagram_NNN_pXXXX.jpg"}`` — Sijbrands/Springer style,
        pre-extracted JPEG files in ``pages/<source>/diagrams/``.
      - ``{"bbox": [x0, y0, x1, y1]}`` — Roozenburg/Keller style, the
        crop is computed on the fly from the page-image at request
        time.  Cuts the need to store separate JPGs for sources where
        no good auto-extractor exists yet.

    The returned dicts contain whichever set of keys the source uses;
    callers branch on key presence.
    """
    manifest_path = _PAGES_DIR / source.lower() / "diagrams_manifest.json"
    if not manifest_path.is_file():
        return {}
    with manifest_path.open() as f:
        data = json.load(f)
    return {(e["page"], e["number"]): e for e in data.get("entries", [])}


@lru_cache(maxsize=8)
def _load_diagram_fens(source: str) -> dict[tuple[int, int], str]:
    """Return ``{(page, number): fen}`` for a source's *human-verified*
    positions, or {} if the file is missing.  Source of truth — wins
    over auto-detected FENs whenever both exist for the same square.
    """
    fens_path = _PAGES_DIR / source.lower() / "diagrams_fens.json"
    if not fens_path.is_file():
        return {}
    with fens_path.open() as f:
        data = json.load(f)
    return {(e["page"], e["number"]): e["fen"] for e in data.get("entries", [])}


@lru_cache(maxsize=8)
def _load_diagram_fens_auto(source: str) -> dict[tuple[int, int], str]:
    """Return ``{(page, number): fen}`` for the *auto-detected* FENs
    (see ``backend/strategy/generate_auto_fens.py``).  Covers the whole
    manifest at ~99.87% per-square accuracy on Sijbrands, so most
    diagrams render an interactive ``<Board>`` even when no human has
    annotated them yet.  Used as a fallback when the human file has no
    entry for a given (page, number).
    """
    fens_path = _PAGES_DIR / source.lower() / "diagrams_fens_auto.json"
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
    entry = manifest.get((page, number))
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"diagram {number} on page {page} not extracted for {source!r}",
        )
    if "bbox" in entry:
        # Bbox manifest entry (Roozenburg / Keller): crop on the fly from
        # the page-image.  Avoids storing redundant JPEGs in the repo.
        return _crop_from_page_image(source, page, entry["bbox"])
    crop_name = entry["crop"]
    crop_path = _PAGES_DIR / source.lower() / "diagrams" / crop_name
    if not crop_path.is_file():
        log.warning("manifest entry %s missing on disk", crop_path)
        raise HTTPException(status_code=404, detail="crop file missing")
    return FileResponse(crop_path, media_type="image/jpeg")


def _crop_from_page_image(source: str, page: int, bbox: list[int]) -> Response:
    """Crop ``bbox`` out of the source's page-image JPEG and return as
    JPEG.  Used by bbox-style manifest entries — see
    ``_load_diagram_manifest`` for the schema."""
    from io import BytesIO
    from PIL import Image

    img_path = _PAGES_DIR / source.lower() / f"page_{page:04d}.jpg"
    if not img_path.is_file():
        raise HTTPException(status_code=404, detail=f"page {page} not bundled for {source!r}")
    x0, y0, x1, y1 = bbox
    with Image.open(img_path) as im:
        crop = im.crop((x0, y0, x1, y1))
        buf = BytesIO()
        crop.save(buf, format="JPEG", quality=85)
    return Response(content=buf.getvalue(), media_type="image/jpeg")


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


@router.get("/kb-themes")
def kb_themes(
    source: Optional[str] = Query(None, description="Restrict to one manual"),
) -> list[dict]:
    """Thematic strategic knowledge base — one card per lesson theme.

    Each card aggregates the engine-validated diagram positions filed
    under a manual lesson ("Le débordement", "Bloquer des pions", …),
    with counts and a 3-position teaser. Powers a browse-by-theme entry
    point alongside the embedding-based topic buttons.
    """
    from .strategic_kb import theme_index

    return theme_index(source)


@router.get("/kb-theme")
def kb_theme(
    theme: str = Query(..., description="Exact lesson title, e.g. 'Le débordement'"),
    source: Optional[str] = Query(None, description="Restrict to one manual"),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Every position illustrating one strategic theme (capped)."""
    from .strategic_kb import theme_detail

    detail = theme_detail(theme, source, limit)
    if detail["n_positions"] == 0:
        raise HTTPException(status_code=404, detail=f"no positions for theme {theme!r}")
    return detail


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
    entry = manifest.get((page, number))
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"no crop for ({source!r}, p.{page}, #{number}) — nothing to detect",
        )
    from .fen_detector import config_for_source, detect_fen
    cfg = config_for_source(source)

    if "bbox" in entry:
        from PIL import Image

        img_path = _PAGES_DIR / source.lower() / f"page_{page:04d}.jpg"
        if not img_path.is_file():
            raise HTTPException(status_code=404, detail=f"page {page} not bundled")
        x0, y0, x1, y1 = entry["bbox"]
        with Image.open(img_path) as im:
            return {"fen": detect_fen(im.crop((x0, y0, x1, y1)), config=cfg)}
    crop_path = _PAGES_DIR / source.lower() / "diagrams" / entry["crop"]
    if not crop_path.is_file():
        raise HTTPException(status_code=404, detail="crop file missing")
    return {"fen": detect_fen(crop_path, config=cfg)}


# Sources where the auto-detector has been validated end-to-end and the
# Sources where the auto-detector has been validated end-to-end and the
# operator has chosen to trust its output without per-diagram review.
# Adding a source here causes ``/diagram-fen`` to return ``kind: "human"``
# even for ``diagrams_fens_auto.json`` entries — the frontend then drops
# the "auto · non validé" badge and the printed-crop side panel.
# Per-entry overrides remain possible: writing to ``diagrams_fens.json``
# always wins over the auto file.
_TRUSTED_AUTO_SOURCES = {"SIJBRANDS", "SPRINGER", "ROOZENBURG", "KELLER"}


@lru_cache(maxsize=8)
def _load_diagram_sections(source: str) -> dict[int, dict[str, str]]:
    """Return ``{page: {"heading": ..., "title": ...}}`` for a source.

    Pedagogical section metadata extracted from the source PDF by
    ``extract_strategy_sections.py``.  Used by the manual endpoint to
    title each passage card with its parent chapter ("Thème 4 — Libérer
    le chemin") instead of the generic "Diagramme N · page X".  Returns
    {} if the source has no metadata bundled.

    The raw extraction is noisy: a heading like "Thème 8" recurs as a
    running page header, and each occurrence captured whatever body line
    followed it — so later pages inherited move sequences or full
    sentences as their "title". We clean that here at load time
    (:func:`_canonical_sections`) so a theme shows ONE stable title.
    """
    p = _PAGES_DIR / source.lower() / "diagram_sections.json"
    if not p.is_file():
        return {}
    with p.open() as f:
        data = json.load(f)
    return _canonical_sections(
        {int(k): v for k, v in data.items()}, trust_titles=source.upper() in _CURATED_SECTION_SOURCES
    )


# Sources whose diagram_sections.json was rebuilt from the book's real table
# of contents (one reliable title per heading) — trust those titles verbatim
# instead of re-filtering them with the noisy-data heuristic.
_CURATED_SECTION_SOURCES = {"SIJBRANDS", "KELLER", "SPRINGER", "ROOZENBURG"}


# A real section heading marker (Thème/Leçon/Partie/Chapitre/Problème N, or
# the "3 - LE JEU DES NOIRS" numbered form). Anything else (all-caps body
# exclamations the extractor mistook for a heading) is dropped.
_HEADING_OK = re.compile(
    r"^(?:Leçon|Thème|Partie|Chapitre|Problème)\s+n?°?\s*\d+|^\d+\s*[-–]\s*\S",
    re.IGNORECASE,
)


def _is_titleish(title: str) -> bool:
    """True when ``title`` reads like a real section title (a short noun
    phrase) rather than a stray body line, move sequence, diagram ref or
    game citation that the extractor latched onto."""
    t = (title or "").strip()
    if not t or len(t) > 55 or len(t.split()) > 6:
        return False
    if not t[0].isalpha() or not t[0].isupper():
        return False
    if t[-1] in ".:!?":                                  # sentence-like
        return False
    if re.search(r"\d+\s*[-x×]\s*\d+", t):               # move / coords
        return False
    if re.search(r"\b(?:19|20)\d{2}\b", t):              # year -> game citation
        return False
    if t.upper().startswith(
        ("DIAGRAMME", "EXERCICE", "PROBLÈME", "FRAGMENT", "VISUALISATION")
    ):
        return False
    if "," in t or " – " in t or " — " in t:             # list / player vs player
        return False
    return True


def _canonical_sections(
    raw: dict[int, dict[str, str]], trust_titles: bool = False
) -> dict[int, dict[str, str]]:
    """Collapse each heading to a single clean title and drop junk headings.

    For every distinct heading, the canonical title is the first (lowest
    page) candidate that passes :func:`_is_titleish`; that title is then
    applied to every page of the heading. Headings with no clean candidate
    keep an empty title (the card shows just "Thème N"). Entries without a
    ``heading`` (e.g. Goedemoed's ``{"theme": ...}`` shape) pass through
    untouched.

    ``trust_titles`` (curated sources, rebuilt from the book's table of
    contents): take the heading's title verbatim — it's reliable and may be a
    long phrase the heuristic would wrongly reject. Noisy page-scan sources
    keep the heuristic filter.
    """
    from collections import defaultdict  # noqa: PLC0415

    titles_by_heading: dict[str, list[str]] = defaultdict(list)
    for page in sorted(raw):
        h = raw[page].get("heading")
        if h:
            titles_by_heading[h].append(raw[page].get("title", ""))

    def _pick(titles: list[str]) -> str:
        if trust_titles:
            return next((t for t in titles if t and t.strip()), "")
        return next((t for t in titles if _is_titleish(t)), "")

    canonical = {h: _pick(titles) for h, titles in titles_by_heading.items()}

    out: dict[int, dict[str, str]] = {}
    for page, entry in raw.items():
        h = entry.get("heading")
        if h is None:
            out[page] = entry                       # theme-style: leave as-is
        elif _HEADING_OK.match(h):
            out[page] = {"heading": h, "title": canonical.get(h, "")}
        # else: junk heading -> omit, card falls back to "Diagramme N · page X"
    return out


@router.get("/manual")
def manual(
    source: str = Query(..., description="Source code, e.g. 'SIJBRANDS'"),
    per_chapter: int = Query(20, ge=1, le=50, description="(unused) kept for API compat"),
) -> dict:
    """Return the source's manual as a *linear, book-faithful* read.

    Walks the prose corpus in document order (page, then position on the
    page) and groups consecutive passages under their printed section
    heading (``Leçon 7``, ``Exercice 1``, ``Thème 3`` …). Each chapter is
    one such section; its passages keep the book order so the reader sees
    "Exercise X → Diagram N + its text → Diagram N+1 …" exactly as printed,
    instead of the old topic-centroid regrouping.

    Move-score / game-citation dumps with no readable sentence are dropped
    (``has_prose``); each passage's text leads with its sentence
    (``lead_excerpt``). The frontend pairs each passage with its diagram
    (live board when a valid FEN exists, else the printed image).
    """
    src_upper = source.upper()
    from .prose_quality import lead_excerpt  # noqa: PLC0415

    groups = _book_chapters(source)
    chapters: list[dict] = []
    for g in groups:
        chapters.append({
            "topic_key": g["topic_key"],
            "title_fr": g["heading"],
            "title_en": g["heading"],
            "description_fr": g["title"],
            "passages": [
                {
                    "passage_id": p.passage_id,
                    "score": 0.0,
                    "text": lead_excerpt(p.text),
                    "source": p.source,
                    "book": p.book,
                    "page": p.page,
                    "systems": list(p.systems),
                    "phase": p.phase,
                    "nature": p.nature,
                    "section": _load_diagram_sections(source).get(p.page),
                }
                for p in g["passages"]
            ],
        })
    return {"source": source, "chapters": chapters}


def _book_chapters(source: str) -> list[dict]:
    """Group a source's prose passages into book-order chapters.

    Returns ``[{topic_key, heading, title, passages: [ProsePassage, …]}]`` in
    document order. Passages are walked in (page, char_offset) order and
    grouped under their printed section heading (``Leçon 7`` / ``Thème 3`` …);
    a page with no section keeps the running heading. Front-matter before the
    first real heading (title page, table of contents, credits) is skipped,
    and move-score dumps with no readable sentence are dropped (``has_prose``).
    Shared by the manual view and the lesson-format endpoints.
    """
    src_upper = source.upper()
    from pedagogy.prose.retrieval import _discover_shards  # noqa: PLC0415

    from .prose_quality import has_prose  # noqa: PLC0415

    passages = []
    for shard in _discover_shards():
        if shard.source != src_upper:
            continue
        passages.extend(shard.passages)
    passages.sort(key=lambda p: (p.page, getattr(p, "char_offset", 0)))

    sections = _load_diagram_sections(source)

    groups: list[dict] = []
    current_heading: str | None = None
    cur: dict | None = None
    seq = 0
    for p in passages:
        if not has_prose(p.text):
            continue
        sec = sections.get(p.page)
        heading = (sec or {}).get("heading") or ""
        title = (sec or {}).get("title") or ""
        if heading:
            if heading != current_heading:
                seq += 1
                current_heading = heading
                cur = {
                    "topic_key": f"section_{seq}",
                    "heading": heading,
                    "title": title,
                    "passages": [],
                }
                groups.append(cur)
        elif cur is None:
            continue  # still in front-matter
        cur["passages"].append(p)
    return [g for g in groups if g["passages"]]


def _theme_chapters(source: str) -> Optional[list[dict]]:
    """Manual-style chapters for a diagram-only *exercise* book.

    Goedemoed's pages carry a study ``theme`` ("Combinaisons", "Calcul",
    "Juger la position"…) instead of a prose ``heading``/``title``, and the
    book has no course text. There is nothing for :func:`_book_chapters` to
    group, so it returns nothing and the manual view is empty.

    Here we synthesise a thematic table of contents instead: every renderable
    diagram is gathered under its theme (themes ordered by first appearance in
    the book), so each theme reads as one chapter — a sequence of study
    positions on the board. Returns ``None`` for ordinary prose sources so
    they keep the heading-based grouping.
    """
    sections = _load_diagram_sections(source)
    if not sections or not any("theme" in (v or {}) for v in sections.values()):
        return None

    by_theme: dict[str, list[tuple[int, int]]] = {}
    first_seen: dict[str, int] = {}
    for (page, number) in sorted(_load_diagram_manifest(source)):
        theme = (sections.get(page) or {}).get("theme")
        if not theme or _fen_for(source, page, number) is None:
            continue
        by_theme.setdefault(theme, []).append((page, number))
        first_seen.setdefault(theme, page)

    return [
        {"theme": theme, "diagrams": by_theme[theme]}
        for theme in sorted(by_theme, key=lambda t: first_seen[t])
    ]


_EXERCISES_PATH = Path(__file__).resolve().parent / "strategy_exercises.json"


@lru_cache(maxsize=8)
def _solution_index(source: str) -> dict:
    """``(page, number) -> {moves, fens, prompt}`` for every exercise whose
    forced solution was mined and verified (see ``build_goedemoed_exercises``).

    Goedemoed is a *recueil d'exercices*: each diagram is a position to solve.
    Here the proven solution line is replayed through the engine so ``fens``
    holds the board after each ply (``fens[0]`` is the start). The reader can
    then step the winning line without re-running the engine per click.
    Diagrams with no proven solution are simply absent from the index.
    """
    try:
        data = json.loads(_EXERCISES_PATH.read_text())
    except (FileNotFoundError, ValueError):
        return {}
    rows = [r for r in data.get("exercises", []) if r.get("source") == source.upper()]
    if not rows:
        return {}

    from game_engine import (  # noqa: PLC0415
        apply_move, board_to_fen, fen_to_board, get_legal_moves,
    )

    out: dict[tuple[int, int], dict] = {}
    for r in rows:
        start = r.get("initial_fen")
        pdn_moves = r.get("solution_moves") or []
        page, number = r.get("page"), r.get("number")
        if not start or not pdn_moves or page is None or number is None:
            continue
        try:
            state = fen_to_board(start)
        except Exception:  # noqa: BLE0001 — a malformed FEN just yields no solution
            continue
        fens, played = [start], []
        for pdn in pdn_moves:
            path = [int(x) for x in re.split(r"[-x]", pdn) if x]
            move = next((m for m in get_legal_moves(state) if m.path == path), None)
            if move is None:  # line diverges from this board — stop, keep prefix
                break
            state = apply_move(state, move)
            fens.append(board_to_fen(state))
            played.append(pdn)
        if not played:
            continue
        side_fr = "blancs" if start[:1].upper() == "W" else "noirs"
        out[(page, number)] = {
            "moves": played,
            "fens": fens,
            "prompt": f"Les {side_fr} jouent et gagnent.",
        }
    return out


# Diagram reference inside the prose: "DIAGRAMME 6" / "diagramme 6".
_PROSE_DIAGRAM_RE = re.compile(r"\bdiagramme\s+(\d+)", re.IGNORECASE)


def _fen_for(source: str, page: int, number: int) -> Optional[str]:
    """Best FEN for a (page, number) diagram, or None when it can't render a
    real board (missing, or an empty 'position in figures'). Human file wins
    over auto; the consolidated library's ``valid`` flag gates auto FENs."""
    fen = _load_diagram_fens(source).get((page, number))
    if fen is None:
        fen = _load_diagram_fens_auto(source).get((page, number))
    if not fen:
        return None
    # Reject blank boards (e.g. "W:W:B"): no men on either side.
    body = fen.upper().replace("W:", "").replace("B:", "")
    if not any(ch.isdigit() for ch in body):
        return None
    from .position_library import get_position  # noqa: PLC0415

    entry = get_position(source, page, number)
    if entry and not entry.get("valid"):
        return None
    return fen


@router.get("/manual-chapters")
def manual_chapters(
    source: str = Query(..., description="Source code, e.g. 'SIJBRANDS'"),
) -> dict:
    """List a strategic manual's chapters in book order (for the table of
    contents). Each entry: ``{index, title, n_passages}``."""
    themed = _theme_chapters(source)
    if themed is not None:
        return {
            "source": source.upper(),
            "chapters": [
                {"index": i, "title": c["theme"], "n_passages": len(c["diagrams"])}
                for i, c in enumerate(themed)
            ],
        }
    groups = _book_chapters(source)
    return {
        "source": source.upper(),
        "chapters": [
            {
                "index": i,
                "title": g["title"] and f"{g['heading']} — {g['title']}" or g["heading"],
                "n_passages": len(g["passages"]),
            }
            for i, g in enumerate(groups)
        ],
    }


@router.get("/manual-lesson")
def manual_lesson(
    source: str = Query(..., description="Source code, e.g. 'SIJBRANDS'"),
    chapter: int = Query(..., ge=0, description="Chapter index from /manual-chapters"),
) -> dict:
    """One chapter of a strategic manual in the *lesson* shape consumed by the
    Débutant ``LessonPanel`` — ``{title, text, diagrams[]}``.

    The chapter's passages are concatenated into one prose blob; each printed
    ``DIAGRAMME N`` reference is rewritten to the Débutant-style ``diag. K``
    (renumbered 1..M within the chapter) and paired with its FEN in
    ``diagrams`` (same row order). Diagrams that can't render a real board
    (missing / empty / invalid FEN) keep their reference as plain text so no
    dead link appears. This makes a scanned manual render identically to the
    Débutant manual: board on top, prose below, clickable diagram links.
    """
    from .prose_quality import lead_excerpt, normalize_whitespace  # noqa: PLC0415

    # Diagram-only exercise books (Goedemoed): a chapter is a study theme, not
    # prose — return its positions as a clickable list of boards.
    themed = _theme_chapters(source)
    if themed is not None:
        if chapter < 0 or chapter >= len(themed):
            raise HTTPException(404, f"chapter {chapter} out of range for {source!r}")
        c = themed[chapter]
        sols = _solution_index(source)
        diagrams = []
        for k, (pg, num) in enumerate(c["diagrams"], start=1):
            sol = sols.get((pg, num))
            # When the solution is known, start from its (side-to-move correct)
            # FEN so the winning line replays cleanly on the board.
            fen = sol["fens"][0] if sol else _fen_for(source, pg, num)
            entry = {
                "ref": f"{source.upper()}_p{pg}_d{num}",
                "fen": fen,
                "label": f"diag. {k}",
            }
            if sol:
                entry["solution"] = {
                    "moves": sol["moves"],
                    "fens": sol["fens"],
                    "prompt": sol["prompt"],
                }
            diagrams.append(entry)
        # Only "diag. N" tokens are clickable; a bare 1-50 anywhere else in the
        # text would be read as a board square, so the prose carries no plain
        # numbers (no count, no page) — the active chip shows the SOURCE_pP_dN
        # reference, which holds the page.
        refs = "  ·  ".join(f"diag. {k}" for k in range(1, len(diagrams) + 1))
        text = (
            f"« {c['theme']} » — recueil d'exercices : à vous de trouver le "
            "meilleur coup. Cliquez une référence pour afficher la position ; "
            "« Voir la solution » dévoile les coups gagnants lorsqu'ils sont "
            f"connus.\n\n{refs}"
        )
        return {
            "title": c["theme"],
            "text": text,
            "diagrams": diagrams,
            "category": f"strategy_{source.lower()}_theme{chapter}",
        }

    groups = _book_chapters(source)
    if chapter < 0 or chapter >= len(groups):
        raise HTTPException(404, f"chapter {chapter} out of range for {source!r}")
    g = groups[chapter]

    diagrams: list[dict] = []
    ref_by_key: dict[tuple[int, int], int] = {}  # (page, number) -> diag.K (1-based)

    def _diag_key(page: int, number: int) -> Optional[int]:
        """Register the (page, number) diagram, returning its 1-based chapter
        index, or None if it has no renderable board. Keyed by (page, number)
        because diagram numbers restart per page."""
        if (page, number) in ref_by_key:
            return ref_by_key[(page, number)]
        fen = _fen_for(source, page, number)
        if fen is None:
            return None
        k = len(diagrams) + 1
        diagrams.append({"ref": f"{source.upper()}_p{page}_d{number}",
                         "fen": fen, "label": f"diag. {k}"})
        ref_by_key[(page, number)] = k
        return k

    manifest = _load_diagram_manifest(source)
    page_numbers: dict[int, list[int]] = {}
    for (pg, num) in manifest:
        page_numbers.setdefault(pg, []).append(num)
    for nums in page_numbers.values():
        nums.sort()

    # How far we've walked through each page's diagrams, and the last one we
    # actually showed there — so successive uncited passages on a page reveal
    # successive positions instead of all repeating its first diagram.
    page_cursor: dict[int, int] = {}
    page_last_k: dict[int, int] = {}

    blocks: list[str] = []
    for p in g["passages"]:
        text = normalize_whitespace(lead_excerpt(p.text))

        cited: list[int] = []

        def _sub(m: "re.Match[str]") -> str:
            number = int(m.group(1))
            k = _diag_key(p.page, number)
            if k is not None:
                cited.append(k)
                return f"diag. {k}"
            return m.group(0)

        text = _PROSE_DIAGRAM_RE.sub(_sub, text)

        # Roozenburg/Keller describe positions in prose without an explicit
        # "DIAGRAMME N". When a passage cites none, attach the next renderable
        # diagram on its page (advancing a per-page cursor, reusing the last
        # once exhausted) and prepend a clickable reference, so the board walks
        # through the page's positions as the prose does rather than freezing
        # on its first diagram.
        if not cited:
            nums = page_numbers.get(p.page, [])
            idx = page_cursor.get(p.page, 0)
            chosen: Optional[int] = None
            while idx < len(nums):
                k = _diag_key(p.page, nums[idx])
                idx += 1
                if k is not None:
                    chosen = k
                    break
            page_cursor[p.page] = idx
            if chosen is None:
                chosen = page_last_k.get(p.page)
            else:
                page_last_k[p.page] = chosen
            if chosen is not None:
                text = f"(diag. {chosen}) {text}"

        blocks.append(text)

    title = g["title"] and f"{g['heading']} — {g['title']}" or g["heading"]
    return {
        "title": title,
        "text": "\n\n".join(blocks),
        "diagrams": diagrams,
        "category": f"strategy_{source.lower()}_ch{chapter}",
    }


@router.get("/diagram-fen")
def diagram_fen(
    source: str = Query(..., description="Source code, e.g. 'SIJBRANDS'"),
    page: int = Query(..., ge=1, description="Page where the diagram is referenced"),
    number: int = Query(..., ge=1, description="Diagram number as printed in the book"),
) -> dict:
    """Return ``{"fen": "...", "kind": "human"|"auto"}`` for a diagram.

    Two-tier lookup:
      1. ``diagrams_fens.json`` — human-verified, the source of truth.
      2. ``diagrams_fens_auto.json`` — output of the rules-based
         detector run on every crop in the manifest (99.87% per-square
         on Sijbrands).  Lets the frontend render an interactive
         ``<Board>`` for diagrams nobody has hand-validated yet.

    For sources in ``_TRUSTED_AUTO_SOURCES`` the auto file is treated
    as authoritative — ``kind`` returns ``"human"`` so the frontend
    doesn't flag the result.  Per-entry human overrides still win.

    404 only when neither file has an entry.

    The response also carries ``valid`` — the engine-validated flag from
    the consolidated position library (parses, 1–20 men a side, has a
    legal move). The frontend uses it to avoid rendering a broken
    ``<Board>`` for the ~3% of auto FENs the detector got wrong.
    """
    def _valid(fen: str) -> bool:
        from .position_library import get_position

        entry = get_position(source, page, number)
        # Library is built from the same manifest+FENs; if the entry is
        # absent (unlikely) treat it as valid rather than hide a board.
        return bool(entry.get("valid")) if entry else True

    fen = _load_diagram_fens(source).get((page, number))
    if fen is not None:
        return {"fen": fen, "source": source, "page": page, "number": number,
                "kind": "human", "valid": _valid(fen)}
    fen = _load_diagram_fens_auto(source).get((page, number))
    if fen is not None:
        kind = "human" if source.upper() in _TRUSTED_AUTO_SOURCES else "auto"
        return {"fen": fen, "source": source, "page": page, "number": number,
                "kind": kind, "valid": _valid(fen)}
    raise HTTPException(
        status_code=404,
        detail=f"no FEN (human or auto) for ({source!r}, p.{page}, #{number})",
    )

