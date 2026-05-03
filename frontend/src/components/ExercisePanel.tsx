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
    <span className="flex-shrink-0">
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} style={{ color: i < count ? '#f59e0b' : '#4b5563', fontSize: '11px' }}>★</span>
      ))}
    </span>
  )
}

// Strip the chapter-title prefix from names like "COMBINAISONS EN 2 TEMPS – D1" → "D1"
function shortName(name: string): string {
  const idx = name.indexOf('–')
  if (idx !== -1) return name.slice(idx + 1).trim()
  const idx2 = name.indexOf('-')
  if (idx2 !== -1 && idx2 > name.length / 2) return name.slice(idx2 + 1).trim()
  return name
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
          <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 0, maxHeight: compact ? '60vh' : '75vh' }}>
            {chapters.map(([ch, exercises]) => {
              const isOpen = openChapters.has(ch)
              const lessonTitle = lessonTitles[String(ch)]?.title ?? `Chapitre ${ch}`
              const firstEx = exercises[0]

              const solvedCount = exercises.filter(e => solvedIds.has(e.id)).length

              return (
                <div key={ch} style={{ borderRadius: 8, overflow: 'hidden', marginBottom: 4 }}>
                  {/* Chapter header row */}
                  <div style={{ display: 'flex', alignItems: 'stretch', background: '#374151' }}>
                    <button
                      onClick={() => toggleChapter(ch)}
                      style={{
                        flex: 1,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '10px 12px',
                        textAlign: 'left',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        minWidth: 0,
                      }}
                    >
                      <span style={{ color: '#9ca3af', fontSize: 10, flexShrink: 0, width: 12 }}>
                        {isOpen ? '▼' : '▶'}
                      </span>
                      <span style={{
                        fontWeight: 700,
                        color: '#fbbf24',
                        fontSize: 13,
                        flex: 1,
                        minWidth: 0,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        lineHeight: 1.3,
                      }}>
                        {lessonTitle}
                      </span>
                      <span style={{ fontSize: 11, color: '#6b7280', flexShrink: 0, marginLeft: 4 }}>
                        {solvedCount}/{exercises.length}
                      </span>
                    </button>
                    {onLessonOpen && (
                      <button
                        onClick={() => onLessonOpen(ch, firstEx.initial_fen)}
                        style={{
                          flexShrink: 0,
                          width: 40,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          background: 'none',
                          border: 'none',
                          borderLeft: '1px solid #4b5563',
                          cursor: 'pointer',
                          fontSize: 16,
                        }}
                        title={`Leçon – ${lessonTitle}`}
                      >
                        📖
                      </button>
                    )}
                  </div>

                  {/* Exercises list */}
                  {isOpen && (
                    <div style={{ background: '#1f2937', paddingLeft: 8 }}>
                      {exercises.map((ex, idx) => {
                        const isActive = currentExerciseId === ex.id
                        const isSolved = solvedIds.has(ex.id)
                        return (
                          <button
                            key={ex.id}
                            onClick={() => handleSelect(ex)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              width: '100%',
                              padding: '8px 12px',
                              textAlign: 'left',
                              background: isActive ? '#92400e' : idx % 2 === 0 ? '#1f2937' : '#263144',
                              border: 'none',
                              borderLeft: isActive ? '3px solid #f59e0b' : '3px solid transparent',
                              cursor: 'pointer',
                              gap: 8,
                            }}
                          >
                            <span style={{ fontSize: 12, color: isSolved ? '#4ade80' : '#6b7280', flexShrink: 0, width: 14 }}>
                              {isSolved ? '✓' : `${idx + 1}`}
                            </span>
                            <span style={{
                              flex: 1,
                              fontSize: 13,
                              color: isActive ? '#fff' : '#d1d5db',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}>
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
