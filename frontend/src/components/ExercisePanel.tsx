import React, { useState, useEffect } from 'react'
import type { ExerciseResponse, ExerciseCheckResponse } from '../types'
import { getExercises } from '../api/client'
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
  captures: 'Prises',
  promotion: 'Promotion',
  endgame: 'Finale',
  opening: 'Ouverture',
  strategy: 'Stratégie',
  tactics: 'Tactique',
  general: 'Général',
}

const CATEGORIES_EN: Record<string, string> = {
  captures: 'Captures',
  promotion: 'Promotion',
  endgame: 'Endgame',
  opening: 'Opening',
  strategy: 'Strategy',
  tactics: 'Tactics',
  general: 'General',
}

export default function ExercisePanel({
  onExerciseLoad,
  currentExerciseId,
  feedback,
}: ExercisePanelProps) {
  const { t, language } = useLanguage()
  const CATEGORIES = language === 'en' ? CATEGORIES_EN : CATEGORIES_FR

  const [exercises, setExercises] = useState<ExerciseResponse[]>([])
  const [selected, setSelected] = useState<ExerciseResponse | null>(null)
  const [showHint, setShowHint] = useState(false)
  const [filterCategory, setFilterCategory] = useState<string>('')
  const [filterDifficulty, setFilterDifficulty] = useState<number | undefined>()

  useEffect(() => {
    loadExercises()
  }, [filterCategory, filterDifficulty])

  const loadExercises = async () => {
    const data = await getExercises({
      category: filterCategory || undefined,
      difficulty: filterDifficulty,
    })
    setExercises(data)
  }

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
            {Object.entries(CATEGORIES).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
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
                <span className="font-medium">{ex.name}</span>
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
