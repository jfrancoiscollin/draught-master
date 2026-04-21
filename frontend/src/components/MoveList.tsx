import React, { useState, useEffect, useRef } from 'react'
import type { MoveData } from '../types'
import { useLanguage } from '../i18n/LanguageContext'

function moveToPdn(move: MoveData): string {
  if (move.captures.length > 0) {
    return move.path.join('x')
  }
  return move.path.join('-')
}

interface MoveListProps {
  moves: MoveData[]
  currentMoveIndex?: number
}

export default function MoveList({ moves, currentMoveIndex }: MoveListProps) {
  const { t } = useLanguage()
  const [open, setOpen] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open && endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [moves.length, open])

  const pairs: Array<{ white?: MoveData; black?: MoveData; index: number }> = []
  for (let i = 0; i < moves.length; i += 2) {
    pairs.push({ white: moves[i], black: moves[i + 1], index: i })
  }

  return (
    <div className="panel flex flex-col gap-2">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center justify-between w-full text-left"
      >
        <h3 className="text-lg font-bold text-amber-600">{t('moveList')}</h3>
        <span className="text-gray-400 text-sm flex items-center gap-1">
          {moves.length > 0 && (
            <span className="bg-gray-700 text-gray-300 text-xs px-1.5 py-0.5 rounded-full">
              {moves.length}
            </span>
          )}
          <span>{open ? '▲' : '▼'}</span>
        </span>
      </button>

      {open && (
        <div className="max-h-40 overflow-y-auto font-mono text-sm">
          {pairs.length === 0 ? (
            <p className="text-gray-500 italic text-xs">{t('noMoves')}</p>
          ) : (
            <table className="w-full border-collapse">
              <tbody>
                {pairs.map(pair => (
                  <tr key={pair.index} className="border-b border-gray-700">
                    <td className="text-gray-500 pr-2 py-0.5 text-right w-8 text-xs">
                      {pair.index / 2 + 1}.
                    </td>
                    <td
                      className={`px-1 py-0.5 rounded ${
                        currentMoveIndex === pair.index
                          ? 'bg-amber-900 text-white'
                          : 'text-gray-200'
                      }`}
                    >
                      {pair.white ? moveToPdn(pair.white) : ''}
                    </td>
                    <td
                      className={`px-1 py-0.5 rounded ${
                        currentMoveIndex === pair.index + 1
                          ? 'bg-amber-900 text-white'
                          : 'text-gray-400'
                      }`}
                    >
                      {pair.black ? moveToPdn(pair.black) : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div ref={endRef} />
        </div>
      )}
    </div>
  )
}
