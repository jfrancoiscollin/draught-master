import React, { useState, useEffect, useRef } from 'react'
import {
  startExerciseVerification,
  getExerciseVerificationStatus,
  ExerciseVerificationStatus,
  ExerciseIssue,
} from '../api/client'

type Dataset = 'all' | 'sens_du_jeu' | 'initial'

function buildReport(status: ExerciseVerificationStatus, dataset: Dataset): string {
  const date = new Date().toLocaleString('fr-FR')
  const mode = status.scan_available ? 'Légalité + Scan' : 'Légalité seule'
  const datasetLabel = dataset === 'all' ? 'Tous les exercices' : dataset === 'sens_du_jeu' ? 'Sens du Jeu' : 'Exercices de base'
  const lines: string[] = [
    `=== RAPPORT DE VÉRIFICATION DES EXERCICES ===`,
    `Date : ${date}`,
    `Jeu de données : ${datasetLabel}`,
    `Mode : ${mode}`,
    `Total : ${status.total} | OK : ${status.ok} | Illégaux : ${status.illegal}${status.scan_available ? ` | Scan mismatch : ${status.scan_mismatch}` : ''}`,
    ``,
  ]
  if (status.issues.length === 0) {
    lines.push('Tous les exercices sont valides.')
  } else {
    for (const issue of status.issues) {
      lines.push(`[${issue.status}] ${issue.name}`)
      lines.push(`  FEN     : ${issue.fen}`)
      lines.push(`  Stocké  : ${issue.stored_move}`)
      lines.push(`  Raison  : ${issue.reason}`)
      if (issue.scan_move) lines.push(`  Scan    : ${issue.scan_move}`)
      if (issue.legal_moves.length > 0)
        lines.push(`  Légaux  : ${issue.legal_moves.join(', ')}${issue.legal_moves.length >= 8 ? '…' : ''}`)
      lines.push(``)
    }
  }
  return lines.join('\n')
}

export default function ExerciseVerificationPanel() {
  const [status, setStatus] = useState<ExerciseVerificationStatus | null>(null)
  const [useScan, setUseScan] = useState(false)
  const [dataset, setDataset] = useState<Dataset>('all')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  useEffect(() => {
    getExerciseVerificationStatus().then(setStatus).catch(() => {})
    return stopPolling
  }, [])

  useEffect(() => {
    if (status?.status === 'running' && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        const s = await getExerciseVerificationStatus()
        setStatus(s)
        if (s.status !== 'running') stopPolling()
      }, 800)
    }
    if (status?.status !== 'running') stopPolling()
  }, [status?.status])

  const handleStart = async () => {
    setCopied(false)
    const res = await startExerciseVerification(useScan, 0.3, dataset)
    if (res.started) {
      const s = await getExerciseVerificationStatus()
      setStatus(s)
    }
  }

  const handleCopy = async () => {
    if (!status) return
    const report = buildReport(status, dataset)
    try {
      await navigator.clipboard.writeText(report)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = report
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  const progress = status && status.total > 0
    ? Math.round((status.done / status.total) * 100)
    : 0

  const isRunning = status?.status === 'running'
  const isDone = status?.status === 'done'

  return (
    <div className="space-y-3">
      {/* Dataset selector */}
      <div className="flex gap-1.5 text-xs">
        {(['all', 'initial', 'sens_du_jeu'] as Dataset[]).map(ds => (
          <button
            key={ds}
            onClick={() => setDataset(ds)}
            disabled={isRunning}
            className={`flex-1 rounded-lg px-2 py-1.5 border transition-colors ${
              dataset === ds
                ? 'bg-indigo-700 border-indigo-500 text-white'
                : 'bg-gray-800 border-gray-600 text-gray-400 hover:border-gray-500'
            }`}
          >
            {ds === 'all' ? 'Tous (480)' : ds === 'initial' ? 'Base (408)' : 'Sens du Jeu (72)'}
          </button>
        ))}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleStart}
          disabled={isRunning}
          className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl px-4 py-2.5 transition-colors"
        >
          {isRunning ? (
            <>
              <span className="animate-spin text-base">⟳</span>
              Vérification… {status.done}/{status.total}
            </>
          ) : (
            <>🔍 Lancer la vérification</>
          )}
        </button>
        <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={useScan}
            onChange={e => setUseScan(e.target.checked)}
            disabled={isRunning}
            className="rounded"
          />
          + Scan
        </label>
      </div>

      {/* Progress bar */}
      {isRunning && (
        <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 transition-all duration-300 rounded-full"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Summary */}
      {status && (isDone || isRunning) && (
        <div className="flex gap-2 text-xs">
          <span className="flex-1 bg-green-900/40 border border-green-800 text-green-400 rounded-lg px-3 py-2 text-center font-semibold">
            ✓ {status.ok} OK
          </span>
          <span className="flex-1 bg-red-900/40 border border-red-800 text-red-400 rounded-lg px-3 py-2 text-center font-semibold">
            ✗ {status.illegal} illégaux
          </span>
          {status.scan_available && (
            <span className="flex-1 bg-yellow-900/40 border border-yellow-800 text-yellow-400 rounded-lg px-3 py-2 text-center font-semibold">
              ? {status.scan_mismatch} Scan
            </span>
          )}
        </div>
      )}

      {/* Copy report button */}
      {isDone && (
        <button
          onClick={handleCopy}
          className="w-full flex items-center justify-center gap-2 bg-gray-700 hover:bg-gray-600 border border-gray-600 text-sm text-gray-200 rounded-xl px-4 py-2.5 transition-colors"
        >
          {copied ? '✓ Rapport copié !' : '📋 Copier le rapport complet'}
        </button>
      )}

      {/* Issue list */}
      {isDone && status.issues.length > 0 && (
        <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
          {status.issues.map((issue) => (
            <IssueRow
              key={issue.name}
              issue={issue}
              open={expanded === issue.name}
              onToggle={() => setExpanded(expanded === issue.name ? null : issue.name)}
            />
          ))}
        </div>
      )}

      {isDone && status.issues.length === 0 && (
        <p className="text-xs text-green-400 text-center py-1">✓ Tous les exercices sont valides</p>
      )}
    </div>
  )
}

function IssueRow({ issue, open, onToggle }: {
  issue: ExerciseIssue
  open: boolean
  onToggle: () => void
}) {
  const isIllegal = issue.status === 'ILLEGAL'
  return (
    <div className={`rounded-lg border text-xs overflow-hidden ${isIllegal ? 'border-red-800 bg-red-950/30' : 'border-yellow-800 bg-yellow-950/30'}`}>
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2 text-left"
      >
        <span className={isIllegal ? 'text-red-400' : 'text-yellow-400'}>
          {isIllegal ? '✗' : '?'}
        </span>
        <span className="flex-1 font-medium text-gray-200 truncate">{issue.name}</span>
        <span className={isIllegal ? 'text-red-400' : 'text-yellow-400'}>
          {issue.stored_move}
        </span>
        <span className="text-gray-500">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-1.5 border-t border-gray-700 pt-2">
          <p className="text-gray-400"><span className="text-gray-500">Raison :</span> {issue.reason}</p>
          {issue.scan_move && (
            <p className="text-yellow-300"><span className="text-gray-500">Scan suggère :</span> {issue.scan_move}</p>
          )}
          {issue.legal_moves.length > 0 && (
            <p className="text-gray-400">
              <span className="text-gray-500">Coups légaux :</span>{' '}
              {issue.legal_moves.join(', ')}{issue.legal_moves.length >= 8 ? '…' : ''}
            </p>
          )}
          <p className="text-gray-600 break-all"><span className="text-gray-500">FEN :</span> {issue.fen}</p>
        </div>
      )}
    </div>
  )
}
