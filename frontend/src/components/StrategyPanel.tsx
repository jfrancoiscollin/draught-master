import React, { useEffect, useState, useCallback, useRef } from 'react'
import {
  listStrategyTopics,
  searchStrategyTopic,
  type StrategyTopic,
  type StrategyPassage,
} from '../api/client'
import Board from './Board'
import FenAnnotator from './FenAnnotator'
import CropTool from './CropTool'
import { PDN_MOVE_RE, replayPdnSequence } from '../utils/pdn'
import { fenToBoard } from '../utils/fen'

interface Props {
  onClose: () => void
  lang?: 'fr' | 'en'
}

// Sources for which we ship rendered PDF page JPGs.  When a passage from
// one of these sources is shown, we offer a "Voir le diagramme" button.
const PAGE_IMAGE_AVAILABLE = new Set([
  'SIJBRANDS',
  'SPRINGER',
  'ROOZENBURG',
  'KELLER',
])

// Captures any explicit mention of "Diagramme N" / "DIAGRAMME N" /
// "diagramme N" in the passage text. We pick the first match — that's
// typically the diagram the passage is teaching from.  The /i flag is
// load-bearing: Sijbrands renders the caption in ALL CAPS ("DIAGRAMME 6"),
// without it the modal would fall back to "Voir la page" + page-image.
const DIAGRAM_REF_RE = /\bdiagramme\s+(\d+)/i

/**
 * Strategy panel — curated topic buttons + sourced passages list.
 *
 * Backed by /api/strategy/*. Each button maps server-side to a
 * "centroid" computed from the prose corpus: clicking it returns the
 * passages most representative of that system. Source + page are
 * displayed verbatim so the reader can cross-reference the original
 * PDF (cf. CADRAGE_STRATEGIE.md §4.S1 — no synthesis without citation).
 */
const StrategyPanel: React.FC<Props> = ({ onClose, lang = 'fr' }) => {
  const [topics, setTopics] = useState<StrategyTopic[]>([])
  const [activeTopic, setActiveTopic] = useState<string | null>(null)
  const [passages, setPassages] = useState<StrategyPassage[]>([])
  const [topicsLoading, setTopicsLoading] = useState(true)
  const [searchLoading, setSearchLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Modal state. We store the index of the focused passage rather than its
  // image URL: that lets ←/→ keys jump between passages without losing the
  // crop/fallback logic, and React remounts the <img> via key={modalIndex}
  // so the data-fallback-used dataset resets between passages.
  const [modalIndex, setModalIndex] = useState<number | null>(null)
  const [zoomed, setZoomed] = useState(false)
  // FEN of the currently focused diagram + provenance.  ``human`` comes
  // from ``diagrams_fens.json`` (validated by JF); ``auto`` from
  // ``diagrams_fens_auto.json`` (rules-based detector run on every crop).
  // The Board renders for either kind; the "⚠ non validé" badge only
  // appears for ``auto``.  Null while loading or when neither file has
  // an entry for this (source, page, number).
  const [modalFen, setModalFen] = useState<{ fen: string; kind: 'human' | 'auto' } | null>(null)
  // Annotation mode replaces the static <Board> by an editable <FenAnnotator>
  // — used when adding a new FEN to diagrams_fens.json without leaving the
  // panel.  Cleared whenever the modal navigates or closes.
  const [annotating, setAnnotating] = useState(false)
  // Move-replay state: which token in the passage text the operator
  // clicked.  ``null`` shows the base FEN of the focused diagram;
  // ``i >= 0`` shows the position *after* the i-th PDN move from the
  // passage (replayed sequentially from the base FEN — see
  // ``utils/pdn.replayPdnSequence``).
  const [replayMoveIndex, setReplayMoveIndex] = useState<number | null>(null)
  // Jump-to-diagram: lets the operator open the modal on any (source, page,
  // number) without going through topic search.  Synthetic passage stored
  // here; when set, the modal renders it instead of passages[modalIndex].
  // No prev/next navigation in jump mode (no passage list).
  const [jumpPassage, setJumpPassage] = useState<StrategyPassage | null>(null)
  const [jumpSource, setJumpSource] = useState('SIJBRANDS')
  const [jumpPage, setJumpPage] = useState('')
  const [jumpNumber, setJumpNumber] = useState('')
  // Manual crop tool — open for sources without an auto-extraction
  // pipeline (Roozenburg / Keller).  When set, fills the screen with
  // a full-page image and lets the operator tap two corners to define
  // a diagram bbox, then copies the JSON manifest entry.
  const [croppingSource, setCroppingSource] = useState<string | null>(null)
  // {page: [number, ...]} index for the *currently selected* source — drives
  // the diagram-number dropdown so operators can only pick (page, number)
  // tuples that have a backing crop.  Fetched on source change and cached
  // per-source in the ref to avoid refetching when toggling back.
  const [jumpIndex, setJumpIndex] = useState<Record<number, number[]>>({})
  const jumpIndexCache = useRef<Record<string, Record<number, number[]>>>({})
  // Diagram number the modal is currently focused on, derived from the
  // passage text *or* (when the passage has no ``Diagramme N`` mention,
  // e.g. on Roozenburg) from the first manifest entry for the passage's
  // page.  Driving the crop URL, FEN fetch, and arrow navigation off
  // this single state lets the same modal logic serve both styles of
  // source — explicit-reference (Sijbrands/Springer) and implicit
  // (Roozenburg, where prose cites move sequences not diagram numbers).
  const [effectiveDiagramNumber, setEffectiveDiagramNumber] = useState<number | null>(null)

  const buildModalContent = useCallback(
    (p: StrategyPassage, diagramNumber: number | null) => {
      const pageUrl = `/api/strategy/page-image?source=${encodeURIComponent(p.source)}&page=${p.page}`
      const cropUrl = diagramNumber !== null
        ? `/api/strategy/diagram?source=${encodeURIComponent(p.source)}&page=${p.page}&number=${diagramNumber}`
        : null
      return {
        src: cropUrl || pageUrl,
        fallback: cropUrl ? pageUrl : undefined,
        caption: diagramNumber !== null
          ? `${p.source} — ${lang === 'fr' ? 'Diagramme' : 'Diagram'} ${diagramNumber} (page ${p.page})`
          : `${p.source} — page ${p.page}`,
      }
    },
    [lang],
  )

  // Reset zoom + annotation when navigating between passages — keeping
  // either active would carry context from the previous diagram into a
  // fresh one.
  useEffect(() => {
    setZoomed(false)
    setAnnotating(false)
    setReplayMoveIndex(null)
  }, [modalIndex, jumpPassage])

  // Fetch the (page → [numbers]) index for the selected source.  Cached so
  // toggling between sources within the session is free.  On cache miss,
  // the dropdown briefly shows "(chargement…)" until the index arrives —
  // tiny payload, runs in parallel with whatever else the user is doing.
  useEffect(() => {
    if (!jumpSource) return
    const cached = jumpIndexCache.current[jumpSource]
    if (cached) {
      setJumpIndex(cached)
      return
    }
    let cancelled = false
    fetch(`/api/strategy/diagram-index?source=${encodeURIComponent(jumpSource)}`)
      .then(r => (r.ok ? r.json() : {}))
      .then((index: Record<string, number[]>) => {
        if (cancelled) return
        // JSON object keys are strings — coerce back to numbers so lookups
        // by `parseInt(jumpPage)` match.
        const coerced: Record<number, number[]> = {}
        for (const [k, v] of Object.entries(index)) coerced[parseInt(k, 10)] = v
        jumpIndexCache.current[jumpSource] = coerced
        setJumpIndex(coerced)
      })
      .catch(() => {
        if (!cancelled) setJumpIndex({})
      })
    return () => {
      cancelled = true
    }
  }, [jumpSource])

  // Clear the diagram number whenever the source or page changes — the
  // previously selected number almost certainly isn't valid for the new
  // (source, page) pair, so leaving it stale would let the user submit a
  // tuple that 404s.
  useEffect(() => {
    setJumpNumber('')
  }, [jumpSource, jumpPage])

  const submitJump = useCallback(() => {
    const page = parseInt(jumpPage, 10)
    const number = parseInt(jumpNumber, 10)
    if (!jumpSource || isNaN(page) || isNaN(number)) return
    // Synthetic passage carries "Diagramme N" in its text so the existing
    // regex match keeps working — that's how the modal derives the crop
    // URL, the FEN fetch key, and the annotator's target number.
    setJumpPassage({
      passage_id: `jump:${jumpSource}:${page}:${number}`,
      score: 0,
      text: `Diagramme ${number}`,
      source: jumpSource,
      book: jumpSource,
      page,
      systems: [],
      phase: null,
      nature: null,
    })
    setModalIndex(null)
  }, [jumpSource, jumpPage, jumpNumber])

  // Single fetch — ``/diagram-fen`` now serves both human-verified
  // (``kind: "human"``) and auto-detected (``kind: "auto"``) FENs,
  // human winning when both exist for the same square.  When ``auto``
  // wins, the modal still renders the Board but shows a badge so the
  // operator knows to validate before trusting it.
  useEffect(() => {
    setModalFen(null)
    const p = jumpPassage ?? (modalIndex !== null ? passages[modalIndex] : null)
    if (!p || effectiveDiagramNumber === null) return
    const qs = `source=${encodeURIComponent(p.source)}&page=${p.page}&number=${effectiveDiagramNumber}`
    const ctrl = new AbortController()
    fetch(`/api/strategy/diagram-fen?${qs}`, { signal: ctrl.signal })
      .then(r => (r.ok ? r.json() : null))
      .then(j => {
        if (j?.fen) setModalFen({ fen: j.fen, kind: j.kind ?? 'human' })
      })
      .catch(() => {})
    return () => ctrl.abort()
  }, [modalIndex, jumpPassage, passages, effectiveDiagramNumber])

  // Compute the effective diagram number for the focused passage AND
  // ensure the source's diagram-index is cached (so arrow navigation
  // works the moment the modal opens).  Three cases:
  //   1. Passage text matches ``DIAGRAMME N`` — use that.
  //   2. No match, but the source has a manifest entry on the passage's
  //      page — use the first one (Roozenburg case: passages cite move
  //      sequences, the actual diagram is anchored by page alone).
  //   3. No match and no manifest coverage for the page — null.  The
  //      modal then falls back to the full page image.
  useEffect(() => {
    const p = jumpPassage ?? (modalIndex !== null ? passages[modalIndex] : null)
    if (!p) {
      setEffectiveDiagramNumber(null)
      return
    }
    const m = p.text.match(DIAGRAM_REF_RE)
    if (m) {
      setEffectiveDiagramNumber(parseInt(m[1], 10))
      return
    }
    const applyFromIndex = (index: Record<number, number[]>) => {
      const nums = index[p.page]
      setEffectiveDiagramNumber(nums && nums.length > 0 ? nums[0] : null)
    }
    const cached = jumpIndexCache.current[p.source]
    if (cached) {
      applyFromIndex(cached)
      return
    }
    if (!PAGE_IMAGE_AVAILABLE.has(p.source)) {
      setEffectiveDiagramNumber(null)
      return
    }
    let cancelled = false
    fetch(`/api/strategy/diagram-index?source=${encodeURIComponent(p.source)}`)
      .then(r => (r.ok ? r.json() : {}))
      .then((index: Record<string, number[]>) => {
        if (cancelled) return
        const coerced: Record<number, number[]> = {}
        for (const [k, v] of Object.entries(index)) coerced[parseInt(k, 10)] = v
        jumpIndexCache.current[p.source] = coerced
        if (p.source === jumpSource) setJumpIndex(coerced)
        applyFromIndex(coerced)
      })
      .catch(() => {
        if (!cancelled) setEffectiveDiagramNumber(null)
      })
    return () => {
      cancelled = true
    }
  }, [modalIndex, jumpPassage, passages, jumpSource])

  // Walk forward/backward through every (page, number) tuple of the
  // *focused* diagram's source.  Works whether the modal was reached
  // via topic search or jump — both eventually look at the same
  // manifest.  Returns null if the focused passage has no diagram
  // reference or if the index isn't cached yet.
  const diagramNeighbour = useCallback(
    (direction: -1 | 1): { page: number; number: number } | null => {
      const p = jumpPassage ?? (modalIndex !== null ? passages[modalIndex] : null)
      if (!p || effectiveDiagramNumber === null) return null
      const index = jumpIndexCache.current[p.source]
      if (!index) return null
      const flat: { page: number; number: number }[] = []
      for (const page of Object.keys(index).map(Number).sort((a, b) => a - b)) {
        for (const number of index[page]) flat.push({ page, number })
      }
      const i = flat.findIndex(
        t => t.page === p.page && t.number === effectiveDiagramNumber,
      )
      if (i < 0) return null
      const j = i + direction
      return j >= 0 && j < flat.length ? flat[j] : null
    },
    [modalIndex, jumpPassage, passages, effectiveDiagramNumber],
  )

  const navigateDiagram = useCallback(
    (direction: -1 | 1) => {
      const target = diagramNeighbour(direction)
      if (!target) return
      const p = jumpPassage ?? (modalIndex !== null ? passages[modalIndex] : null)
      if (!p) return
      // Drop into jump mode regardless of how we got here.  The synthetic
      // passage carries the source/page/number the modal needs; the
      // ``text`` field stays "Diagramme N" so DIAGRAM_REF_RE keeps matching.
      setJumpPassage({
        passage_id: `jump:${p.source}:${target.page}:${target.number}`,
        score: 0,
        text: `Diagramme ${target.number}`,
        source: p.source,
        book: p.book,
        page: target.page,
        systems: [],
        phase: null,
        nature: null,
      })
      setModalIndex(null)
    },
    [diagramNeighbour, modalIndex, jumpPassage, passages],
  )

  // Keyboard shortcuts inside the modal: Esc closes, ←/→ walk the
  // source's diagram manifest when the focused passage references a
  // diagram, and fall back to passage-list navigation (topic mode only)
  // when it doesn't.
  useEffect(() => {
    const open = modalIndex !== null || jumpPassage !== null
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setModalIndex(null)
        setJumpPassage(null)
        return
      }
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
      const direction: -1 | 1 = e.key === 'ArrowLeft' ? -1 : 1
      // Diagram nav first — works in both topic and jump modes.
      if (diagramNeighbour(direction)) {
        navigateDiagram(direction)
        return
      }
      // Passage-level fallback: only meaningful in topic mode for
      // passages that don't reference a diagram.
      if (modalIndex !== null) {
        const next = modalIndex + direction
        if (next >= 0 && next < passages.length) setModalIndex(next)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [modalIndex, jumpPassage, passages, navigateDiagram, diagramNeighbour])

  useEffect(() => {
    let cancelled = false
    setTopicsLoading(true)
    listStrategyTopics()
      .then(ts => {
        if (cancelled) return
        setTopics(ts)
      })
      .catch(e => {
        if (cancelled) return
        setError(lang === 'fr'
          ? `Impossible de charger les sujets : ${e?.message ?? e}`
          : `Failed to load topics: ${e?.message ?? e}`)
      })
      .finally(() => { if (!cancelled) setTopicsLoading(false) })
    return () => { cancelled = true }
  }, [lang])

  const handleTopicClick = useCallback(async (key: string) => {
    setActiveTopic(key)
    setSearchLoading(true)
    setError(null)
    try {
      const result = await searchStrategyTopic(key, 10)
      setPassages(result.passages)
    } catch (e) {
      setError(lang === 'fr'
        ? `Erreur de recherche : ${(e as Error)?.message ?? e}`
        : `Search error: ${(e as Error)?.message ?? e}`)
      setPassages([])
    } finally {
      setSearchLoading(false)
    }
  }, [lang])

  const labelFor = (t: StrategyTopic) =>
    lang === 'fr' ? t.label_fr : t.label_en

  return (
    <div className="h-full flex flex-col bg-gray-900 text-gray-100">
      <header className="flex items-center justify-between border-b border-gray-700 px-4 py-3">
        <h2 className="text-lg font-bold">
          {lang === 'fr' ? 'Concepts stratégiques' : 'Strategic concepts'}
        </h2>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white"
          aria-label={lang === 'fr' ? 'Fermer' : 'Close'}
        >
          ✕
        </button>
      </header>

      <div className="p-4 border-b border-gray-700">
        <p className="text-sm text-gray-400 mb-3">
          {lang === 'fr'
            ? "Sélectionne un thème pour afficher les passages les plus représentatifs du corpus stratégique."
            : "Pick a topic to display the most representative passages from the strategy corpus."}
        </p>
        {topicsLoading ? (
          <p className="text-sm text-gray-500">
            {lang === 'fr' ? 'Chargement…' : 'Loading…'}
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {topics.map(t => (
              <button
                key={t.key}
                disabled={!t.available || searchLoading}
                onClick={() => handleTopicClick(t.key)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors
                  ${activeTopic === t.key
                    ? 'bg-amber-600 text-white'
                    : 'bg-gray-800 text-gray-200 hover:bg-gray-700'}
                  disabled:opacity-50 disabled:cursor-not-allowed`}
                title={t.description_fr}
              >
                {labelFor(t)}
              </button>
            ))}
          </div>
        )}
        {/* Jump-to-diagram: opens the modal directly on any (source, page,
            number) without going through topic search.  Useful for the
            FEN annotation workflow where the operator wants to cover
            specific diagrams that no curated topic surfaces. */}
        <form
          onSubmit={e => {
            e.preventDefault()
            submitJump()
          }}
          className="flex flex-wrap items-center gap-2 text-xs text-gray-400 pt-1"
        >
          <span className="text-[10px] uppercase tracking-wide">
            {lang === 'fr' ? 'Aller à un diagramme :' : 'Jump to diagram:'}
          </span>
          <select
            value={jumpSource}
            onChange={e => setJumpSource(e.target.value)}
            className="bg-gray-800 text-gray-100 rounded px-2 py-1 border border-gray-700"
          >
            <option value="SIJBRANDS">SIJBRANDS</option>
            <option value="SPRINGER">SPRINGER</option>
            <option value="ROOZENBURG">ROOZENBURG</option>
            <option value="KELLER">KELLER</option>
            <option value="GOEDEMOED">GOEDEMOED</option>
          </select>
          <input
            type="number"
            min={1}
            value={jumpPage}
            onChange={e => setJumpPage(e.target.value)}
            placeholder={lang === 'fr' ? 'page' : 'page'}
            className="bg-gray-800 text-gray-100 rounded px-2 py-1 border border-gray-700 w-20"
          />
          {(() => {
            const pageNum = parseInt(jumpPage, 10)
            const numbers = !isNaN(pageNum) ? jumpIndex[pageNum] : undefined
            // Empty placeholder distinguishes "no page typed yet" from
            // "page typed but no crops on it" — different prompts help
            // the operator understand why no numbers are listed.
            const placeholder = !jumpPage
              ? lang === 'fr' ? 'page ?' : 'page?'
              : numbers && numbers.length > 0
              ? '#'
              : lang === 'fr' ? '(aucun)' : '(none)'
            return (
              <select
                value={jumpNumber}
                onChange={e => setJumpNumber(e.target.value)}
                disabled={!numbers || numbers.length === 0}
                className="bg-gray-800 text-gray-100 rounded px-2 py-1 border border-gray-700 w-20 disabled:opacity-50"
              >
                <option value="">{placeholder}</option>
                {numbers?.map(n => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            )
          })()}
          <button
            type="submit"
            disabled={!jumpPage || !jumpNumber}
            className="px-2 py-1 bg-amber-700 hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs rounded font-medium"
          >
            {lang === 'fr' ? 'Voir' : 'Open'}
          </button>
          {/* Manual crop tool for sources without an auto-extracted
              manifest.  Click → fullscreen page-image + 2-tap bbox
              capture → copy JSON manifest entry. */}
          <button
            type="button"
            onClick={() => setCroppingSource(jumpSource)}
            className="px-2 py-1 text-amber-400 hover:text-amber-300 text-xs underline"
            title={lang === 'fr' ? 'Crop manuel d’un diagramme' : 'Manual diagram crop'}
          >
            {lang === 'fr' ? '✂ crop' : '✂ crop'}
          </button>
        </form>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {error && (
          <div className="rounded-md border border-red-700 bg-red-900/30 px-3 py-2 text-sm text-red-200">
            {error}
          </div>
        )}
        {searchLoading && (
          <p className="text-sm text-gray-500">
            {lang === 'fr' ? 'Recherche…' : 'Searching…'}
          </p>
        )}
        {!searchLoading && activeTopic === null && !error && (
          <p className="text-sm text-gray-500 italic">
            {lang === 'fr'
              ? 'Aucun thème sélectionné.'
              : 'No topic selected.'}
          </p>
        )}
        {!searchLoading && activeTopic !== null && passages.length === 0 && !error && (
          <p className="text-sm text-gray-500 italic">
            {lang === 'fr' ? 'Aucun passage trouvé.' : 'No passages found.'}
          </p>
        )}
        {passages.map((p, idx) => {
          const diagramMatch = p.text.match(DIAGRAM_REF_RE)
          const showImageBtn = PAGE_IMAGE_AVAILABLE.has(p.source)
          const diagramNumber = diagramMatch ? diagramMatch[1] : null
          return (
            <article
              key={p.passage_id}
              className="rounded-md border border-gray-700 px-3 py-2"
              style={{ backgroundColor: 'rgb(28, 32, 40)' }}
            >
              <header className="flex items-baseline justify-between gap-2 mb-1">
                <span className="text-xs uppercase tracking-wide text-amber-400 font-semibold">
                  {p.source}
                </span>
                <span className="text-xs text-gray-500">
                  {lang === 'fr' ? 'page' : 'p.'} {p.page} · score {p.score.toFixed(3)}
                </span>
              </header>
              <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
                {p.text}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-gray-500">
                {p.systems.map(s => (
                  <span key={s} className="px-1.5 py-0.5 bg-gray-800 rounded">
                    {s}
                  </span>
                ))}
                {p.phase && (
                  <span className="px-1.5 py-0.5 bg-gray-800 rounded">{p.phase}</span>
                )}
                {p.nature && (
                  <span className="px-1.5 py-0.5 bg-gray-800 rounded">{p.nature}</span>
                )}
                {showImageBtn && (
                  <button
                    onClick={() => setModalIndex(idx)}
                    className="ml-auto px-2 py-1 bg-amber-700 hover:bg-amber-600 text-white text-xs rounded-md font-medium"
                  >
                    {lang === 'fr'
                      ? (diagramNumber ? `Voir Diagramme ${diagramNumber}` : 'Voir la page')
                      : (diagramNumber ? `View Diagram ${diagramNumber}` : 'View page')}
                  </button>
                )}
              </div>
            </article>
          )
        })}
      </div>

      {(() => {
        const focusedPassage =
          jumpPassage ?? (modalIndex !== null ? passages[modalIndex] : null)
        if (!focusedPassage) return null
        const modal = buildModalContent(focusedPassage, effectiveDiagramNumber)
        // Prev/next ALWAYS walk the source manifest when the focused
        // passage references a diagram — regardless of whether the user
        // reached the modal via topic search or via jump.  This is the
        // navigation the operator wants when annotating a series of
        // diagrams.  Topic mode only falls back to passage-list nav
        // when the focused passage has no diagram reference.
        const inJump = jumpPassage !== null
        const inTopic = jumpPassage === null && modalIndex !== null
        const hasDiagramNav = diagramNeighbour(-1) !== null || diagramNeighbour(1) !== null
        const hasPrev = hasDiagramNav
          ? diagramNeighbour(-1) !== null
          : inTopic && modalIndex! > 0
        const hasNext = hasDiagramNav
          ? diagramNeighbour(1) !== null
          : inTopic && modalIndex! < passages.length - 1
        const goPrev = () => {
          if (hasDiagramNav) navigateDiagram(-1)
          else if (inTopic) setModalIndex(modalIndex! - 1)
        }
        const goNext = () => {
          if (hasDiagramNav) navigateDiagram(1)
          else if (inTopic) setModalIndex(modalIndex! + 1)
        }
        const diagramNumber = effectiveDiagramNumber
        const canAnnotate = diagramNumber !== null
        const closeModal = () => {
          setModalIndex(null)
          setJumpPassage(null)
        }
        return (
          <div
            className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 p-4"
            onClick={closeModal}
          >
            <div
              className={`bg-gray-900 rounded-lg p-4 ${zoomed ? 'max-w-[95vw] max-h-[95vh]' : 'max-w-3xl max-h-[90vh]'} overflow-auto`}
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-3 gap-2">
                <span className="text-amber-400 font-semibold text-sm">
                  {modal.caption}
                </span>
                <div className="flex items-center gap-1 text-xs text-gray-400">
                  {inTopic && (
                    <span>
                      {modalIndex! + 1} / {passages.length}
                    </span>
                  )}
                  {(inTopic || inJump) && (
                    <>
                      <button
                        onClick={goPrev}
                        disabled={!hasPrev}
                        className="px-2 py-1 rounded hover:bg-gray-800 disabled:opacity-30 disabled:hover:bg-transparent"
                        aria-label={lang === 'fr' ? 'Précédent' : 'Previous'}
                        title="←"
                      >
                        ←
                      </button>
                      <button
                        onClick={goNext}
                        disabled={!hasNext}
                        className="px-2 py-1 rounded hover:bg-gray-800 disabled:opacity-30 disabled:hover:bg-transparent"
                        aria-label={lang === 'fr' ? 'Suivant' : 'Next'}
                        title="→"
                      >
                        →
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => setZoomed(z => !z)}
                    className="px-2 py-1 rounded hover:bg-gray-800"
                    aria-label={lang === 'fr' ? 'Zoom' : 'Zoom'}
                    title={zoomed ? '−' : '+'}
                  >
                    {zoomed ? '−' : '+'}
                  </button>
                  {canAnnotate && (
                    <button
                      onClick={() => setAnnotating(a => !a)}
                      className={`px-2 py-1 rounded text-[11px] font-medium ${
                        annotating
                          ? 'bg-amber-600 text-white hover:bg-amber-500'
                          : 'text-amber-400 hover:bg-gray-800'
                      }`}
                      title={lang === 'fr' ? 'Mode annotation FEN' : 'FEN annotation mode'}
                    >
                      {annotating
                        ? lang === 'fr' ? '✎ stop' : '✎ stop'
                        : lang === 'fr' ? '✎ annoter' : '✎ annotate'}
                    </button>
                  )}
                  <button
                    onClick={closeModal}
                    className="px-2 py-1 rounded hover:bg-gray-800"
                    aria-label={lang === 'fr' ? 'Fermer (Esc)' : 'Close (Esc)'}
                    title="Esc"
                  >
                    ✕
                  </button>
                </div>
              </div>
              {/* Lesson-style stack: Board on top, prose with clickable
                  moves below.  No printed crop — every diagram is now
                  trusted-auto across the four sources, so the Board is
                  always the source of truth.  Click any PDN token in
                  the prose ("33-29", "18x29", "20x31x42") to replay
                  the moves from the base FEN up to that point and show
                  the resulting position. */}
              {annotating && diagramNumber !== null ? (
                <div className="flex flex-wrap items-start gap-4">
                  <img
                    key={modalIndex}
                    src={modal.src}
                    alt={modal.caption}
                    className={
                      zoomed
                        ? 'cursor-zoom-out'
                        : 'max-w-xs h-auto cursor-zoom-in'
                    }
                    onClick={() => setZoomed(z => !z)}
                    onError={e => {
                      const img = e.currentTarget
                      if (modal.fallback && img.dataset.fallbackUsed !== 'true') {
                        img.dataset.fallbackUsed = 'true'
                        img.src = modal.fallback
                      }
                    }}
                  />
                  <div className="flex-1 min-w-[280px]">
                    {modalFen?.kind === 'auto' && (
                      <div className="mb-2 text-[11px] text-amber-300 bg-amber-900/30 border border-amber-700/50 rounded px-2 py-1">
                        {lang === 'fr'
                          ? '⚠ Pré-rempli par détection auto — vérifier chaque case avant copie.'
                          : '⚠ Pre-filled by auto-detector — verify each square before copying.'}
                      </div>
                    )}
                    <FenAnnotator
                      source={focusedPassage.source}
                      page={focusedPassage.page}
                      number={diagramNumber}
                      initialFen={modalFen?.fen}
                      onClose={() => setAnnotating(false)}
                      lang={lang}
                    />
                  </div>
                </div>
              ) : modalFen ? (
                (() => {
                  // Tokenize the passage prose into a mix of text and
                  // PDN move tokens.  Each move keeps its ordinal in
                  // the sequence so clicking it replays the right
                  // prefix from the base FEN.
                  const baseBoard = fenToBoard(modalFen.fen)
                  const text = focusedPassage.text
                  type Tok =
                    | { kind: 'text'; text: string }
                    | { kind: 'move'; text: string; index: number }
                  const tokens: Tok[] = []
                  const moves: string[] = []
                  PDN_MOVE_RE.lastIndex = 0
                  let cursor = 0
                  let m: RegExpExecArray | null
                  while ((m = PDN_MOVE_RE.exec(text)) !== null) {
                    if (m.index > cursor) {
                      tokens.push({ kind: 'text', text: text.slice(cursor, m.index) })
                    }
                    tokens.push({ kind: 'move', text: m[0], index: moves.length })
                    moves.push(m[0])
                    cursor = m.index + m[0].length
                  }
                  if (cursor < text.length) {
                    tokens.push({ kind: 'text', text: text.slice(cursor) })
                  }
                  const displayed =
                    replayMoveIndex === null
                      ? baseBoard
                      : replayPdnSequence(baseBoard, moves.slice(0, replayMoveIndex + 1)).board
                  return (
                    <div className="flex flex-col gap-3 items-stretch">
                      <div className="flex items-center justify-between gap-2 text-[10px] uppercase tracking-wide text-gray-500">
                        <span>
                          {lang === 'fr' ? 'Plateau interactif' : 'Interactive board'}
                          {replayMoveIndex !== null && (
                            <> · {lang === 'fr' ? 'après' : 'after'} <span className="text-amber-400">{moves[replayMoveIndex]}</span></>
                          )}
                        </span>
                        {replayMoveIndex !== null && (
                          <button
                            onClick={() => setReplayMoveIndex(null)}
                            className="text-amber-400 hover:text-amber-300 text-[10px] underline normal-case tracking-normal"
                          >
                            {lang === 'fr' ? '↺ position initiale' : '↺ initial position'}
                          </button>
                        )}
                      </div>
                      <Board
                        board={displayed}
                        legalMoves={[]}
                        onMove={() => {}}
                        selectedSquare={null}
                        onSelectSquare={() => {}}
                        disabled
                      />
                      {jumpPassage === null && (
                        <p className="text-xs text-gray-200 leading-relaxed max-h-48 overflow-auto border-t border-gray-700 pt-2">
                          {tokens.map((t, i) =>
                            t.kind === 'text' ? (
                              <span key={i}>{t.text}</span>
                            ) : (
                              <button
                                key={i}
                                onClick={() => setReplayMoveIndex(t.index)}
                                className={`mx-0.5 px-1 rounded font-medium ${
                                  replayMoveIndex === t.index
                                    ? 'bg-amber-600 text-white'
                                    : 'text-amber-400 hover:bg-amber-900/40'
                                }`}
                                title={
                                  lang === 'fr'
                                    ? 'Voir la position après ce coup'
                                    : 'Show the position after this move'
                                }
                              >
                                {t.text}
                              </button>
                            ),
                          )}
                        </p>
                      )}
                    </div>
                  )
                })()
              ) : (
                <p className="text-xs text-gray-400 italic">
                  {lang === 'fr'
                    ? 'Position non disponible pour ce diagramme.'
                    : 'Position not available for this diagram.'}
                </p>
              )}
            </div>
          </div>
        )
      })()}
      {croppingSource && (
        <CropTool
          source={croppingSource}
          initialPage={parseInt(jumpPage, 10) || undefined}
          onClose={() => setCroppingSource(null)}
          lang={lang}
        />
      )}
    </div>
  )
}

export default StrategyPanel
