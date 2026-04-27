import React, { useState, useEffect } from 'react'
import type { ExerciseResponse, ExerciseCheckResponse } from '../types'
import { getExercises, getUserProgress } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'

interface ExercisePanelProps {
  onExerciseLoad: (fen: string, exerciseId: number) => void
  currentExerciseId: number | null
  feedback: ExerciseCheckResponse | null
}

function Stars({ count }: { count: number }) {
  return (
    <span>
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={i < count ? 'star-filled' : 'star-empty'}>
          ★
        </span>
      ))}
    </span>
  )
}

const CATEGORIES_FR: Record<string, string> = {
  combinaisons_2: 'Combinaisons 2 temps',
  combinaisons_2_3: 'Combinaisons 2-3 temps',
  combinaisons_3: 'Combinaisons 3 temps',
  combinaisons_3_4: 'Combinaisons 3-4 temps',
  combinaisons_4: 'Combinaisons 4 temps',
  combinaisons_4_5: 'Combinaisons 4-5 temps',
  combinaisons_5: 'Combinaisons 5 temps',
  combinaisons_5_6: 'Combinaisons 5-6 temps',
  combinaisons_6: 'Combinaisons 6 temps',
}

const CATEGORIES_EN: Record<string, string> = {
  combinaisons_2: '2-move combinations',
  combinaisons_2_3: '2-3 move combinations',
  combinaisons_3: '3-move combinations',
  combinaisons_3_4: '3-4 move combinations',
  combinaisons_4: '4-move combinations',
  combinaisons_4_5: '4-5 move combinations',
  combinaisons_5: '5-move combinations',
  combinaisons_5_6: '5-6 move combinations',
  combinaisons_6: '6-move combinations',
}

export default function ExercisePanel({
  onExerciseLoad,
  currentExerciseId,
  feedback,
}: ExercisePanelProps) {
  const { t, language } = useLanguage()
  const { user } = useAuth()
  const CATEGORIES = language === 'en' ? CATEGORIES_EN : CATEGORIES_FR

  const [allExercises, setAllExercises] = useState<ExerciseResponse[]>([])
  const [exercises, setExercises] = useState<ExerciseResponse[]>([])
  const [selected, setSelected] = useState<ExerciseResponse | null>(null)
  const [showHint, setShowHint] = useState(false)
  const [filterCategory, setFilterCategory] = useState<string>('')
  const [filterDifficulty, setFilterDifficulty] = useState<number | undefined>()
  const [availableCategoryKeys, setAvailableCategoryKeys] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [solvedIds, setSolvedIds] = useState<Set<number>>(new Set())

  useEffect(() => {
    setLoading(true)
    setLoadError(null)
    getExercises()
      .then(data => {
        setAllExercises(data)
        const seen: Record<string, boolean> = {}
        for (const ex of data) {
          if (!seen[ex.category]) seen[ex.category] = true
        }
        setAvailableCategoryKeys(Object.keys(seen))
      })
      .catch(err => {
        setLoadError(String(err?.message ?? err))
      })
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

  useEffect(() => {
    let filtered = allExercises
    if (filterCategory) {
      filtered = filtered.filter(ex => ex.category === filterCategory)
    }
    if (filterDifficulty !== undefined) {
      filtered = filtered.filter(ex => ex.difficulty === filterDifficulty)
    }
    setExercises(filtered)
  }, [allExercises, filterCategory, filterDifficulty])

  const handleSelect = (ex: ExerciseResponse) => {
    setSelected(ex)
    setShowHint(false)
    onExerciseLoad(ex.initial_fen, ex.id)
  }

  const handleNext = () => {
    if (!selected) return
    const idx = exercises.findIndex(e => e.id === selected.id)
    if (idx < exercises.length - 1) {
      handleSelect(exercises[idx + 1])
    }
  }

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="panel">
        <h3 className="text-lg font-bold text-amber-600 mb-3">{t('exercises')}</h3>

        <div className="flex gap-2 mb-3 flex-wrap">
          <select
            value={filterCategory}
            onChange={e => setFilterCategory(e.target.value)}
            className="bg-gray-700 text-white rounded px-2 py-1 text-sm border border-gray-600"
          >
            <option value="">{t('category')}: {t('all')}</option>
            {availableCategoryKeys.map(key => (
              <option key={key} value={key}>{CATEGORIES[key] ?? key}</option>
            ))}
          </select>

          <select
            value={filterDifficulty ?? ''}
            onChange={e => setFilterDifficulty(e.target.value ? Number(e.target.value) : undefined)}
            className="bg-gray-700 text-white rounded px-2 py-1 text-sm border border-gray-600"
          >
            <option value="">{t('difficulty')}: {t('all')}</option>
            {[1, 2, 3, 4, 5].map(d => (
              <option key={d} value={d}>{d} ★</option>
            ))}
          </select>
        </div>

        <div className="max-h-48 overflow-y-auto flex flex-col gap-1">
          {loading && (
            <p className="text-gray-400 text-sm text-center py-2">Chargement...</p>
          )}
          {loadError && (
            <p className="text-red-400 text-xs py-2">Erreur: {loadError}</p>
          )}
          {!loading && !loadError && exercises.length === 0 && (
            <p className="text-gray-500 text-sm text-center py-2">Aucun exercice</p>
          )}
          {exercises.map(ex => (
            <button
              key={ex.id}
              onClick={() => handleSelect(ex)}
              className={`text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                currentExerciseId === ex.id
                  ? 'bg-amber-900 text-white'
                  : 'bg-gray-700 hover:bg-gray-600 text-gray-200'
              }`}
            >
              <div className="flex justify-between items-start">
                <span className="font-medium flex items-center gap-1.5">
                  {solvedIds.has(ex.id) && (
                    <span className="text-green-400 text-base leading-none">✓</span>
                  )}
                  {ex.name}
                </span>
                <Stars count={ex.difficulty} />
              </div>
              <div className="text-xs text-gray-400 mt-0.5">
                {CATEGORIES[ex.category] || ex.category}
              </div>
            </button>
          ))}
        </div>
      </div>

      {selected && (
        <div className="panel flex flex-col gap-3">
          <div>
            <h4 className="font-bold text-white">{selected.name}</h4>
            <div className="flex items-center gap-2 mt-1">
              <Stars count={selected.difficulty} />
              <span className="text-xs text-gray-400">
                {CATEGORIES[selected.category] || selected.category}
              </span>
            </div>
          </div>

          {selected.description && (
            <p className="text-gray-300 text-sm">{selected.description}</p>
          )}

          {showHint && selected.hint && (
            <div className="bg-yellow-900 border border-yellow-700 rounded-lg px-3 py-2 text-sm text-yellow-200">
              <span className="font-semibold">{t('hint')} :</span> {selected.hint}
            </div>
          )}

          {feedback && (
            <div
              className={`rounded-lg px-3 py-2 text-sm ${
                feedback.correct
                  ? 'bg-amber-900 border border-amber-700 text-amber-100'
                  : 'bg-red-900 border border-red-600 text-red-200'
              }`}
            >
              <p className="font-semibold">
                {feedback.correct ? `✓ ${t('wellDone')}` : `✗ ${t('tryAgain')}`}
              </p>
              {feedback.solution && (
                <p className="mt-1 text-xs">
                  Solution : {feedback.solution.join(', ')}
                </p>
              )}
            </div>
          )}

          <div className="flex gap-2">
            {selected.hint && (
              <button
                onClick={() => setShowHint(!showHint)}
                className="btn-secondary text-sm flex-1"
              >
                {showHint ? t('hideHint') : t('hint')}
              </button>
            )}
            <button
              onClick={handleNext}
              disabled={exercises.findIndex(e => e.id === selected.id) >= exercises.length - 1}
              className="btn-secondary text-sm flex-1"
            >
              {t('next')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
