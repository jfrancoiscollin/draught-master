import React, { useState } from 'react'
import type { AnalysisResponse } from '../types'

interface AnalysisPanelProps {
  gameId: string | null
  onAnalyze: (question?: string) => Promise<AnalysisResponse | null>
  analysis: AnalysisResponse | null
  loading: boolean
}

export default function AnalysisPanel({
  gameId,
  onAnalyze,
  analysis,
  loading,
}: AnalysisPanelProps) {
  const [question, setQuestion] = useState('')

  const handleAnalyze = async () => {
    await onAnalyze(question || undefined)
    setQuestion('')
  }

  return (
    <div className="panel flex flex-col gap-3">
      <h3 className="text-lg font-bold text-green-400">Analyse Claude</h3>

      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !loading && gameId && handleAnalyze()}
          placeholder="Posez une question..."
          disabled={!gameId || loading}
          className="flex-1 bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:outline-none focus:border-green-500 disabled:opacity-50"
        />
        <button
          onClick={handleAnalyze}
          disabled={!gameId || loading}
          className="btn-primary text-sm whitespace-nowrap"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <div className="spinner" style={{ width: 16, height: 16 }} />
              Analyse...
            </span>
          ) : (
            'Analyser'
          )}
        </button>
      </div>

      {analysis && (
        <div className="flex flex-col gap-3 text-sm">
          {analysis.best_moves.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 uppercase font-semibold mb-1">
                Meilleurs coups
              </div>
              <div className="flex flex-wrap gap-1">
                {analysis.best_moves.map((m, i) => (
                  <span
                    key={i}
                    className="bg-gray-700 text-green-300 px-2 py-0.5 rounded font-mono text-xs"
                  >
                    {m}
                  </span>
                ))}
              </div>
            </div>
          )}

          {analysis.strategic_advice && (
            <div>
              <div className="text-xs text-gray-400 uppercase font-semibold mb-1">
                Conseil stratégique
              </div>
              <p className="text-gray-200 leading-relaxed">{analysis.strategic_advice}</p>
            </div>
          )}

          <div>
            <div className="text-xs text-gray-400 uppercase font-semibold mb-1">
              Analyse complète
            </div>
            <div className="bg-gray-900 rounded-lg p-3 text-gray-300 leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto text-xs">
              {analysis.analysis}
            </div>
          </div>

          {analysis.key_squares.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 uppercase font-semibold mb-1">
                Cases clés
              </div>
              <div className="flex flex-wrap gap-1">
                {analysis.key_squares.map(sq => (
                  <span
                    key={sq}
                    className="bg-yellow-800 text-yellow-200 px-2 py-0.5 rounded text-xs font-mono"
                  >
                    {sq}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!analysis && !loading && (
        <p className="text-gray-500 text-sm italic">
          Cliquez sur "Analyser" pour obtenir une analyse de la position par Claude.
        </p>
      )}
    </div>
  )
}
