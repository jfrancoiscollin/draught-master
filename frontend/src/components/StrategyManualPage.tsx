import React, { useEffect, useState } from 'react'
import LessonPanel from './LessonPanel'
import { getManualChapters, type ManualChapterSummary } from '../api/client'

interface Props {
  source: string
  onClose: () => void
  lang?: 'fr' | 'en'
}

const SOURCE_LABEL: Record<string, { fr: string; en: string; author?: string }> = {
  SIJBRANDS: { fr: 'Manuel Sijbrands', en: 'Sijbrands Manual', author: 'Ton Sijbrands' },
  SPRINGER: { fr: 'Manuel Springer', en: 'Springer Manual', author: 'Springer' },
  ROOZENBURG: { fr: 'Manuel Roozenburg', en: 'Roozenburg Manual', author: 'Piet Roozenburg' },
  KELLER: { fr: 'Manuel Keller', en: 'Keller Manual', author: 'Keller' },
}

/**
 * Strategic manual — rendered with the SAME view as the Débutant manual.
 *
 * A table of contents lists the book's chapters in order; clicking one opens
 * the shared ``LessonPanel`` (board on top, prose below, clickable ``diag. N``
 * references and clickable square numbers) fed by ``/strategy/manual-lesson``.
 * ‹ Précédent / Suivant › step through the chapters without returning to the
 * list.
 */
const StrategyManualPage: React.FC<Props> = ({ source, onClose, lang = 'fr' }) => {
  const [chapters, setChapters] = useState<ManualChapterSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [openChapter, setOpenChapter] = useState<number | null>(null)
  const label = SOURCE_LABEL[source] ?? { fr: source, en: source }
  const fr = lang !== 'en'

  useEffect(() => {
    setChapters(null)
    setError(null)
    setOpenChapter(null)
    getManualChapters(source)
      .then(setChapters)
      .catch(e => setError(String(e?.message ?? e)))
  }, [source])

  // ── Chapter detail (reuses the Débutant LessonPanel) ──
  if (openChapter !== null && chapters) {
    return (
      <LessonPanel
        key={openChapter}
        chapter={openChapter}
        exampleFen=""
        manualSource={source}
        onClose={() => setOpenChapter(null)}
        onPrev={openChapter > 0 ? () => setOpenChapter(openChapter - 1) : undefined}
        onNext={openChapter < chapters.length - 1 ? () => setOpenChapter(openChapter + 1) : undefined}
        navLabel={`${openChapter + 1} / ${chapters.length}`}
      />
    )
  }

  // ── Table of contents ──
  return (
    <div className="h-full overflow-y-auto bg-gray-900 text-gray-100">
      <header className="sticky top-0 z-10 bg-gray-900 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-amber-500">
            {lang === 'en' ? label.en : label.fr}
          </h1>
          {label.author && <p className="text-xs text-gray-500">{label.author}</p>}
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white"
          aria-label={fr ? 'Fermer' : 'Close'}
        >
          ✕
        </button>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-6">
        {error && <p className="text-sm text-red-400">{error}</p>}
        {!error && !chapters && (
          <p className="text-sm text-gray-500">{fr ? 'Chargement…' : 'Loading…'}</p>
        )}
        {chapters && chapters.length === 0 && (
          <p className="text-sm text-gray-500 italic">
            {fr ? 'Aucun chapitre indexé pour ce manuel.' : 'No chapter indexed for this manual.'}
          </p>
        )}
        <ol className="space-y-2">
          {chapters?.map(ch => (
            <li key={ch.index}>
              <button
                onClick={() => setOpenChapter(ch.index)}
                className="group w-full flex items-center gap-3 rounded-xl border border-gray-700 bg-gray-800 hover:border-amber-600 hover:bg-gray-750 px-4 py-3 text-left transition-all duration-200 cursor-pointer"
              >
                <span className="text-gray-500 text-sm font-mono w-7 shrink-0">{ch.index + 1}.</span>
                <span className="flex-1 min-w-0 font-semibold text-gray-100">{ch.title}</span>
                <span className="ml-auto text-gray-500 group-hover:text-amber-400">→</span>
              </button>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}

export default StrategyManualPage
