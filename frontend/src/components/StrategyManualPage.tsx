import React, { useEffect, useMemo, useState } from 'react'
import Board from './Board'
import { fenToBoard } from '../utils/fen'
import { PDN_MOVE_RE, replayPdnSequence } from '../utils/pdn'
import { type StrategyPassage } from '../api/client'

interface Chapter {
  topic_key: string
  title_fr: string
  title_en: string
  description_fr: string
  passages: StrategyPassage[]
}

interface ManualResponse {
  source: string
  chapters: Chapter[]
}

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
 * Strategic manual rendered as a long-form pedagogical document.
 *
 * One manual per source (Sijbrands / Springer / Roozenburg / Keller).
 * The corpus is grouped into chapters by topic centroid match and
 * rendered top-down: chapter title, chapter description, then each
 * passage as a section card with the diagram's Board on top and the
 * prose below.  Every PDN move in the prose is a button — clicking
 * replays the sequence from the diagram's FEN and shows the resulting
 * position on that section's Board (per-section state so each passage
 * has its own independent move cursor).
 */
const StrategyManualPage: React.FC<Props> = ({ source, onClose, lang = 'fr' }) => {
  const [manual, setManual] = useState<ManualResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setManual(null)
    setError(null)
    const ctrl = new AbortController()
    fetch(`/api/strategy/manual?source=${encodeURIComponent(source)}`, {
      signal: ctrl.signal,
    })
      .then(r => {
        if (!r.ok) throw new Error(`${r.status}`)
        return r.json()
      })
      .then(setManual)
      .catch(e => {
        if (e?.name !== 'AbortError') {
          setError(
            lang === 'fr'
              ? `Impossible de charger le manuel : ${e?.message ?? e}`
              : `Failed to load manual: ${e?.message ?? e}`,
          )
        }
      })
    return () => ctrl.abort()
  }, [source, lang])

  const label = SOURCE_LABEL[source] ?? { fr: source, en: source }

  return (
    <div className="h-full overflow-y-auto bg-gray-900 text-gray-100">
      <header className="sticky top-0 z-10 bg-gray-900 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-amber-500">
            {lang === 'en' ? label.en : label.fr}
          </h1>
          {label.author && (
            <p className="text-xs text-gray-500">{label.author}</p>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white"
          aria-label={lang === 'fr' ? 'Fermer' : 'Close'}
        >
          ✕
        </button>
      </header>
      <div className="max-w-2xl mx-auto px-4 py-6 space-y-10">
        {error && (
          <p className="text-sm text-red-400">{error}</p>
        )}
        {!error && !manual && (
          <p className="text-sm text-gray-500">
            {lang === 'fr' ? 'Chargement…' : 'Loading…'}
          </p>
        )}
        {manual?.chapters.length === 0 && (
          <p className="text-sm text-gray-500 italic">
            {lang === 'fr'
              ? 'Aucun passage indexé pour ce manuel.'
              : 'No passage indexed for this manual.'}
          </p>
        )}
        {manual?.chapters.map((chapter, ci) => (
          <ChapterSection key={chapter.topic_key} chapter={chapter} index={ci + 1} lang={lang} />
        ))}
      </div>
    </div>
  )
}

const ChapterSection: React.FC<{ chapter: Chapter; index: number; lang: 'fr' | 'en' }> = ({
  chapter,
  index,
  lang,
}) => {
  return (
    <section>
      <h2 className="text-base font-bold text-white border-l-4 border-amber-500 pl-3 mb-1">
        {lang === 'en' ? chapter.title_en : chapter.title_fr}
      </h2>
      <p className="text-xs text-gray-500 mb-4">
        {lang === 'en' ? `Chapter ${index}` : `Chapitre ${index}`}
        {chapter.description_fr && lang === 'fr' && (
          <> · {chapter.description_fr}</>
        )}
      </p>
      <div className="space-y-6">
        {chapter.passages.map((p, pi) => (
          <PassageCard key={p.passage_id} passage={p} index={pi + 1} lang={lang} />
        ))}
      </div>
    </section>
  )
}

// Captures explicit diagram references in the passage text — same
// regex as the StrategyPanel modal.  ``DIAGRAMME 6`` / ``diagramme 6``
// case-insensitive.  Used to fetch the position FEN for the Board.
const DIAGRAM_REF_RE = /\bdiagramme\s+(\d+)/i

const PassageCard: React.FC<{ passage: StrategyPassage; index: number; lang: 'fr' | 'en' }> = ({
  passage,
  index,
  lang,
}) => {
  const [fen, setFen] = useState<string | null>(null)
  const [replayMoveIndex, setReplayMoveIndex] = useState<number | null>(null)

  // Derive the diagram number from the prose ("Diagramme N") or fall
  // back to the first diagram on the passage's page (Roozenburg/Keller
  // style — passages cite move sequences, not diagram numbers).
  const diagramMatch = passage.text.match(DIAGRAM_REF_RE)
  const explicitNumber = diagramMatch ? parseInt(diagramMatch[1], 10) : null

  useEffect(() => {
    setFen(null)
    setReplayMoveIndex(null)
    if (explicitNumber !== null) {
      const qs = `source=${encodeURIComponent(passage.source)}&page=${passage.page}&number=${explicitNumber}`
      fetch(`/api/strategy/diagram-fen?${qs}`)
        .then(r => (r.ok ? r.json() : null))
        .then(j => {
          if (j?.fen) setFen(j.fen)
        })
        .catch(() => {})
      return
    }
    // Fallback: ask the diagram-index for the first diagram on this page
    fetch(`/api/strategy/diagram-index?source=${encodeURIComponent(passage.source)}`)
      .then(r => (r.ok ? r.json() : {}))
      .then((idx: Record<string, number[]>) => {
        const nums = idx[String(passage.page)]
        if (nums && nums.length > 0) {
          const qs = `source=${encodeURIComponent(passage.source)}&page=${passage.page}&number=${nums[0]}`
          return fetch(`/api/strategy/diagram-fen?${qs}`)
            .then(r => (r.ok ? r.json() : null))
            .then(j => {
              if (j?.fen) setFen(j.fen)
            })
        }
      })
      .catch(() => {})
  }, [passage.passage_id, explicitNumber, passage.source, passage.page])

  // Tokenize prose into text + clickable PDN move tokens (independent
  // of whether the Board is available — even without an FEN, the
  // user can still read the prose).
  const { tokens, moves } = useMemo(() => {
    const text = passage.text
    type Tok =
      | { kind: 'text'; text: string }
      | { kind: 'move'; text: string; index: number }
    const t: Tok[] = []
    const m: string[] = []
    PDN_MOVE_RE.lastIndex = 0
    let cursor = 0
    let match: RegExpExecArray | null
    while ((match = PDN_MOVE_RE.exec(text)) !== null) {
      if (match.index > cursor) {
        t.push({ kind: 'text', text: text.slice(cursor, match.index) })
      }
      t.push({ kind: 'move', text: match[0], index: m.length })
      m.push(match[0])
      cursor = match.index + match[0].length
    }
    if (cursor < text.length) {
      t.push({ kind: 'text', text: text.slice(cursor) })
    }
    return { tokens: t, moves: m }
  }, [passage.text])

  const baseBoard = fen ? fenToBoard(fen) : null
  const displayedBoard = useMemo(() => {
    if (!baseBoard) return null
    if (replayMoveIndex === null) return baseBoard
    return replayPdnSequence(baseBoard, moves.slice(0, replayMoveIndex + 1)).board
  }, [baseBoard, moves, replayMoveIndex])

  const sectionTitle = explicitNumber !== null
    ? `${lang === 'fr' ? 'Diagramme' : 'Diagram'} ${explicitNumber} · ${lang === 'fr' ? 'page' : 'page'} ${passage.page}`
    : `${lang === 'fr' ? 'Section' : 'Section'} ${index} · ${lang === 'fr' ? 'page' : 'page'} ${passage.page}`

  return (
    <article className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-4">
      <h3 className="text-sm font-semibold text-amber-400 mb-3">
        {sectionTitle}
      </h3>
      {displayedBoard && (
        <div className="mb-3">
          <div className="flex items-center justify-between gap-2 text-[10px] uppercase tracking-wide text-gray-500 mb-1">
            <span>
              {replayMoveIndex !== null
                ? <>{lang === 'fr' ? 'Après' : 'After'} <span className="text-amber-400">{moves[replayMoveIndex]}</span></>
                : (lang === 'fr' ? 'Position initiale' : 'Initial position')}
            </span>
            {replayMoveIndex !== null && (
              <button
                onClick={() => setReplayMoveIndex(null)}
                className="text-amber-400 hover:text-amber-300 text-[10px] underline normal-case tracking-normal"
              >
                {lang === 'fr' ? '↺ initial' : '↺ initial'}
              </button>
            )}
          </div>
          <Board
            board={displayedBoard}
            legalMoves={[]}
            onMove={() => {}}
            selectedSquare={null}
            onSelectSquare={() => {}}
            disabled
          />
        </div>
      )}
      {!displayedBoard && (
        <p className="text-[11px] text-gray-500 italic mb-3">
          {lang === 'fr' ? 'Position indisponible.' : 'Position unavailable.'}
        </p>
      )}
      <div className="text-sm text-gray-200 leading-relaxed">
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
                  : 'Show position after this move'
              }
            >
              {t.text}
            </button>
          ),
        )}
      </div>
    </article>
  )
}

export default StrategyManualPage
