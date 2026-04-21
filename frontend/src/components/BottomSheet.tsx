import React from 'react'

interface BottomSheetProps {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}

export default function BottomSheet({ open, onClose, title, children }: BottomSheetProps) {
  if (!open) return null
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        onClick={onClose}
      />
      {/* Sheet */}
      <div className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-gray-800 rounded-t-2xl shadow-2xl border-t border-gray-700"
        style={{ animation: 'slideUp 0.25s ease-out' }}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <h2 className="text-base font-bold text-amber-600">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl leading-none w-10 h-10 flex items-center justify-center"
          >
            ×
          </button>
        </div>
        <div className="px-4 py-4 pb-8 overflow-y-auto max-h-[70vh]">
          {children}
        </div>
      </div>
    </>
  )
}
