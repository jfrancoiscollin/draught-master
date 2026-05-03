import React, { useEffect, useState, useCallback } from 'react'
import Board from './Board'
import { getLesson } from '../api/client'
import { fenToBoard } from '../utils/fen'
import type { MoveData } from '../types'

interface LessonPanelProps {
  chapter: number
  exampleFen: string
  onClose: () => void
}

// Wrap square numbers (1-50) appearing as standalone tokens in lesson text
// into clickable spans. Avoids matching numbers inside longer numbers.
function LessonText({
  text,
  onSquareClick,
  highlighted,
}: {
  text: string
  onSquareClick: (sq: number) => void
  highlighted: number[]
}) {
  // Split text into tokens: square numbers vs everything else
  const parts = text.split(/\b([1-4]?\d|50)\b/)

  return (
    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, fontSize: '0.92rem' }}>
      {parts.map((part, i) => {
        const n = Number(part)
        if (i % 2 === 1 && n >= 1 && n <= 50) {
          const isHl = highlighted.includes(n)
          return (
            <span
              key={i}
              onClick={() => onSquareClick(n)}
              style={{
                cursor: 'pointer',
                fontWeight: 700,
                color: isHl ? '#f59e0b' : '#fbbf24',
                background: isHl ? 'rgba(245,158,11,0.18)' : 'transparent',
                borderRadius: 3,
                padding: '0 1px',
                textDecoration: 'underline dotted',
              }}
              title={`Case ${n}`}
            >
              {part}
            </span>
          )
        }
        return <span key={i}>{part}</span>
      })}
    </div>
  )
}

export default function LessonPanel({ chapter, exampleFen, onClose }: LessonPanelProps) {
  const [lesson, setLesson] = useState<{ title: string; text: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [highlighted, setHighlighted] = useState<number[]>([])

  useEffect(() => {
    setLoading(true)
    setError(null)
    setHighlighted([])
    getLesson(chapter)
      .then(setLesson)
      .catch(() => setError('Leçon introuvable'))
      .finally(() => setLoading(false))
  }, [chapter])

  const board = fenToBoard(exampleFen)
  const flipped = exampleFen.startsWith('B:')

  const handleSquareClick = useCallback((sq: number) => {
    setHighlighted(prev =>
      prev.includes(sq) ? prev.filter(s => s !== sq) : [...prev, sq]
    )
  }, [])

  const noOp = useCallback((_: MoveData) => {}, [])
  const noOpSq = useCallback((_: number | null) => {}, [])

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-gray-800 border-b border-gray-700 flex-shrink-0">
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-amber-500 text-2xl w-9 h-9 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors"
        >
          ←
        </button>
        <h2 className="font-bold text-amber-500 text-base leading-tight flex-1 min-w-0 truncate">
          {lesson?.title ?? `Chapitre ${chapter}`}
        </h2>
      </div>

      {/* Board — fixed below header, never scrolls */}
      <div className="flex-shrink-0 flex flex-col items-center py-3 bg-gray-900 border-b border-gray-700">
        <div style={{ width: '100%', maxWidth: 240 }}>
          <Board
            board={board}
            legalMoves={[]}
            onMove={noOp}
            selectedSquare={null}
            onSelectSquare={noOpSq}
            disabled={true}
            highlightSquares={highlighted}
            flipped={flipped}
          />
        </div>
        <div className="flex items-center gap-4 mt-1">
          {highlighted.length > 0 && (
            <button
              onClick={() => setHighlighted([])}
              className="text-xs text-gray-500 hover:text-gray-300 underline"
            >
              Effacer sélection
            </button>
          )}
          <p className="text-xs text-gray-600">
            Clique sur un numéro → surligne la case
          </p>
        </div>
      </div>

      {/* Lesson text — scrollable */}
      <div className="flex-1 overflow-y-auto overscroll-contain px-4 py-4">
        {loading && (
          <div className="flex justify-center py-12">
            <div className="spinner" style={{ width: 28, height: 28 }} />
          </div>
        )}
        {error && (
          <p className="text-red-400 text-sm py-6 text-center">{error}</p>
        )}
        {lesson && !loading && (
          <LessonText
            text={lesson.text}
            onSquareClick={handleSquareClick}
            highlighted={highlighted}
          />
        )}
      </div>
    </div>
  )
}
