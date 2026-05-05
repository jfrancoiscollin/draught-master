import React, { useState, useEffect, useCallback, useRef } from 'react'
import Board from './Board'
import AnalysisPanel from './AnalysisPanel'
import ScanBar from './ScanBar'
import { useScanEngine } from '../hooks/useScanEngine'
import { getScanEngine } from '../lib/scanEngine'
import type { Arrow } from './Board'
import {
  importPdn, getPositionLegalMoves, applyPositionMove,
  analyzePositionFen, getPositionBestMove,
} from '../api/client'
import type { PdnPosition, PdnImportResult } from '../api/client'
import { fenToBoard } from '../utils/fen'
import { useLanguage } from '../i18n/LanguageContext'
import type { MoveData, AnalysisResponse } from '../types'

interface ImportGamePanelProps {
  onClose: () => void
}

export default function ImportGamePanel({ onClose }: ImportGamePanelProps) {
  const { language } = useLanguage()

  // ── Import phase ──────────────────────────────────────────────
  const [pdn, setPdn] = useState('')
  const [importing, setImporting] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)
  const [result, setResult] = useState<PdnImportResult | null>(null)

  // ── Review phase ──────────────────────────────────────────────
  const [currentIdx, setCurrentIdx] = useState(0)
  const [currentFen, setCurrentFen] = useState('')
  const [legalMoves, setLegalMoves] = useState<MoveData[]>([])
  const [selectedSquare, setSelectedSquare] = useState<number | null>(null)
  const [isDiverted, setIsDiverted] = useState(false)
  const [highlighted, setHighlighted] = useState<number[]>([])
  const loadingMovesRef = useRef(false)

  // ── Analysis ──────────────────────────────────────────────────
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [aiThinking, setAiThinking] = useState(false)

  // ── WASM engine (continuous evaluation) ───────────────────────
  const scanInfo = useScanEngine(result ? currentFen : null)

  // ── Best-move arrow ────────────────────────────────────────────
  const [arrow, setArrow] = useState<Arrow | null>(null)

  const loadLegalMoves = useCallback(async (fen: string) => {
    if (!fen || loadingMovesRef.current) return
    loadingMovesRef.current = true
    try {
      const moves = await getPositionLegalMoves(fen)
      setLegalMoves(moves)
    } catch {
      setLegalMoves([])
    } finally {
      loadingMovesRef.current = false
    }
  }, [])

  const goTo = useCallback((idx: number, positions: PdnPosition[]) => {
    const pos = positions[Math.max(0, Math.min(idx, positions.length - 1))]
    setCurrentIdx(idx)
    setCurrentFen(pos.fen)
    setIsDiverted(false)
    setSelectedSquare(null)
    setHighlighted([])
    setAnalysis(null)
    setArrow(null)
    loadLegalMoves(pos.fen)
  }, [loadLegalMoves])

  // Keyboard navigation ← →
  useEffect(() => {
    if (!result) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') goTo(Math.max(0, currentIdx - 1), result.positions)
      else if (e.key === 'ArrowRight') goTo(Math.min(result.positions.length - 1, currentIdx + 1), result.positions)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [result, currentIdx, goTo])

  const handleImport = async () => {
    if (!pdn.trim()) return
    setImporting(true)
    setImportError(null)
    try {
      const data = await importPdn(pdn)
      setResult(data)
      setCurrentIdx(0)
      setCurrentFen(data.positions[0].fen)
      loadLegalMoves(data.positions[0].fen)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setImportError(detail ?? 'Erreur lors de l\'import')
    } finally {
      setImporting(false)
    }
  }

  const handleMove = useCallback(async (move: MoveData) => {
    setSelectedSquare(null)
    setArrow(null)
    try {
      const res = await applyPositionMove(currentFen, move.path)
      setCurrentFen(res.fen)
      setLegalMoves(res.moves)
      setIsDiverted(true)
      setAnalysis(null)
    } catch {
      loadLegalMoves(currentFen)
    }
  }, [currentFen, loadLegalMoves])

  const handleAnalyze = useCallback(async (question?: string, mode?: string) => {
    setAnalysisLoading(true)
    try {
      const analysisMode = mode ?? 'position'
      // For full game analysis, extract all PDN moves up to the current position
      const moveHistory = (analysisMode === 'full_game' && result)
        ? result.positions.slice(1, currentIdx + 1).map(p => p.notation).filter((n): n is string => n !== null)
        : undefined
      const res = await analyzePositionFen(currentFen, question, language, analysisMode, moveHistory)
      setAnalysis(res)
      return res
    } catch {
      return null
    } finally {
      setAnalysisLoading(false)
    }
  }, [currentFen, language, result, currentIdx])

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const text = await file.text()
    setPdn(text)
    setImportError(null)
    // Auto-import after reading the file
    setImporting(true)
    try {
      const data = await importPdn(text)
      setResult(data)
      setCurrentIdx(0)
      setCurrentFen(data.positions[0].fen)
      loadLegalMoves(data.positions[0].fen)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setImportError(detail ?? 'Erreur lors de l\'import')
    } finally {
      setImporting(false)
      // Reset input so the same file can be re-selected
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  function hubNotationToArrow(hub: string): Arrow | null {
    const sep = hub.includes('x') ? 'x' : hub.includes('-') ? '-' : null
    if (!sep) return null
    const parts = hub.split(sep).map(Number)
    if (parts.length < 2 || isNaN(parts[0]) || isNaN(parts[parts.length - 1])) return null
    return { from: parts[0], to: parts[parts.length - 1] }
  }

  const handleBestMove = useCallback(async (): Promise<string[] | null> => {
    setAiThinking(true)
    setArrow(null)
    try {
      const engine = getScanEngine()
      let hubMove: string | null = await engine.getMove(currentFen, 1500)
      // Fallback to server if WASM not ready
      if (!hubMove) hubMove = await getPositionBestMove(currentFen)
      if (!hubMove) return null
      const a = hubNotationToArrow(hubMove)
      if (a) setArrow(a)
      return [hubMove]
    } catch {
      return null
    } finally {
      setAiThinking(false)
    }
  }, [currentFen])

  // ── Import phase UI ───────────────────────────────────────────
  if (!result) {
    return (
      <div className="flex flex-col h-full bg-gray-900 text-gray-100">
        <div className="flex items-center gap-3 px-4 py-3 bg-gray-800 border-b border-gray-700 flex-shrink-0">
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-amber-500 text-2xl w-9 h-9 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors"
          >
            ←
          </button>
          <h2 className="font-bold text-amber-500 text-base">Importer une partie</h2>
        </div>

        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5">
          <p className="text-gray-400 text-sm text-center">
            Sélectionnez un fichier <span className="text-amber-400 font-mono">.pdn</span> exporté depuis lidraughts ou un autre logiciel.
          </p>

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileChange}
          />

          {/* Drop zone / pick button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="w-full flex flex-col items-center gap-3 border-2 border-dashed border-gray-600 hover:border-amber-500 rounded-xl py-12 px-4 transition-colors disabled:opacity-40 cursor-pointer"
          >
            <span className="text-5xl">📂</span>
            <span className="text-white font-semibold text-sm">
              {importing ? 'Chargement…' : 'Choisir un fichier .pdn'}
            </span>
            <span className="text-gray-500 text-xs">lidraughts · DraughtsBoard · etc.</span>
          </button>

          {importError && (
            <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded px-3 py-2">
              {importError}
            </p>
          )}
        </div>
      </div>
    )
  }

  // ── Review phase UI ───────────────────────────────────────────
  const positions = result.positions
  const meta = result.metadata
  const currentPos = positions[currentIdx]
  const board = fenToBoard(currentFen)
  const flipped = positions[0].fen.startsWith('B:')

  const moveLabel = currentIdx === 0
    ? 'Position initiale'
    : `Coup ${currentPos.move_number} · ${currentPos.color === 'white' ? '⬜' : '⬛'} ${currentPos.notation}`

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 bg-gray-800 border-b border-gray-700 flex-shrink-0">
        <button
          onClick={() => { setResult(null); setPdn('') }}
          className="text-gray-400 hover:text-amber-500 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors"
        >
          ←
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-amber-500 font-bold text-sm truncate">
            {(meta.white && meta.black) ? `${meta.white} — ${meta.black}` : 'Partie importée'}
          </p>
          {(meta.result || meta.event) && (
            <p className="text-gray-500 text-xs truncate">
              {[meta.result, meta.event, meta.date].filter(Boolean).join(' · ')}
            </p>
          )}
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-300 text-sm px-1">✕</button>
      </div>

      {/* Board + navigation — fixed */}
      <div className="flex-shrink-0 flex flex-col items-center py-2 bg-gray-900 border-b border-gray-700">
        <div style={{ width: '100%', maxWidth: 240 }}>
          <Board
            board={board}
            legalMoves={legalMoves}
            onMove={handleMove}
            selectedSquare={selectedSquare}
            onSelectSquare={setSelectedSquare}
            disabled={false}
            highlightSquares={highlighted}
            arrows={arrow ? [arrow] : []}
            flipped={flipped}
          />
        </div>

        {/* Navigation arrows */}
        <div className="flex items-center gap-2 mt-2 w-full max-w-xs px-2">
          <button
            onClick={() => goTo(Math.max(0, currentIdx - 1), positions)}
            disabled={currentIdx === 0}
            className="w-10 h-10 flex items-center justify-center rounded-lg bg-gray-800 border border-gray-600 text-white disabled:opacity-25 text-2xl hover:bg-gray-700 transition-colors cursor-pointer"
          >
            ‹
          </button>
          <div className="flex-1 text-center">
            <p className="text-xs text-gray-200 truncate">{moveLabel}</p>
            <p className="text-xs text-gray-600">{currentIdx} / {result.total_moves}</p>
          </div>
          <button
            onClick={() => goTo(Math.min(positions.length - 1, currentIdx + 1), positions)}
            disabled={currentIdx >= positions.length - 1}
            className="w-10 h-10 flex items-center justify-center rounded-lg bg-gray-800 border border-gray-600 text-white disabled:opacity-25 text-2xl hover:bg-gray-700 transition-colors cursor-pointer"
          >
            ›
          </button>
        </div>

        {isDiverted && (
          <button
            onClick={() => goTo(currentIdx, positions)}
            className="mt-1.5 text-xs text-amber-500 hover:text-amber-300 underline cursor-pointer"
          >
            ↺ Revenir à la partie importée
          </button>
        )}
      </div>

      {/* Scan WASM engine bar */}
      <ScanBar info={scanInfo} />

      {/* Move list — horizontal scrollable strip */}
      <div className="flex-shrink-0 flex gap-1 px-2 py-1.5 overflow-x-auto bg-gray-950 border-b border-gray-800">
        {positions.map((pos, idx) => {
          const isActive = idx === currentIdx
          if (idx === 0) return (
            <button
              key={0}
              onClick={() => goTo(0, positions)}
              className={`px-2 py-0.5 rounded text-xs flex-shrink-0 cursor-pointer ${isActive ? 'bg-amber-700 text-white font-bold' : 'text-gray-500 hover:text-gray-300'}`}
            >
              départ
            </button>
          )
          if (pos.color === 'white') {
            return (
              <button
                key={idx}
                onClick={() => goTo(idx, positions)}
                className={`px-2 py-0.5 rounded text-xs flex-shrink-0 cursor-pointer border ${isActive ? 'bg-amber-700 border-amber-500 text-white font-bold' : 'border-gray-700 text-gray-400 hover:text-gray-200'}`}
              >
                {pos.move_number}. {pos.notation}
              </button>
            )
          }
          return (
            <button
              key={idx}
              onClick={() => goTo(idx, positions)}
              className={`px-2 py-0.5 rounded text-xs flex-shrink-0 cursor-pointer ${isActive ? 'bg-amber-700 text-white font-bold' : 'text-gray-500 hover:text-gray-300'}`}
            >
              {pos.notation}
            </button>
          )
        })}
      </div>

      {/* Analysis panel — scrollable */}
      <div className="flex-1 overflow-y-auto overscroll-contain">
        <AnalysisPanel
          gameId="import"
          onAnalyze={handleAnalyze}
          onBestMove={handleBestMove}
          analysis={analysis}
          loading={analysisLoading}
          onHighlightSquare={setHighlighted}
          aiThinking={aiThinking}
        />
      </div>
    </div>
  )
}
