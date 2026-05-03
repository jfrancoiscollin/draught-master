import React, { useState, useEffect } from 'react'
import type { ExerciseResponse, ExerciseCheckResponse } from '../types'
import { getExercises, getUserProgress, getLessonTitles } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'

interface ExercisePanelProps {
  onExerciseLoad: (fen: string, exerciseId: number) => void
  onLessonOpen?: (chapter: number, fen: string) => void
  currentExerciseId: number | null
  feedback: ExerciseCheckResponse | null
  compact?: boolean
}

function Stars({ count }: { count: number }) {
  return (
    <span>
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={i < count ? 'star-filled' : 'star-empty'}>★</span>
      ))}
    </span>
  )
}

export default function ExercisePanel({
  onExerciseLoad,
  onLessonOpen,
  currentExerciseId,
  feedback,
  compact = true,
}: ExercisePanelProps) {
  const { t } = useLanguage()
  const { user } = useAuth()

  const [allExercises, setAllExercises] = useState<ExerciseResponse[]>([])
  const [lessonTitles, setLessonTitles] = useState<Record<string, { title: string }>>({})
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [solvedIds, setSolvedIds] = useState<Set<number>>(new Set())
  const [openChapters, setOpenChapters] = useState<Set<number>>(new Set())
  const [selected, setSelected] = useState<ExerciseResponse | null>(null)

  useEffect(() => {
    setLoading(true)
    setLoadError(null)
    Promise.all([getExercises(), getLessonTitles()])
      .then(([exercises, titles]) => {
        setAllExercises(exercises)
        setLessonTitles(titles)
        // Open first chapter by default
        const firstChapter = exercises.find(e => e.chapter)?.chapter
        if (firstChapter) setOpenChapters(new Set([firstChapter]))
      })
      .catch(err => setLoadError(String(err?.message ?? err)))
      .finally(() => setLoading(false))
  }, [])

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

  // Auto-open chapter of currently active exercise
  useEffect(() => {
    if (currentExerciseId === null) return
    const ex = allExercises.find(e => e.id === currentExerciseId)
    if (ex?.chapter) setOpenChapters(prev => new Set([...prev, ex.chapter!]))
  }, [currentExerciseId, allExercises])

  const handleSelect = (ex: ExerciseResponse) => {
    setSelected(ex)
    onExerciseLoad(ex.initial_fen, ex.id)
  }

  // Group exercises by chapter (preserving order)
  const chapters = React.useMemo(() => {
    const map = new Map<number, ExerciseResponse[]>()
    for (const ex of allExercises) {
      const ch = ex.chapter ?? 0
      if (!map.has(ch)) map.set(ch, [])
      map.get(ch)!.push(ex)
    }
    return Array.from(map.entries()).sort(([a], [b]) => a - b)
  }, [allExercises])

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
          <div className={`overflow-y-auto flex flex-col gap-0.5 ${compact ? 'max-h-[50vh]' : 'max-h-[70vh]'}`}>
            {chapters.map(([ch, exercises]) => {
              const isOpen = openChapters.has(ch)
              const lessonTitle = lessonTitles[String(ch)]?.title ?? `Chapitre ${ch}`
              const firstEx = exercises[0]

              return (
                <div key={ch} className="rounded-lg overflow-hidden">
                  {/* Chapter row */}
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => toggleChapter(ch)}
                      className="flex-1 flex items-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-left text-sm transition-colors"
                    >
                      <span className="text-gray-400 w-3 flex-shrink-0 text-xs">
                        {isOpen ? '▼' : '▶'}
                      </span>
                      <span className="font-semibold text-amber-400 flex-1 min-w-0 leading-snug">
                        {lessonTitle}
                      </span>
                      <span className="text-xs text-gray-500 flex-shrink-0">
                        {exercises.length} ex.
                      </span>
                    </button>
                    {onLessonOpen && (
                      <button
                        onClick={() => onLessonOpen(ch, firstEx.initial_fen)}
                        className="flex-shrink-0 w-9 h-full flex items-center justify-center bg-gray-700 hover:bg-amber-800 text-gray-400 hover:text-amber-300 transition-colors text-sm px-2 py-2"
                        title={`Leçon – ${lessonTitle}`}
                      >
                        📖
                      </button>
                    )}
                  </div>

                  {/* Exercises list */}
                  {isOpen && (
                    <div className="flex flex-col gap-px pl-4 bg-gray-800">
                      {exercises.map(ex => (
                        <button
                          key={ex.id}
                          onClick={() => handleSelect(ex)}
                          className={`text-left px-3 py-1.5 text-sm transition-colors ${
                            currentExerciseId === ex.id
                              ? 'bg-amber-900 text-white'
                              : 'bg-gray-750 hover:bg-gray-600 text-gray-300'
                          }`}
                          style={{ backgroundColor: currentExerciseId === ex.id ? undefined : '#2d3748' }}
                        >
                          <div className="flex justify-between items-center gap-2">
                            <span className="flex items-center gap-1.5 min-w-0">
                              {solvedIds.has(ex.id) && (
                                <span className="text-green-400 text-sm leading-none flex-shrink-0">✓</span>
                              )}
                              <span className="truncate">{ex.name}</span>
                            </span>
                            <Stars count={ex.difficulty} />
                          </div>
                        </button>
                      ))}
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
