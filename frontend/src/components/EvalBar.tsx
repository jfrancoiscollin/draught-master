import React, { useState, useEffect } from 'react'
import { getScanEngine } from '../lib/scanEngine'

interface EvalBarProps {
  fen: string | null
}

export default function EvalBar({ fen }: EvalBarProps) {
  const [whitePct, setWhitePct] = useState(50)

  useEffect(() => {
    if (!fen) { setWhitePct(50); return }
    let cancelled = false
    getScanEngine().evaluate(fen, 200).then(res => {
      if (cancelled || !res) return
      // Scan score is from side-to-move perspective; convert to white's
      const cp = fen.startsWith('B:') ? -res.score : res.score
      const wc = 2 / (1 + Math.exp(-0.015 * cp)) - 1  // [-1,+1], positive = white
      setWhitePct(Math.round((wc + 1) / 2 * 100))
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
