import React, { useState, useEffect } from 'react'
import { getMotifInfo } from '../api/client'
import type { MotifInfo, MotifExercise } from '../api/client'

interface Props {
  slug: string
  lang: string
  onClose: () => void
  onStartExercise: (exerciseId: number) => void
}

function DifficultyStars({ n }: { n: number }) {
  return (
    <span className="text-xs tracking-tight">
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={i < n ? 'text-amber-400' : 'text-gray-600'}>★</span>
      ))}
    </span>
  )
}

function ExerciseRow({
  ex,
  idx,
  onStart,
}: {
  ex: MotifExercise
  idx: number
  onStart: () => void
}) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-gray-800 last:border-0">
      <span className="text-xs text-gray-600 w-5 text-right flex-shrink-0">{idx + 1}.</span>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-200 truncate">{ex.name}</p>
        <DifficultyStars n={ex.difficulty} />
      </div>
      <button
        onClick={onStart}
        className="flex-shrink-0 text-xs bg-indigo-700 hover:bg-indigo-600 text-white px-3 py-1 rounded transition-colors"
      >
        Commencer
      </button>
    </div>
  )
}

export default function MotifDetailPage({ slug, lang, onClose, onStartExercise }: Props) {
  const [info, setInfo] = useState<MotifInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getMotifInfo(slug)
      .then(setInfo)
      .catch(() => setError('Impossible de charger les informations du motif.'))
      .finally(() => setLoading(false))
  }, [slug])

  const name = lang === 'fr' ? (info?.name_fr ?? slug) : (info?.name_en ?? slug)
  const description = lang === 'fr' ? info?.description_fr : info?.description_en

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 bg-gray-800 border-b border-gray-700 flex-shrink-0">
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-amber-500 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors"
        >
          ←
        </button>
        <div className="flex-1">
          <p className="text-amber-500 font-bold text-sm">Motif tactique</p>
          <p className="text-white text-xs font-semibold">{name}</p>
        </div>
      </div>

      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-gray-400 text-sm animate-pulse">Chargement…</p>
        </div>
      )}

      {error && (
        <div className="flex-1 flex items-center justify-center p-6">
          <p className="text-red-400 text-sm text-center">{error}</p>
        </div>
      )}

      {!loading && info && (
        <div className="flex-1 overflow-y-auto">
          {/* Description */}
          <div className="px-4 py-3 bg-gray-800/40 border-b border-gray-800">
            <p className="text-xs text-gray-300 leading-relaxed">{description}</p>
          </div>

          {/* Exercise list */}
          <div className="px-4 pt-3 pb-2">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              {info.exercises.length > 0
                ? `${info.exercises.length} exercice${info.exercises.length > 1 ? 's' : ''} associé${info.exercises.length > 1 ? 's' : ''}`
                : 'Aucun exercice associé pour l\'instant'}
            </p>

            {info.exercises.length === 0 && (
              <p className="text-gray-600 text-xs">
                Les exercices seront disponibles après le premier déploiement complet.
              </p>
            )}

            {info.exercises.map((ex, i) => (
              <ExerciseRow
                key={ex.id}
                ex={ex}
                idx={i}
                onStart={() => onStartExercise(ex.id)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
