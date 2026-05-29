import React, { useCallback, useEffect, useRef, useState } from 'react'

interface Props {
  source: string
  initialPage?: number
  onClose: () => void
  lang?: 'fr' | 'en'
}

/**
 * Manual diagram cropper for sources without an automated extraction
 * pipeline (Roozenburg, Keller — text-heavy books where the
 * texture-variance board detector breaks down).
 *
 * Flow:
 *  1. Operator picks a page number; the rendered JPG fills the canvas.
 *  2. Two taps/clicks mark the top-left and bottom-right corners of a
 *     diagram on the page.
 *  3. The (x0, y0, x1, y1) bbox is shown alongside a ``Diagramme N``
 *     number input and a "Copier" button that puts the JSON manifest
 *     entry on the clipboard.
 *  4. JF pastes the entry into ``diagrams_manifest.json`` via PR, then
 *     ``/api/strategy/diagram`` crops the page-image on the fly using
 *     that bbox — no separate JPEG bundled in the repo.
 *
 * Mobile-friendly: works with one-finger taps, no drag.  The image is
 * scaled to fit the viewport and the bbox coordinates are mapped back
 * to the original page-image resolution before being copied.
 */
const CropTool: React.FC<Props> = ({ source, initialPage, onClose, lang = 'fr' }) => {
  const [page, setPage] = useState<string>(initialPage ? String(initialPage) : '')
  const [number, setNumber] = useState<string>('1')
  const [corners, setCorners] = useState<{ x: number; y: number }[]>([])
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number } | null>(null)
  const [copied, setCopied] = useState(false)
  const imgRef = useRef<HTMLImageElement | null>(null)

  // Reset everything when the page changes — the previous corners are
  // tied to a specific page-image and can't be reused across pages.
  useEffect(() => {
    setCorners([])
    setNaturalSize(null)
    setCopied(false)
  }, [page, source])

  const handleImgClick = useCallback(
    (e: React.MouseEvent<HTMLImageElement>) => {
      const img = imgRef.current
      if (!img || !naturalSize) return
      const rect = img.getBoundingClientRect()
      // Map screen coordinates back to the page-image's *native*
      // resolution — that's what the backend's PIL.crop expects.
      const scaleX = naturalSize.w / rect.width
      const scaleY = naturalSize.h / rect.height
      const x = Math.round((e.clientX - rect.left) * scaleX)
      const y = Math.round((e.clientY - rect.top) * scaleY)
      setCorners(prev => {
        if (prev.length >= 2) return [{ x, y }] // 3rd click restarts
        return [...prev, { x, y }]
      })
      setCopied(false)
    },
    [naturalSize],
  )

  const bbox = corners.length === 2
    ? [
        Math.min(corners[0].x, corners[1].x),
        Math.min(corners[0].y, corners[1].y),
        Math.max(corners[0].x, corners[1].x),
        Math.max(corners[0].y, corners[1].y),
      ]
    : null

  const manifestEntry = bbox && page && number
    ? {
        page: parseInt(page, 10),
        number: parseInt(number, 10),
        bbox,
      }
    : null

  const copyEntry = useCallback(() => {
    if (!manifestEntry) return
    const text = JSON.stringify(manifestEntry, null, 2)
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      // Auto-advance the diagram number so multi-crop sessions on the
      // same page don't require manual increment between entries.
      setNumber(n => String((parseInt(n, 10) || 0) + 1))
      setCorners([])
    })
  }, [manifestEntry])

  const pageUrl = page
    ? `/api/strategy/page-image?source=${encodeURIComponent(source)}&page=${page}`
    : null

  // Overlay positions for the corner markers + bbox rectangle, in
  // *display* coordinates (so they line up visually).
  const overlay = (() => {
    const img = imgRef.current
    if (!img || !naturalSize) return null
    const rect = img.getBoundingClientRect()
    const scaleX = rect.width / naturalSize.w
    const scaleY = rect.height / naturalSize.h
    return { scaleX, scaleY }
  })()

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-90 flex flex-col z-50"
      onClick={e => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <header className="flex items-center justify-between bg-gray-900 border-b border-gray-700 px-4 py-2 gap-2">
        <span className="text-amber-400 font-semibold text-sm">
          {source} · {lang === 'fr' ? 'Crop manuel' : 'Manual crop'}
        </span>
        <div className="flex items-center gap-2 text-xs text-gray-300">
          <label className="flex items-center gap-1">
            {lang === 'fr' ? 'Page' : 'Page'}
            <input
              type="number"
              min={1}
              value={page}
              onChange={e => setPage(e.target.value)}
              className="bg-gray-800 text-gray-100 rounded px-2 py-1 border border-gray-700 w-20"
            />
          </label>
          <label className="flex items-center gap-1">
            #
            <input
              type="number"
              min={1}
              value={number}
              onChange={e => setNumber(e.target.value)}
              className="bg-gray-800 text-gray-100 rounded px-2 py-1 border border-gray-700 w-16"
            />
          </label>
          <button
            onClick={copyEntry}
            disabled={!manifestEntry}
            className="px-2 py-1 bg-amber-700 hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs rounded font-medium"
          >
            {copied
              ? lang === 'fr' ? '✓ copié' : '✓ copied'
              : lang === 'fr' ? 'Copier entrée' : 'Copy entry'}
          </button>
          <button
            onClick={onClose}
            className="px-2 py-1 rounded hover:bg-gray-800"
            title="Esc"
          >
            ×
          </button>
        </div>
      </header>
      <div className="flex-1 overflow-auto p-4 flex items-start justify-center relative">
        {!pageUrl && (
          <p className="text-gray-400 text-sm mt-8">
            {lang === 'fr'
              ? 'Entre un numéro de page pour charger l’image.'
              : 'Enter a page number to load the image.'}
          </p>
        )}
        {pageUrl && (
          <div className="relative inline-block">
            <img
              ref={imgRef}
              src={pageUrl}
              alt={`${source} page ${page}`}
              onLoad={e => {
                const img = e.currentTarget
                setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight })
              }}
              onClick={handleImgClick}
              className="max-w-full max-h-[80vh] cursor-crosshair select-none"
              draggable={false}
            />
            {/* Corner markers — small amber dots so the operator sees
                where they tapped without losing the underlying pixel. */}
            {overlay && corners.map((c, i) => (
              <div
                key={i}
                className="absolute pointer-events-none w-3 h-3 -ml-1.5 -mt-1.5 rounded-full bg-amber-400 ring-2 ring-amber-900"
                style={{
                  left: c.x * overlay.scaleX,
                  top: c.y * overlay.scaleY,
                }}
              />
            ))}
            {/* Bbox rectangle once both corners are placed. */}
            {overlay && bbox && (
              <div
                className="absolute pointer-events-none border-2 border-amber-400 bg-amber-400 bg-opacity-10"
                style={{
                  left: bbox[0] * overlay.scaleX,
                  top: bbox[1] * overlay.scaleY,
                  width: (bbox[2] - bbox[0]) * overlay.scaleX,
                  height: (bbox[3] - bbox[1]) * overlay.scaleY,
                }}
              />
            )}
          </div>
        )}
      </div>
      <footer className="bg-gray-900 border-t border-gray-700 px-4 py-2 text-xs text-gray-400 flex items-center gap-3">
        <span>
          {lang === 'fr'
            ? corners.length === 0
              ? 'Tape le coin supérieur-gauche du diagramme.'
              : corners.length === 1
              ? 'Tape le coin inférieur-droit.'
              : 'Bbox prête — vérifier le numéro puis copier.'
            : corners.length === 0
            ? 'Tap the top-left corner of the diagram.'
            : corners.length === 1
            ? 'Tap the bottom-right corner.'
            : 'Bbox ready — check the number then copy.'}
        </span>
        {manifestEntry && (
          <code className="text-amber-300 ml-auto">
            {JSON.stringify(manifestEntry)}
          </code>
        )}
      </footer>
    </div>
  )
}

export default CropTool
