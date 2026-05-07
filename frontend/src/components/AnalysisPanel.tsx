import React, { useState, useRef, useEffect } from 'react'
import type { AnalysisResponse, MoveAnnotationItem } from '../types'
import { useLanguage } from '../i18n/LanguageContext'
import AnalysisText from './AnalysisText'

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
  onMoveClick?: (pdn: string) => void
  onAnnotate?: () => void
  onLearn?: () => void
  annotating?: boolean
}

function extractMoveSquares(text: string, charIndex: number): number[] {
  const rest = text.slice(charIndex)
  const numMatch = rest.match(/^(\d+)/)
  if (!numMatch) return []

  const num1 = parseInt(numMatch[1], 10)
  if (num1 < 1 || num1 > 50) return []

  // Look forward: "32-27" or "32x27" or "32×27"
  const afterNum = rest.slice(numMatch[1].length)
  const forwardMatch = afterNum.match(/^[-–x×](\d+)/)
  if (forwardMatch) {
    const num2 = parseInt(forwardMatch[1], 10)
    if (num2 >= 1 && num2 <= 50) return [num1, num2]
  }

  // Look backward: "32-" or "32x" already read, now reading "27"
  const before = text.slice(Math.max(0, charIndex - 4), charIndex)
  const backMatch = before.match(/(\d+)[-–x×]$/)
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

const VERDICT_SYMBOL: Record<string, string> = {
  blunder: '??',
  mistake: '?',
  inaccuracy: '?!',
}
const VERDICT_COLOR: Record<string, string> = {
  blunder: '#ef4444',
  mistake: '#f97316',
  inaccuracy: '#eab308',
}
const VERDICT_LABEL: Record<string, { fr: string; en: string }> = {
  blunder:    { fr: 'Gaffe',       en: 'Blunder' },
  mistake:    { fr: 'Erreur',      en: 'Mistake' },
  inaccuracy: { fr: 'Imprécision', en: 'Inaccuracy' },
}

export function MoveAnnotationsTable({
  annotations,
  language,
}: {
  annotations: MoveAnnotationItem[]
  language: string
}) {
  const fr = language === 'fr'
  const notable = annotations.filter(a => a.verdict !== null)

  if (notable.length === 0) {
    return (
      <div className="text-xs text-green-400 text-center py-2">
        {fr ? '✓ Partie propre — aucune erreur détectée' : '✓ Clean game — no errors detected'}
      </div>
    )
  }

  const whiteBad = notable.filter(a => a.color === 'white')
  const blackBad = notable.filter(a => a.color === 'black')

  return (
    <div className="flex flex-col gap-2">
      {/* Stats bar */}
      <div className="grid grid-cols-2 gap-px bg-gray-800 rounded overflow-hidden text-xs">
        {(['white', 'black'] as const).map(color => {
          const items = color === 'white' ? whiteBad : blackBad
          const blunders   = items.filter(a => a.verdict === 'blunder').length
          const mistakes   = items.filter(a => a.verdict === 'mistake').length
          const inaccuracies = items.filter(a => a.verdict === 'inaccuracy').length
          return (
            <div key={color} className="bg-gray-950 px-2 py-1.5 flex flex-col gap-0.5">
              <span className="font-medium">{color === 'white' ? '⬜ Blancs' : '⬛ Noirs'}</span>
              <div className="flex gap-2">
                {blunders > 0 && <span style={{ color: VERDICT_COLOR.blunder }} className="font-bold">{blunders}??</span>}
                {mistakes > 0 && <span style={{ color: VERDICT_COLOR.mistake }} className="font-bold">{mistakes}?</span>}
                {inaccuracies > 0 && <span style={{ color: VERDICT_COLOR.inaccuracy }} className="font-bold">{inaccuracies}?!</span>}
                {blunders + mistakes + inaccuracies === 0 && <span className="text-green-500">✓</span>}
              </div>
            </div>
          )
        })}
      </div>

      {/* Per-move list */}
      <div className="flex flex-col gap-1.5">
        {notable.map((ann, idx) => {
          const sym = ann.verdict ? VERDICT_SYMBOL[ann.verdict] : ''
          const clr = ann.verdict ? VERDICT_COLOR[ann.verdict] : '#9ca3af'
          const label = ann.verdict ? (fr ? VERDICT_LABEL[ann.verdict].fr : VERDICT_LABEL[ann.verdict].en) : ''
          const colorLabel = ann.color === 'white' ? (fr ? 'Blancs' : 'White') : (fr ? 'Noirs' : 'Black')
          return (
            <div key={idx} className="bg-gray-900 rounded px-2 py-1.5 text-xs flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span style={{ color: clr, fontWeight: 700, fontSize: '0.85rem' }}>{sym}</span>
                <span className="font-medium" style={{ color: clr }}>{label}</span>
                <span className="text-gray-400">{fr ? 'Coup' : 'Move'} {ann.move_number} · {colorLabel}</span>
                <span className="font-mono text-gray-200 ml-auto">{ann.move_pdn}</span>
              </div>
              {ann.best_move && ann.best_move !== ann.move_pdn && (
                <div className="text-gray-400">
                  {fr ? 'Meilleur coup' : 'Best move'} : <span className="font-mono text-amber-400">{ann.best_move}</span>
                </div>
              )}
              {ann.book_tip && (
                <div className="text-gray-500 border-t border-gray-800 pt-1 mt-0.5">
                  <span className="text-amber-600">📚</span>{' '}
                  <span className="text-gray-400">{ann.book_tip.concept}</span>
                  {ann.book_tip.source && (
                    <span className="text-gray-600 ml-1">— {ann.book_tip.source}</span>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
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
  onMoveClick,
  onAnnotate,
  onLearn,
  annotating = false,
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
          className="btn-primary text-sm col-span-1"
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
          className="btn-secondary text-sm col-span-1"
        >
          {loading && mode === 'bestmoveexplain' ? (
            <span className="flex items-center gap-2 justify-center">
              <div className="spinner" style={{ width: 14, height: 14 }} />
            </span>
          ) : t('explainMove')}
        </button>

        {onAnnotate && (
          <button
            onClick={onAnnotate}
            disabled={!gameId || annotating || aiThinking}
            className="btn-secondary text-sm col-span-1 disabled:opacity-40"
          >
            {annotating ? (
              <span className="flex items-center gap-2 justify-center">
                <div className="spinner" style={{ width: 14, height: 14 }} />
              </span>
            ) : '⚙ Coup par coup'}
          </button>
        )}

        {onLearn && (
          <button
            onClick={onLearn}
            disabled={!gameId || annotating || aiThinking}
            className="btn-secondary text-sm col-span-1 disabled:opacity-40"
          >
            📚 Apprendre
          </button>
        )}
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
              <div className="bg-gray-900 rounded-lg p-3 text-gray-300 leading-relaxed overflow-y-auto text-xs max-h-48">
                <AnalysisText text={analysis.analysis} onMoveClick={onMoveClick} className="whitespace-pre-wrap" />
              </div>
            </div>
          )}

          {/* Move-by-move annotations — full game, non-expanded panel only */}
          {!expanded && mode === 'fullgame' && analysis.move_annotations && analysis.move_annotations.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 uppercase font-semibold mb-1">
                {language === 'fr' ? 'Analyse coup par coup' : 'Move-by-move analysis'}
              </div>
              <MoveAnnotationsTable annotations={analysis.move_annotations} language={language} />
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
