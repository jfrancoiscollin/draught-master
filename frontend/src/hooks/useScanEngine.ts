import { useEffect, useState, useRef } from 'react'
import { getScanEngine } from '../lib/scanEngine'
import type { ScanInfo } from '../lib/scanEngine'

export function useScanEngine(fen: string | null): ScanInfo | null {
  const [info, setInfo] = useState<ScanInfo | null>(null)
  const prevFen = useRef<string | null>(null)

  useEffect(() => {
    if (!fen) {
      setInfo(null)
      return
    }
    if (fen === prevFen.current) return
    prevFen.current = fen
    setInfo(null)

    const engine = getScanEngine()
    if (!engine.available) return

    engine.analyze(fen, (newInfo) => setInfo(newInfo))

    return () => { engine.stop() }
  }, [fen])

  return info
}
