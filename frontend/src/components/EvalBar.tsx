import React, { useState, useEffect } from 'react'
import { getScanEngine } from '../lib/scanEngine'

interface EvalBarProps {
  fen: string | null
}

// Material balance from FEN: man=100cp, king=150cp, positive=white
function materialCp(fen: string): number {
  let score = 0
  const parts = fen.split(':')
  for (let i = 1; i < parts.length; i++) {
    const section = parts[i]
    if (!section) continue
    const sign = section[0] === 'W' ? 1 : -1
    for (const token of section.slice(1).split(',')) {
      if (!token) continue
      score += sign * (token.startsWith('K') ? 150 : 100)
    }
  }
  return score
}

const toPct = (cp: number) => Math.round((2 / (1 + Math.exp(-0.015 * cp)) - 1 + 1) / 2 * 100)

export default function EvalBar({ fen }: EvalBarProps) {
  const [whitePct, setWhitePct] = useState(50)

  useEffect(() => {
    if (!fen) { setWhitePct(50); return }

    // Immediate: material balance (instant, always reliable)
    const mat = materialCp(fen)
    setWhitePct(toPct(mat))

    // Async: engine positional evaluation (overrides material only when nonzero)
    let cancelled = false
    getScanEngine().evaluate(fen, 1500).then(res => {
      if (cancelled || !res || res.score === 0) return
      const cp = fen.startsWith('B:') ? -res.score : res.score
      setWhitePct(toPct(cp))
    })
    return () => { cancelled = true }
  }, [fen])

  // Use flex proportions for smooth, reliable animation in flex columns
  const blackFlex = 100 - whitePct
  const whiteFlex = whitePct

  return (
    <div style={{
      width: 12,
      flexShrink: 0,
      alignSelf: 'stretch',
      display: 'flex',
      flexDirection: 'column',
      borderRadius: 3,
      overflow: 'hidden',
      border: '1px solid rgba(255,255,255,0.08)',
    }}>
      {/* Black on top */}
      <div style={{
        flex: blackFlex,
        background: 'linear-gradient(180deg, #1a0e06 0%, #2a1a0a 100%)',
        transition: 'flex 0.5s ease',
      }} />
      {/* White on bottom */}
      <div style={{
        flex: whiteFlex,
        background: 'linear-gradient(180deg, #c8b888 0%, #e8d8b0 100%)',
        transition: 'flex 0.5s ease',
      }} />
    </div>
  )
}
