import React from 'react'

// Normalise Unicode dashes/minus → ASCII hyphen, × → x
const DASH_VARIANTS = /[‐‑‒–—―−﹘﹣－­]/g
function normalise(s: string): string {
  return s.replace(DASH_VARIANTS, '-').replace(/×/g, 'x')
}

// Split on potential move patterns — simplest possible, no lookbehind/\b
const MOVE_SPLIT_RE = /(\d{1,2}(?:[-x]\d{1,2})+)/g

function isValidMove(s: string): boolean {
  const parts = s.split(/[-x]/)
  return parts.length >= 2 && parts.every(p => {
    const n = parseInt(p, 10)
    return !isNaN(n) && n >= 1 && n <= 50
  })
}

interface Props {
  text: string
  onMoveClick?: (pdn: string) => void
  className?: string
}

export default function AnalysisText({ text, onMoveClick, className }: Props) {
  const norm = normalise(text)
  // split() with a capturing group alternates: [plain, match, plain, match, ...]
  const parts = norm.split(MOVE_SPLIT_RE)

  const nodes: React.ReactNode[] = []
  let moveCount = 0
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i]
    if (!part) continue
    if (i % 2 === 1 && isValidMove(part)) {
      moveCount++
      nodes.push(
        onMoveClick ? (
          <button
            key={i}
            type="button"
            onClick={() => onMoveClick(part)}
            className="text-amber-400 hover:text-amber-200 font-mono font-semibold underline decoration-dotted cursor-pointer bg-amber-950/30 rounded px-0.5"
          >
            {part}
          </button>
        ) : (
          <span key={i} className="font-mono font-semibold text-amber-400 bg-amber-950/30 rounded px-0.5">
            {part}
          </span>
        )
      )
    } else {
      nodes.push(part)
    }
  }

  // Diagnostic badge — remove once confirmed working
  return (
    <span className={className}>
      <span className="text-xs text-amber-500 font-mono mr-1">[v4:{moveCount}]</span>
      {nodes}
    </span>
  )
}
