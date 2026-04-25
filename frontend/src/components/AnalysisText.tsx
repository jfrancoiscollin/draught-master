import React from 'react'

// Normalise all Unicode dash/minus variants → ASCII hyphen, × → x
const DASH_VARIANTS = /[‐‑‒–—―−﹘﹣－]/g
function normalise(s: string): string {
  return s.replace(DASH_VARIANTS, '-').replace(/×/g, 'x')
}

// Match standard draughts PDN after normalisation: "34-30", "32x21", "32x21x10"
// Uses negative lookaround instead of \b to avoid edge-cases with hyphens
const MOVE_RE = /(?<!\d)(\d{1,2}(?:[-x]\d{1,2})+)(?!\d)/g

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

  const nodes: React.ReactNode[] = []
  let last = 0
  let keyIdx = 0
  const re = new RegExp(MOVE_RE.source, 'g')
  let m: RegExpExecArray | null

  while ((m = re.exec(norm)) !== null) {
    const pdn = m[1] ?? m[0]
    if (!isValidMove(pdn)) continue
    if (m.index > last) nodes.push(text.slice(last, m.index))
    nodes.push(
      onMoveClick ? (
        <button
          key={keyIdx++}
          type="button"
          onClick={() => onMoveClick(pdn)}
          className="text-amber-400 hover:text-amber-200 font-mono font-semibold underline decoration-dotted cursor-pointer bg-amber-950/30 rounded px-0.5"
        >
          {pdn}
        </button>
      ) : (
        <span key={keyIdx++} className="font-mono font-semibold text-amber-400 bg-amber-950/30 rounded px-0.5">{pdn}</span>
      )
    )
    last = m.index + pdn.length
  }
  if (last < text.length) nodes.push(text.slice(last))

  return <span className={className}>{nodes}</span>
}
