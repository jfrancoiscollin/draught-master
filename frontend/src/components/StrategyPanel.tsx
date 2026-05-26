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
        {passages.map(p => (
          <article
            key={p.passage_id}
            className="rounded-md border border-gray-700 bg-gray-850 px-3 py-2"
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
            {(p.phase || p.nature || p.systems.length > 0) && (
              <footer className="mt-2 flex flex-wrap gap-1.5 text-[10px] text-gray-500">
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
              </footer>
            )}
          </article>
        ))}
      </div>
    </div>
  )
}

export default StrategyPanel
