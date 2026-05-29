import React from 'react'
import type { BookTip } from '../types'
import Board from './Board'
import { fenToBoard } from '../utils/fen'

/** Illustrative positions mined from the manuals for a knowledge-base
 *  tip — rendered as small static boards beside the advice. Shared by
 *  the collapsed AnalysisPanel and the expanded analysis view. */
const TipExamples: React.FC<{ tip: BookTip; lang: 'fr' | 'en' }> = ({ tip, lang }) => {
  const examples = tip.example_positions ?? []
  if (examples.length === 0) return null
  return (
    <div>
      <div className="text-xs text-gray-400 uppercase font-semibold mb-1">
        {lang === 'fr' ? 'Exemples dans les manuels' : 'Examples in the manuals'}
      </div>
      <div className="flex flex-wrap gap-3">
        {examples.map(ex => (
          <div key={ex.id} className="w-36">
            <div className="w-36">
              <Board
                board={fenToBoard(ex.fen)}
                legalMoves={[]}
                onMove={() => {}}
                selectedSquare={null}
                onSelectSquare={() => {}}
                disabled
              />
            </div>
            <div className="text-[10px] text-gray-500 mt-0.5 text-center">
              {ex.source} · {lang === 'fr' ? 'diag.' : 'diag.'} {ex.number} (p.{ex.page})
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default TipExamples
