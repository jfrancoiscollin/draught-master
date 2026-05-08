import React, { useState, useCallback, useEffect, useRef } from 'react'
import Board from './Board'
import type { Arrow } from './Board'
import { fenToBoard } from '../utils/fen'
import { getPositionLegalMoves } from '../api/client'
import type { PdnPosition } from '../api/client'
import type { MoveData } from '../types'
import {
  type MoveAnnotation, VERDICT_SYMBOL, VERDICT_COLOR, VERDICT_LABEL_FR,
} from '../lib/gameAnnotations'
import { matchHubMove } from '../lib/scanEngine'

interface LearnFromMistakesProps {
  positions: PdnPosition[]
  annotations: MoveAnnotation[]
  playerColor: 'white' | 'black' | null  // null = both
  onClose: () => void
}

type StepState = 'waiting' | 'correct' | 'wrong'

export default function LearnFromMistakes({
  positions, annotations, playerColor, onClose,
}: LearnFromMistakesProps) {
  // Filter to mistakes/blunders (skip inaccuracies for conciseness, but include all)
  const lessons = annotations.filter(a =>
    a.verdict !== null &&
    (playerColor === null || a.color === playerColor)
  )

  const [lessonIdx, setLessonIdx] = useState(0)
  const [stepState, setStepState] = useState<StepState>('waiting')
  const [legalMoves, setLegalMoves] = useState<MoveData[]>([])
  const [selectedSquare, setSelectedSquare] = useState<number | null>(null)
  const [arrow, setArrow] = useState<Arrow | null>(null)
  const [score, setScore] = useState({ correct: 0, wrong: 0 })
  const [done, setDone] = useState(false)
  const loadingRef = useRef(false)

  const currentLesson = lessons[lessonIdx]
  // Position BEFORE the mistake (where the user should find the best move)
  const boardPos = currentLesson ? positions[currentLesson.posIdx - 1] : null
  const board = boardPos ? fenToBoard(boardPos.fen) : fenToBoard(positions[0].fen)
  const flipped = positions[0].fen.startsWith('B:')

  // Load legal moves for the current lesson position
  useEffect(() => {
    if (!boardPos || loadingRef.current) return
    loadingRef.current = true
    setLegalMoves([])
    setSelectedSquare(null)
    setArrow(null)
    setStepState('waiting')
    getPositionLegalMoves(boardPos.fen)
      .then(moves => setLegalMoves(moves))
      .catch(() => setLegalMoves([]))
      .finally(() => { loadingRef.current = false })
  }, [boardPos?.fen])

  const handleMove = useCallback((move: MoveData) => {
    if (!currentLesson || stepState !== 'waiting') return
    const best = currentLesson.bestMove
    if (!best) return

    // Match user move against best move
    const bestMoveData = matchHubMove(best, legalMoves)
    const isCorrect = bestMoveData !== null &&
      move.path[0] === bestMoveData.path[0] &&
      move.path[move.path.length - 1] === bestMoveData.path[bestMoveData.path.length - 1]

    if (isCorrect) {
      setStepState('correct')
      setScore(s => ({ ...s, correct: s.correct + 1 }))
    } else {
      setStepState('wrong')
      setScore(s => ({ ...s, wrong: s.wrong + 1 }))
      // Show the correct move as an arrow
      if (bestMoveData) {
        const sep = best.includes('x') ? 'x' : '-'
        const parts = best.split(sep).map(Number)
        if (parts.length >= 2) setArrow({ from: parts[0], to: parts[parts.length - 1] })
      }
    }
    setSelectedSquare(null)
  }, [currentLesson, stepState, legalMoves])

  const handleShowAnswer = () => {
    if (!currentLesson?.bestMove || stepState !== 'waiting') return
    const best = currentLesson.bestMove
    const sep = best.includes('x') ? 'x' : '-'
    const parts = best.split(sep).map(Number)
    if (parts.length >= 2) setArrow({ from: parts[0], to: parts[parts.length - 1] })
    setStepState('wrong')
    setScore(s => ({ ...s, wrong: s.wrong + 1 }))
  }

  const handleNext = () => {
    if (lessonIdx >= lessons.length - 1) {
      setDone(true)
    } else {
      setLessonIdx(i => i + 1)
    }
  }

  if (lessons.length === 0) {
    return (
      <div className="flex flex-col h-full bg-gray-900 text-gray-100 items-center justify-center gap-4 p-6">
        <div className="text-5xl">🎉</div>
        <p className="text-white font-bold text-lg">Aucune erreur trouvée !</p>
        <p className="text-gray-400 text-sm text-center">La partie ne contient pas d'imprécisions, d'erreurs ou de gaffes.</p>
        <button onClick={onClose} className="btn-primary mt-2">← Retour</button>
      </div>
    )
  }

  if (done) {
    const total = score.correct + score.wrong
    const pct = total > 0 ? Math.round((score.correct / total) * 100) : 0
    return (
      <div className="flex flex-col h-full bg-gray-900 text-gray-100 items-center justify-center gap-5 p-6">
        <div className="text-5xl">{pct >= 70 ? '🏆' : pct >= 40 ? '💪' : '📚'}</div>
        <p className="text-white font-bold text-xl">Entraînement terminé</p>
        <div className="bg-gray-800 rounded-xl p-5 w-full max-w-xs flex flex-col gap-2 text-center">
          <p className="text-gray-400 text-sm">Score</p>
          <p className="text-3xl font-bold text-amber-400">{score.correct} / {total}</p>
          <p className="text-gray-500 text-sm">{pct}% de coups corrects</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => { setLessonIdx(0); setScore({ correct: 0, wrong: 0 }); setDone(false) }}
            className="btn-secondary">
            Recommencer
          </button>
          <button onClick={onClose} className="btn-primary">← Retour</button>
        </div>
      </div>
    )
  }

  const lesson = currentLesson!
  const verdictColor = lesson.verdict ? VERDICT_COLOR[lesson.verdict] : '#9ca3af'
  const verdictLabel = lesson.verdict ? VERDICT_LABEL_FR[lesson.verdict] : ''
  const verdictSym = lesson.verdict ? VERDICT_SYMBOL[lesson.verdict] : ''

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 bg-gray-800 border-b border-gray-700 flex-shrink-0">
        <button onClick={onClose}
          className="text-gray-400 hover:text-amber-500 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors">
          ←
        </button>
        <div className="flex-1">
          <p className="text-amber-500 font-bold text-sm">Apprendre de ses erreurs</p>
          <p className="text-gray-500 text-xs">{lessonIdx + 1} / {lessons.length}</p>
        </div>
        <div className="flex gap-3 text-xs font-mono">
          <span className="text-green-400">{score.correct} ✓</span>
          <span className="text-red-400">{score.wrong} ✗</span>
        </div>
      </div>

      {/* Verdict badge */}
      <div className="flex-shrink-0 flex items-center gap-2 px-3 py-2 bg-gray-950 border-b border-gray-800">
        <span className="font-bold text-sm" style={{ color: verdictColor }}>
          {verdictSym} {verdictLabel}
        </span>
        <span className="text-gray-500 text-xs">
          · Coup {positions[lesson.posIdx].move_number} · {lesson.color === 'white' ? '⬜ Blancs' : '⬛ Noirs'}
        </span>
        <span className="ml-auto text-gray-600 text-xs font-mono">
          −{lesson.lossCp} cp
        </span>
      </div>

      {/* Instruction */}
      <div className="flex-shrink-0 px-3 py-2 text-xs text-center">
        {stepState === 'waiting' && (
          <span className="text-gray-300">
            Trouvez le meilleur coup pour les <strong>{lesson.color === 'white' ? 'Blancs' : 'Noirs'}</strong>
          </span>
        )}
        {stepState === 'correct' && (
          <span className="text-green-400 font-semibold">✓ Correct ! C'est le meilleur coup.</span>
        )}
        {stepState === 'wrong' && (
          <span className="text-red-400 font-semibold">
            ✗ {lesson.bestMove ? `Le meilleur coup était ${lesson.bestMove}` : 'Incorrect'}
          </span>
        )}
      </div>

      {/* Board */}
      <div className="flex-shrink-0 flex flex-col items-center py-2">
        <div style={{ width: '100%', maxWidth: 260 }}>
          <Board
            board={board}
            legalMoves={stepState === 'waiting' ? legalMoves : []}
            onMove={handleMove}
            selectedSquare={selectedSquare}
            onSelectSquare={setSelectedSquare}
            disabled={stepState !== 'waiting'}
            arrows={arrow ? [arrow] : []}
            flipped={flipped}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex-shrink-0 flex gap-2 px-4 py-3">
        {stepState === 'waiting' && (
          <button onClick={handleShowAnswer} className="flex-1 btn-secondary text-sm">
            Voir la réponse
          </button>
        )}
        {stepState !== 'waiting' && (
          <button onClick={handleNext} className="flex-1 btn-primary text-sm">
            {lessonIdx < lessons.length - 1 ? 'Suivant →' : 'Terminer'}
          </button>
        )}
      </div>

      {/* Progress bar */}
      <div className="flex-shrink-0 px-4 pb-3">
        <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-amber-500 rounded-full transition-all duration-300"
            style={{ width: `${((lessonIdx) / lessons.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  )
}
