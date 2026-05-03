import React, { useEffect, useState, useCallback } from 'react'
import Board from './Board'
import { getLesson, getExercises } from '../api/client'
import { fenToBoard } from '../utils/fen'
import type { MoveData, ExerciseResponse } from '../types'

interface LessonPanelProps {
  chapter: number
  exampleFen: string
  onClose: () => void
}

type Token =
  | { kind: 'text'; value: string }
  | { kind: 'square'; sq: number; value: string }
  | { kind: 'diag'; n: number; value: string }

function tokenize(text: string): Token[] {
  const tokens: Token[] = []
  // Match (diag. N), diag. N, or standalone square numbers 1-50
  const re = /\(diag\.\s*(\d+)\)|diag\.\s*(\d+)|\b([1-4]?\d|50)\b/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) tokens.push({ kind: 'text', value: text.slice(last, m.index) })
    if (m[1] !== undefined) {
      tokens.push({ kind: 'diag', n: parseInt(m[1]), value: m[0] })
    } else if (m[2] !== undefined) {
      tokens.push({ kind: 'diag', n: parseInt(m[2]), value: m[0] })
    } else {
      const sq = parseInt(m[3])
      if (sq >= 1 && sq <= 50) tokens.push({ kind: 'square', sq, value: m[0] })
      else tokens.push({ kind: 'text', value: m[0] })
    }
    last = m.index + m[0].length
  }
  if (last < text.length) tokens.push({ kind: 'text', value: text.slice(last) })
  return tokens
}

function LessonText({
  text,
  onSquareClick,
  onDiagramClick,
  highlighted,
}: {
  text: string
  onSquareClick: (sq: number) => void
  onDiagramClick: (n: number) => void
  highlighted: number[]
}) {
  const tokens = tokenize(text)
  return (
    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.75, fontSize: '0.92rem' }}>
      {tokens.map((tok, i) => {
        if (tok.kind === 'square') {
          const isHl = highlighted.includes(tok.sq)
          return (
            <span
              key={i}
              onClick={() => onSquareClick(tok.sq)}
              style={{
                cursor: 'pointer',
                fontWeight: 700,
                color: isHl ? '#f59e0b' : '#fbbf24',
                background: isHl ? 'rgba(245,158,11,0.18)' : 'transparent',
                borderRadius: 3,
                padding: '0 1px',
                textDecoration: 'underline dotted',
              }}
              title={`Case ${tok.sq}`}
            >
              {tok.value}
            </span>
          )
        }
        if (tok.kind === 'diag') {
          return (
            <span
              key={i}
              onClick={() => onDiagramClick(tok.n)}
              style={{
                cursor: 'pointer',
                fontWeight: 700,
                color: '#67e8f9',
                background: 'rgba(103,232,249,0.12)',
                borderRadius: 4,
                padding: '0 3px',
                textDecoration: 'underline dotted',
              }}
              title={`Voir diagramme ${tok.n}`}
            >
              {tok.value}
            </span>
          )
        }
        return <span key={i}>{tok.value}</span>
      })}
    </div>
  )
}

export default function LessonPanel({ chapter, exampleFen, onClose }: LessonPanelProps) {
  const [lesson, setLesson] = useState<{ title: string; text: string; diagrams?: string[] } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exercises, setExercises] = useState<ExerciseResponse[]>([])
  const [activeDiagram, setActiveDiagram] = useState(0)
  const [highlighted, setHighlighted] = useState<number[]>([])

  useEffect(() => {
    setLoading(true)
    setError(null)
    setHighlighted([])
    setActiveDiagram(0)
    Promise.all([
      getLesson(chapter),
      getExercises(),
    ])
      .then(([lessonData, allExercises]) => {
        setLesson(lessonData as typeof lesson)
        const chExercises = allExercises.filter(e => e.chapter === chapter)
        setExercises(chExercises)
      })
      .catch(() => setError('Leçon introuvable'))
      .finally(() => setLoading(false))
  }, [chapter])

  // Prefer lesson-specific diagrams extracted from PDF; fall back to exercise FENs
  const lessonDiagrams = lesson?.diagrams ?? []
  const diagrams: Array<{ label: string; fen: string }> = lessonDiagrams.length > 0
    ? lessonDiagrams.map((fen, i) => ({ label: `Diag. ${i + 1}`, fen }))
    : exercises.map((ex, i) => ({ label: `D${i + 1}`, fen: ex.initial_fen }))

  const activeFen = diagrams[activeDiagram]?.fen ?? exampleFen
  const board = fenToBoard(activeFen)
  const flipped = activeFen.startsWith('B:')

  const handleSquareClick = useCallback((sq: number) => {
    setHighlighted(prev => prev.includes(sq) ? prev.filter(s => s !== sq) : [...prev, sq])
  }, [])

  const handleDiagramClick = useCallback((n: number) => {
    const idx = n - 1
    if (idx >= 0 && idx < diagrams.length) {
      setActiveDiagram(idx)
      setHighlighted([])
    }
  }, [diagrams])

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

      {/* Board — fixed below header */}
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

        {/* Diagram selector buttons */}
        {diagrams.length > 0 && (
          <div className="flex items-center gap-1 mt-2 px-2 flex-wrap justify-center">
            {diagrams.map((d, idx) => {
              const isActive = activeDiagram === idx
              return (
                <button
                  key={idx}
                  onClick={() => { setActiveDiagram(idx); setHighlighted([]) }}
                  className={`px-2 py-0.5 text-xs rounded border cursor-pointer ${
                    isActive
                      ? 'bg-cyan-700 border-cyan-500 text-white font-bold'
                      : 'bg-gray-800 border-gray-600 text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {d.label}
                </button>
              )
            })}
          </div>
        )}

        <div className="flex items-center gap-4 mt-1.5">
          {highlighted.length > 0 && (
            <button
              onClick={() => setHighlighted([])}
              className="text-xs text-gray-500 hover:text-gray-300 underline"
            >
              Effacer sélection
            </button>
          )}
          <p className="text-xs text-gray-600">
            Clique sur un numéro → case · <span className="text-cyan-600">diag.</span> → damier
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
        {error && <p className="text-red-400 text-sm py-6 text-center">{error}</p>}
        {lesson && !loading && (
          <LessonText
            text={lesson.text}
            onSquareClick={handleSquareClick}
            onDiagramClick={handleDiagramClick}
            highlighted={highlighted}
          />
        )}
      </div>
    </div>
  )
}
