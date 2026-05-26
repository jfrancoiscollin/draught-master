import React, { useEffect, useState, useCallback } from 'react'
import {
  listStrategyTopics,
  searchStrategyTopic,
  type StrategyTopic,
  type StrategyPassage,
} from '../api/client'

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

// Captures any explicit mention of "Diagramme N" / "DIAGRAMME N" in
// the passage text. We pick the first match — that's typically the
// diagram the passage is teaching from.
const DIAGRAM_REF_RE = /\b[Dd]iagramme\s+(\d+)/

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
  const [modalImage, setModalImage] = useState<{ src: string; caption: string } | null>(null)

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
        {passages.map(p => {
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
                    onClick={() =>
                      setModalImage({
                        src: `/api/strategy/page-image?source=${encodeURIComponent(p.source)}&page=${p.page}`,
                        caption: diagramNumber
                          ? `${p.source} — ${lang === 'fr' ? 'Diagramme' : 'Diagram'} ${diagramNumber} (page ${p.page})`
                          : `${p.source} — page ${p.page}`,
                      })
                    }
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

      {modalImage && (
        <div
          className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 p-4"
          onClick={() => setModalImage(null)}
        >
          <div
            className="bg-gray-900 rounded-lg p-4 max-w-3xl max-h-[90vh] overflow-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-amber-400 font-semibold text-sm">
                {modalImage.caption}
              </span>
              <button
                onClick={() => setModalImage(null)}
                className="text-gray-400 hover:text-white"
                aria-label={lang === 'fr' ? 'Fermer' : 'Close'}
              >
                ✕
              </button>
            </div>
            <img
              src={modalImage.src}
              alt={modalImage.caption}
              className="max-w-full h-auto"
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default StrategyPanel
