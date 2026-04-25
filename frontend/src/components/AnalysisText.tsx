import React from 'react'

// Matches draughts move notation: "34-30", "32x21", "32x21x10", "32×21", "34–30" (en-dash)
const MOVE_RE = /\b(\d{1,2}(?:[-–x×]\d{1,2})+)\b/g

function isValidMove(s: string): boolean {
  return s.split(/[-–x×]/).every(n => {
    const v = parseInt(n, 10)
    return v >= 1 && v <= 50
  })
}

interface Props {
  text: string
  onMoveClick?: (pdn: string) => void
  className?: string
}

export default function AnalysisText({ text, onMoveClick, className }: Props) {
  const nodes: React.ReactNode[] = []
  let last = 0
  let keyIdx = 0
  const re = new RegExp(MOVE_RE.source, 'g')
  let m: RegExpExecArray | null

  while ((m = re.exec(text)) !== null) {
    if (!isValidMove(m[0])) continue
    if (m.index > last) nodes.push(text.slice(last, m.index))
    const pdn = m[0]
    nodes.push(
      onMoveClick ? (
        <button
          key={keyIdx++}
          type="button"
          onClick={() => onMoveClick(pdn)}
          className="text-amber-400 hover:text-amber-200 font-mono font-semibold underline decoration-dotted cursor-pointer"
        >
          {pdn}
        </button>
      ) : (
        <span key={keyIdx++} className="font-mono font-semibold text-amber-400">{pdn}</span>
      )
    )
    last = m.index + pdn.length
  }
  if (last < text.length) nodes.push(text.slice(last))

  return <span className={className}>{nodes}</span>
}
