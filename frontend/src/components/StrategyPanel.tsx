import React, { useEffect, useState, useCallback } from 'react'
import {
  listStrategyTopics,
  searchStrategyTopic,
  type StrategyTopic,
  type StrategyPassage,
} from '../api/client'
import Board from './Board'
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
  // FEN of the currently focused diagram, when manually annotated in the
  // diagrams_fens.json file of its source.  Null while loading or when the
  // endpoint 404s (no annotation yet) — frontend shows the crop alone.
  const [modalFen, setModalFen] = useState<string | null>(null)

  const buildModalContent = useCallback(
    (p: StrategyPassage) => {
      const diagramMatch = p.text.match(DIAGRAM_REF_RE)
      const diagramNumber = diagramMatch ? diagramMatch[1] : null
      const pageUrl = `/api/strategy/page-image?source=${encodeURIComponent(p.source)}&page=${p.page}`
      const cropUrl = diagramNumber
        ? `/api/strategy/diagram?source=${encodeURIComponent(p.source)}&page=${p.page}&number=${diagramNumber}`
        : null
      return {
        src: cropUrl || pageUrl,
        fallback: cropUrl ? pageUrl : undefined,
        caption: diagramNumber
          ? `${p.source} — ${lang === 'fr' ? 'Diagramme' : 'Diagram'} ${diagramNumber} (page ${p.page})`
          : `${p.source} — page ${p.page}`,
      }
    },
    [lang],
  )

  // Reset zoom when navigating between passages — keeping it stretched on a
  // smaller crop than the previous one would dump the user off-screen.
  useEffect(() => {
    setZoomed(false)
  }, [modalIndex])

  // Try to load a manually annotated FEN for the focused passage. Most
  // diagrams aren't annotated yet (Lane C is a long manual effort) so 404s
  // are expected and silent.  We abort on unmount/navigation to prevent
  // a late response from overwriting a newer one.
  useEffect(() => {
    setModalFen(null)
    if (modalIndex === null) return
    const p = passages[modalIndex]
    if (!p) return
    const diagramMatch = p.text.match(DIAGRAM_REF_RE)
    if (!diagramMatch) return
    const ctrl = new AbortController()
    fetch(
      `/api/strategy/diagram-fen?source=${encodeURIComponent(p.source)}&page=${p.page}&number=${diagramMatch[1]}`,
      { signal: ctrl.signal },
    )
      .then(r => (r.ok ? r.json() : null))
      .then(j => {
        if (j?.fen) setModalFen(j.fen)
      })
      .catch(() => {
        /* aborted or network error — keep modalFen null, the crop alone is fine */
      })
    return () => ctrl.abort()
  }, [modalIndex, passages])

  // Keyboard shortcuts inside the modal: Esc closes, ←/→ navigate to the
  // previous/next passage with a diagram button (all sources have one now,
  // so any adjacent passage works).
  useEffect(() => {
    if (modalIndex === null) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setModalIndex(null)
      } else if (e.key === 'ArrowLeft' && modalIndex > 0) {
        setModalIndex(modalIndex - 1)
      } else if (e.key === 'ArrowRight' && modalIndex < passages.length - 1) {
        setModalIndex(modalIndex + 1)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [modalIndex, passages.length])

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

      {modalIndex !== null && passages[modalIndex] && (() => {
        const focusedPassage = passages[modalIndex]
        const modal = buildModalContent(focusedPassage)
        const hasPrev = modalIndex > 0
        const hasNext = modalIndex < passages.length - 1
        return (
          <div
            className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 p-4"
            onClick={() => setModalIndex(null)}
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
                  <span>
                    {modalIndex + 1} / {passages.length}
                  </span>
                  <button
                    onClick={() => setModalIndex(modalIndex - 1)}
                    disabled={!hasPrev}
                    className="px-2 py-1 rounded hover:bg-gray-800 disabled:opacity-30 disabled:hover:bg-transparent"
                    aria-label={lang === 'fr' ? 'Précédent' : 'Previous'}
                    title="←"
                  >
                    ←
                  </button>
                  <button
                    onClick={() => setModalIndex(modalIndex + 1)}
                    disabled={!hasNext}
                    className="px-2 py-1 rounded hover:bg-gray-800 disabled:opacity-30 disabled:hover:bg-transparent"
                    aria-label={lang === 'fr' ? 'Suivant' : 'Next'}
                    title="→"
                  >
                    →
                  </button>
                  <button
                    onClick={() => setZoomed(z => !z)}
                    className="px-2 py-1 rounded hover:bg-gray-800"
                    aria-label={lang === 'fr' ? 'Zoom' : 'Zoom'}
                    title={zoomed ? '−' : '+'}
                  >
                    {zoomed ? '−' : '+'}
                  </button>
                  <button
                    onClick={() => setModalIndex(null)}
                    className="px-2 py-1 rounded hover:bg-gray-800"
                    aria-label={lang === 'fr' ? 'Fermer (Esc)' : 'Close (Esc)'}
                    title="Esc"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div className={modalFen ? 'flex flex-wrap items-start gap-4' : ''}>
                <img
                  key={modalIndex}
                  src={modal.src}
                  alt={modal.caption}
                  className={
                    zoomed
                      ? 'cursor-zoom-out'
                      : `${modalFen ? 'max-w-xs' : 'max-w-full'} h-auto cursor-zoom-in`
                  }
                  onClick={() => setZoomed(z => !z)}
                  onError={e => {
                    // Crop endpoint 404s for ~30% of (page, number) pairs that
                    // weren't extracted — swap to full-page image once.  The
                    // key={modalIndex} above resets data-fallback-used between
                    // passages so each one gets its own chance.
                    const img = e.currentTarget
                    if (modal.fallback && img.dataset.fallbackUsed !== 'true') {
                      img.dataset.fallbackUsed = 'true'
                      img.src = modal.fallback
                    }
                  }}
                />
                {modalFen && (
                  <div className="flex-1 min-w-[280px]">
                    <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1">
                      {lang === 'fr' ? 'Plateau interactif' : 'Interactive board'}
                    </div>
                    <Board
                      board={fenToBoard(modalFen)}
                      legalMoves={[]}
                      onMove={() => {}}
                      selectedSquare={null}
                      onSelectSquare={() => {}}
                      disabled
                    />
                  </div>
                )}
              </div>
              <p className="mt-3 text-xs text-gray-200 leading-relaxed max-h-32 overflow-auto border-t border-gray-700 pt-2">
                {focusedPassage.text}
              </p>
            </div>
          </div>
        )
      })()}
    </div>
  )
}

export default StrategyPanel
