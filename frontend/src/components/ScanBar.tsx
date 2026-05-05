import React from 'react'
import type { ScanInfo } from '../lib/scanEngine'

interface ScanBarProps {
  info: ScanInfo | null
  loading?: boolean
}

function formatScore(score: number): string {
  const v = score / 100
  if (Math.abs(v) >= 90) return score > 0 ? '+♛' : '-♛'  // forced win
  if (v === 0) return '0.00'
  return (v > 0 ? '+' : '') + v.toFixed(2)
}

function formatNps(nps: number): string {
  if (nps >= 1_000_000) return `${(nps / 1_000_000).toFixed(1)}M`
  if (nps >= 1_000)     return `${(nps / 1_000).toFixed(0)}k`
  return String(nps)
}

export default function ScanBar({ info, loading = false }: ScanBarProps) {
  const isRunning = !info?.done || loading

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-950 border-b border-gray-800 text-xs font-mono select-none min-h-[28px]">
      {/* Status dot */}
      <span className={`text-[10px] ${isRunning ? 'text-green-400 animate-pulse' : 'text-green-600'}`}>●</span>

      {/* Engine label */}
      <span className="text-gray-500 font-sans">Scan 3.1</span>
      <span className="px-1 py-0.5 rounded text-[9px] font-bold bg-green-900 text-green-300">WASM</span>

      {!info && (
        <span className="text-gray-600 font-sans">Chargement…</span>
      )}

      {info && (
        <>
          <span className="text-gray-600">·</span>

          {/* Depth */}
          <span className="text-gray-400">
            <span className="text-gray-600 font-sans text-[10px]">Prof.</span>{' '}
            <span className="text-gray-200">{info.depth}</span>
          </span>

          <span className="text-gray-600">·</span>

          {/* Score */}
          <span className={
            info.score > 30  ? 'text-blue-300' :
            info.score < -30 ? 'text-red-400'  : 'text-gray-300'
          }>
            {formatScore(info.score)}
          </span>

          {/* Nodes/s */}
          {info.nps > 0 && (
            <>
              <span className="text-gray-600">·</span>
              <span className="text-gray-600">{formatNps(info.nps)} n/s</span>
            </>
          )}

          {/* Best move */}
          {info.pv.length > 0 && (
            <>
              <span className="text-gray-600">·</span>
              <span className="text-amber-400">{info.pv[0]}</span>
            </>
          )}
        </>
      )}
    </div>
  )
}
