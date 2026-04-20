import React, { useState, useRef, useEffect } from 'react'
import type { AnalysisResponse } from '../types'
import { useLanguage } from '../i18n/LanguageContext'

interface AnalysisPanelProps {
  gameId: string | null
  onAnalyze: (question?: string) => Promise<AnalysisResponse | null>
  analysis: AnalysisResponse | null
  loading: boolean
  onHighlightSquare: (squares: number[]) => void
}

function extractMoveSquares(text: string, charIndex: number): number[] {
  const rest = text.slice(charIndex)
  const numMatch = rest.match(/^(\d+)/)
  if (!numMatch) return []

  const num1 = parseInt(numMatch[1], 10)
  if (num1 < 1 || num1 > 50) return []

  // Look forward: "32-27" or "32x27" or "32×27"
  const afterNum = rest.slice(numMatch[1].length)
  const forwardMatch = afterNum.match(/^[-x×](\d+)/)
  if (forwardMatch) {
    const num2 = parseInt(forwardMatch[1], 10)
    if (num2 >= 1 && num2 <= 50) return [num1, num2]
  }

  // Look backward: "32-" or "32x" already read, now reading "27"
  const before = text.slice(Math.max(0, charIndex - 4), charIndex)
  const backMatch = before.match(/(\d+)[-x×]$/)
  if (backMatch) {
    const num2 = parseInt(backMatch[1], 10)
    if (num2 >= 1 && num2 <= 50) return [num2, num1]
  }

  return [num1]
}

function useSpeech(language: string, onSquares: (squares: number[]) => void) {
  const [speaking, setSpeaking] = useState(false)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  useEffect(() => {
    return () => { window.speechSynthesis?.cancel() }
  }, [])

  const speak = (text: string) => {
    if (!window.speechSynthesis) return
    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = language === 'en' ? 'en-GB' : 'fr-FR'
    utterance.rate = 0.9

    utterance.onboundary = (event) => {
      if (event.name !== 'word') return
      onSquares(extractMoveSquares(text, event.charIndex))
    }

    utterance.onstart = () => setSpeaking(true)
    utterance.onend = () => { setSpeaking(false); onSquares([]) }
    utterance.onerror = () => { setSpeaking(false); onSquares([]) }

    utteranceRef.current = utterance
    window.speechSynthesis.speak(utterance)
  }

  const stop = () => {
    window.speechSynthesis?.cancel()
    setSpeaking(false)
    onSquares([])
  }

  return { speak, stop, speaking }
}

export default function AnalysisPanel({
  gameId,
  onAnalyze,
  analysis,
  loading,
  onHighlightSquare,
}: AnalysisPanelProps) {
  const { t, language } = useLanguage()
  const [question, setQuestion] = useState('')
  const { speak, stop, speaking } = useSpeech(language, onHighlightSquare)


  const handleAnalyze = async () => {
    stop()
    const result = await onAnalyze(question || undefined)
    setQuestion('')
    if (result?.analysis) {
      speak(result.analysis)
    }
  }

  return (
    <div className="panel flex flex-col gap-3">
      <h3 className="text-lg font-bold text-green-400">{t('claudeAnalysis')}</h3>

      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !loading && gameId && handleAnalyze()}
          placeholder={t('yourQuestion')}
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
              {t('analyzing')}
            </span>
          ) : (
            t('analyze')
          )}
        </button>
      </div>

      {analysis && (
        <div className="flex flex-col gap-3 text-sm">
          {analysis.best_moves.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 uppercase font-semibold mb-1">
                {t('bestMoves')}
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
                {t('strategicAdvice')}
              </div>
              <p className="text-gray-200 leading-relaxed">{analysis.strategic_advice}</p>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="text-xs text-gray-400 uppercase font-semibold">
                {t('fullAnalysis')}
              </div>
              <button
                onClick={speaking ? stop : () => speak(analysis.analysis)}
                className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors ${
                  speaking
                    ? 'bg-red-700 hover:bg-red-600 text-white'
                    : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                }`}
                title={speaking ? t('stopReading') : t('readAloud')}
              >
                <span>{speaking ? '⏹' : '🔊'}</span>
                <span>{speaking ? t('stopReading') : t('readAloud')}</span>
              </button>
            </div>
            <div className="bg-gray-900 rounded-lg p-3 text-gray-300 leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto text-xs">
              {analysis.analysis}
            </div>
          </div>

          {analysis.key_squares.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 uppercase font-semibold mb-1">
                {t('keySquares')}
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
          {t('clickToAnalyze')}
        </p>
      )}
    </div>
  )
}
