import React, { useEffect } from 'react'

interface ToastProps {
  message: string
  onClose: () => void
  duration?: number
}

export default function Toast({ message, onClose, duration = 4000 }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, duration)
    return () => clearTimeout(timer)
  }, [onClose, duration])

  return (
    <div className="toast" onClick={onClose}>
      <div className="flex items-center gap-2">
        <span className="text-red-300">⚠</span>
        <span>{message}</span>
        <button className="ml-2 text-gray-300 hover:text-white" onClick={onClose}>
          ✕
        </button>
      </div>
    </div>
  )
}
