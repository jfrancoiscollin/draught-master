import React, { useState, useRef, useEffect } from 'react'
import type { AnalysisResponse } from '../types'
import { useLanguage } from '../i18n/LanguageContext'

interface AnalysisPanelProps {
  gameId: string | null
  onAnalyze: (question?: string, mode?: string) => Promise<AnalysisResponse | null>
  onBestMove: () => Promise<string[] | null>
  analysis: AnalysisResponse | null
  loading: boolean
  onHighlightSquare: (squares: number[]) => void
  expanded?: boolean
  onCollapse?: () => void
  aiThinking?: boolean
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
  onBestMove,
  analysis,
  loading,
  onHighlightSquare,
  expanded = false,
  onCollapse,
  aiThinking = false,
}: AnalysisPanelProps) {
  const { t, language } = useLanguage()
  const [mode, setMode] = useState<'bestmove' | 'full' | 'fullgame' | 'bestmoveexplain' | null>(null)
  const [quickMoves, setQuickMoves] = useState<string[] | null>(null)
  const [quickLoading, setQuickLoading] = useState(false)
  const { speak, stop, speaking } = useSpeech(language, onHighlightSquare)

  const handleBestMove = async () => {
    if (!gameId) return
    stop()
    setMode('bestmove')
    setQuickMoves(null)
    setQuickLoading(true)
    try {
      const moves = await onBestMove()
      setQuickMoves(moves ?? [])
    } finally {
      setQuickLoading(false)
    }
  }

  const handleFullAnalyze = async () => {
    stop()
    setMode('full')
    const result = await onAnalyze(undefined, 'position')
    if (result?.analysis) speak(result.analysis)
  }

  const handleFullGame = async () => {
    stop()
    setMode('fullgame')
    const result = await onAnalyze(undefined, 'full_game')
    if (result?.analysis) speak(result.analysis)
  }

  const handleExplainBestMove = async () => {
    stop()
    setMode('bestmoveexplain')
    const result = await onAnalyze(undefined, 'best_move')
    if (result?.analysis) speak(result.analysis)
  }

  return (
    <div className="panel flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-amber-600">{t('analysis')}</h3>
        {expanded && onCollapse && (
          <button
            onClick={onCollapse}
            className="text-gray-400 hover:text-white text-base px-2 py-0.5 rounded hover:bg-gray-700 transition-colors"
            title="Réduire"
          >
            ✕
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={handleBestMove}
          disabled={!gameId || quickLoading || aiThinking}
          className="btn-secondary text-sm"
        >
          {quickLoading ? (
            <span className="flex items-center gap-2 justify-center">
              <div className="spinner" style={{ width: 14, height: 14 }} />
            </span>
          ) : t('bestMove')}
        </button>
        <button
          onClick={handleFullAnalyze}
          disabled={!gameId || loading || aiThinking}
          className="btn-primary text-sm"
        >
          {loading && mode === 'full' ? (
            <span className="flex items-center gap-2 justify-center">
              <div className="spinner" style={{ width: 14, height: 14 }} />
            </span>
          ) : t('analyze')}
        </button>
        <button
          onClick={handleFullGame}
          disabled={!gameId || loading || aiThinking}
          className="btn-secondary text-sm col-span-1"
        >
          {loading && mode === 'fullgame' ? (
            <span className="flex items-center gap-2 justify-center">
              <div className="spinner" style={{ width: 14, height: 14 }} />
            </span>
          ) : t('analyzeGame')}
        </button>
        <button
          onClick={handleExplainBestMove}
          disabled={!gameId || loading || aiThinking}
          className="btn-primary text-sm col-span-1"
        >
          {loading && mode === 'bestmoveexplain' ? (
            <span className="flex items-center gap-2 justify-center">
              <div className="spinner" style={{ width: 14, height: 14 }} />
            </span>
          ) : t('explainMove')}
        </button>
      </div>

      {mode === 'bestmove' && quickMoves !== null && (
        <div className="flex flex-wrap gap-1">
          {quickMoves.length > 0 ? (
            quickMoves.map((m, i) => (
              <span
                key={i}
                className="bg-gray-700 text-amber-400 px-2 py-1 rounded font-mono text-sm font-semibold"
              >
                {m}
              </span>
            ))
          ) : (
            <p className="text-gray-500 text-sm italic">{t('noMoves')}</p>
          )}
        </div>
      )}

      {analysis && (mode === 'full' || mode === 'fullgame' || mode === 'bestmoveexplain') && (
        <div className="flex flex-col gap-3 text-sm">
          {analysis.best_moves.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 uppercase font-semibold mb-1">{t('bestMoves')}</div>
              <div className="flex flex-wrap gap-1">
                {analysis.best_moves.map((m, i) => (
                  <span key={i} className="bg-gray-700 text-amber-400 px-2 py-0.5 rounded font-mono text-xs">
                    {m}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Strategic advice only in non-expanded mode */}
          {!expanded && analysis.strategic_advice && (
            <div>
              <div className="text-xs text-gray-400 uppercase font-semibold mb-1">{t('strategicAdvice')}</div>
              <p className="text-gray-200 leading-relaxed">{analysis.strategic_advice}</p>
            </div>
          )}

          {/* Full analysis text — only shown here when NOT expanded (App.tsx renders it below) */}
          {!expanded && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs text-gray-400 uppercase font-semibold">{t('fullAnalysis')}</div>
                <button
                  onClick={speaking ? stop : () => speak(analysis.analysis)}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors ${
                    speaking ? 'bg-red-700 hover:bg-red-600 text-white' : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                  }`}
                >
                  <span>{speaking ? '⏹' : '🔊'}</span>
                  <span>{speaking ? t('stopReading') : t('readAloud')}</span>
                </button>
              </div>
              <div className="bg-gray-900 rounded-lg p-3 text-gray-300 leading-relaxed whitespace-pre-wrap overflow-y-auto text-xs max-h-48">
                {analysis.analysis}
              </div>
            </div>
          )}

          {analysis.key_squares.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 uppercase font-semibold mb-1">{t('keySquares')}</div>
              <div className="flex flex-wrap gap-1">
                {analysis.key_squares.map(sq => (
                  <span key={sq} className="bg-yellow-800 text-yellow-200 px-2 py-0.5 rounded text-xs font-mono">
                    {sq}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!analysis && !loading && (
        <p className="text-gray-500 text-sm italic">{t('clickToAnalyze')}</p>
      )}
    </div>
  )
}
