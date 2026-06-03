import React, { useState, useEffect, useRef } from 'react'
import type { ExerciseResponse, ExerciseCheckResponse } from '../types'
import { getExercises, getUserProgress, getLessonTitles, getReadLessons } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'

interface ExercisePanelProps {
  onExerciseLoad: (fen: string, exerciseId: number) => void
  onLessonOpen?: (chapter: number, fen: string) => void
  currentExerciseId: number | null
  feedback: ExerciseCheckResponse | null
  compact?: boolean
  readChapters?: Set<number>
  bookId?: string
}

function Stars({ count }: { count: number }) {
  return (
    <span className="flex-shrink-0 text-xs tracking-tight">
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={i < count ? 'text-amber-400' : 'text-gray-600'}>★</span>
      ))}
    </span>
  )
}

// Strip the chapter-title prefix: "COMBINAISONS EN 2 TEMPS – D1" → "D1"
function shortName(name: string): string {
  const idx = name.indexOf('–')
  if (idx !== -1) return name.slice(idx + 1).trim()
  const idx2 = name.lastIndexOf(' - ')
  if (idx2 !== -1) return name.slice(idx2 + 3).trim()
  return name
}

// Some books re-key their lesson prose to a dedicated id range to avoid
// colliding with other books on the shared /api/lessons/{chapter} endpoint
// (the exercise's parsed chapter stays 1..N, but the prose lives at offset+N).
// Mirrors backend combinaisons_loader.COMBINAISONS_CHAPTER_OFFSET / sens-du-jeu.
const LESSON_ID_OFFSET: Record<string, number> = {
  manuel_dubois_combinaisons: 200,
  manuel_dubois_sens_du_jeu: 100,
}

export default function ExercisePanel({
  onExerciseLoad,
  onLessonOpen,
  currentExerciseId,
  feedback,
  compact = true,
  readChapters = new Set(),
  bookId = '',
}: ExercisePanelProps) {
  const { t } = useLanguage()
  const { user } = useAuth()
  // Map an exercise's chapter number to the id its prose lesson is keyed under.
  const lessonId = (ch: number): number => ch + (LESSON_ID_OFFSET[bookId] ?? 0)

  const [allExercises, setAllExercises] = useState<ExerciseResponse[]>([])
  const [lessonTitles, setLessonTitles] = useState<Record<string, { title: string }>>({})
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [solvedIds, setSolvedIds] = useState<Set<number>>(new Set())
  const [openChapters, setOpenChapters] = useState<Set<number>>(new Set())
  const [selected, setSelected] = useState<ExerciseResponse | null>(null)
  const activeRowRef = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    setLoading(true)
    setLoadError(null)
    Promise.all([getExercises({ book_id: bookId }), getLessonTitles(bookId)])
      .then(([exercises, titles]) => {
        setAllExercises(exercises)
        setLessonTitles(titles)
      })
      .catch(err => setLoadError(String(err?.message ?? err)))
      .finally(() => setLoading(false))
  }, [bookId])

  useEffect(() => {
    if (!user) { setSolvedIds(new Set()); return }
    getUserProgress()
      .then(ids => setSolvedIds(new Set(ids)))
      .catch(() => {})
  }, [user])

  useEffect(() => {
    if (feedback?.correct && !feedback.in_progress && selected && user) {
      setSolvedIds(prev => new Set([...prev, selected.id]))
    }
  }, [feedback, selected, user])

  useEffect(() => {
    if (currentExerciseId === null) return
    const ex = allExercises.find(e => e.id === currentExerciseId)
    if (ex?.chapter) setOpenChapters(prev => new Set([...prev, ex.chapter!]))
  }, [currentExerciseId, allExercises])

  // Scroll the active exercise row into view once its chapter is open
  useEffect(() => {
    if (!activeRowRef.current) return
    setTimeout(() => activeRowRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 80)
  }, [currentExerciseId, openChapters])

  const handleSelect = (ex: ExerciseResponse) => {
    setSelected(ex)
    onExerciseLoad(ex.initial_fen, ex.id)
  }

  const chapters = React.useMemo(() => {
    const map = new Map<number, ExerciseResponse[]>()
    for (const ex of allExercises) {
      const ch = ex.chapter ?? 0
      if (!map.has(ch)) map.set(ch, [])
      map.get(ch)!.push(ex)
    }
    // Also include chapters that have a lesson but no exercises (lesson-only
    // chapters). Lesson ids may be offset (e.g. 201..241) — map them back to
    // the exercise-chapter space so they align with the rows above.
    const offset = LESSON_ID_OFFSET[bookId] ?? 0
    for (const chStr of Object.keys(lessonTitles)) {
      const ch = Number(chStr) - offset
      if (ch > 0 && !map.has(ch)) map.set(ch, [])
    }
    return Array.from(map.entries()).sort(([a], [b]) => a - b)
  }, [allExercises, lessonTitles, bookId])

  const toggleChapter = (ch: number) => {
    setOpenChapters(prev => {
      const next = new Set(prev)
      if (next.has(ch)) next.delete(ch); else next.add(ch)
      return next
    })
  }

  return (
    <div className="flex flex-col gap-0 h-full">
      <div className="panel">
        <h3 className="text-lg font-bold text-amber-600 mb-3">{t('exercises')}</h3>

        {loading && <p className="text-gray-400 text-sm text-center py-4">Chargement...</p>}
        {loadError && <p className="text-red-400 text-xs py-2">Erreur : {loadError}</p>}

        {!loading && !loadError && (
          <div
            className={compact ? 'max-h-[60vh]' : 'max-h-[75vh]'}
            style={{ overflowY: 'auto', WebkitOverflowScrolling: 'touch' as never }}
          >
            {chapters.map(([ch, exercises]) => {
              const isOpen = openChapters.has(ch)
              const lessonTitle = lessonTitles[String(lessonId(ch))]?.title ?? `Chapitre ${ch}`
              const firstEx = exercises[0]
              const solvedCount = exercises.filter(e => solvedIds.has(e.id)).length
              const isLessonRead = readChapters.has(lessonId(ch))
              const lessonOnly = exercises.length === 0

              return (
                <div key={ch} className="mb-1 rounded-lg overflow-hidden">
                  {/* Chapter header */}
                  <div className="flex items-stretch bg-gray-700">
                    <button
                      onClick={() => !lessonOnly && toggleChapter(ch)}
                      className={[
                        'flex-1 flex items-center gap-2 px-3 py-2.5 text-left bg-gray-700 border-0',
                        lessonOnly ? 'cursor-default' : 'hover:bg-gray-600 cursor-pointer',
                      ].join(' ')}
                    >
                      <span className="text-gray-400 text-xs w-3 flex-shrink-0">
                        {lessonOnly ? ' ' : (isOpen ? '▼' : '▶')}
                      </span>
                      <span className={`font-bold text-sm flex-1 min-w-0 leading-snug ${lessonOnly ? 'text-gray-300' : 'text-amber-400'}`}>
                        {lessonTitle}
                      </span>
                      <span className="flex items-center gap-1.5 flex-shrink-0 ml-1">
                        {isLessonRead && (
                          <span className="text-green-400 font-bold text-sm" title="Leçon lue">✓</span>
                        )}
                        {!lessonOnly && (
                          <span className="text-xs text-gray-400">
                            {solvedCount}/{exercises.length}
                          </span>
                        )}
                      </span>
                    </button>
                    {onLessonOpen && Object.keys(lessonTitles).length > 0 && (
                      <button
                        onClick={() => onLessonOpen(lessonId(ch), firstEx?.initial_fen ?? '')}
                        className="flex-shrink-0 w-10 flex items-center justify-center bg-gray-700 hover:bg-amber-900 border-0 border-l border-gray-600 cursor-pointer text-base"
                        title={`Leçon – ${lessonTitle}`}
                      >
                        📖
                      </button>
                    )}
                  </div>

                  {/* Exercise rows — only when there are exercises and the chapter is open */}
                  {isOpen && !lessonOnly && (
                    <div className="bg-gray-800 pl-2">
                      {exercises.map((ex, idx) => {
                        const isActive = currentExerciseId === ex.id
                        const isSolved = solvedIds.has(ex.id)
                        return (
                          <button
                            key={ex.id}
                            ref={isActive ? activeRowRef : null}
                            onClick={() => handleSelect(ex)}
                            className={[
                              'w-full flex items-center gap-2 px-3 py-2 text-left border-0 cursor-pointer',
                              isActive
                                ? 'bg-amber-900 border-l-2 border-amber-400'
                                : idx % 2 === 0
                                  ? 'bg-gray-800 hover:bg-gray-700 border-l-2 border-transparent'
                                  : 'bg-gray-750 hover:bg-gray-700 border-l-2 border-transparent',
                            ].join(' ')}
                            style={idx % 2 !== 0 && !isActive ? { backgroundColor: '#263144' } : undefined}
                          >
                            <span className={`text-xs w-5 flex-shrink-0 text-center ${isSolved ? 'text-green-400' : 'text-gray-500'}`}>
                              {isSolved ? '✓' : idx + 1}
                            </span>
                            <span className={`flex-1 text-sm truncate ${isActive ? 'text-white' : 'text-gray-200'}`}>
                              {shortName(ex.name)}
                            </span>
                            <Stars count={ex.difficulty} />
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {selected && feedback && !feedback.correct && (
        <div className="panel mt-2">
          <p className="text-red-300 font-semibold text-sm">{`✗ ${t('tryAgain')}`}</p>
        </div>
      )}
    </div>
  )
}
