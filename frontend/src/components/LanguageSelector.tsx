import React, { useState, useRef, useEffect } from 'react'
import { useLanguage } from '../i18n/LanguageContext'
import type { Language } from '../i18n/translations'

const LANGUAGES: { code: Language; flag: string; label: string }[] = [
  { code: 'fr', flag: '🇫🇷', label: 'Français' },
  { code: 'en', flag: '🇬🇧', label: 'English' },
]

export default function LanguageSelector() {
  const { language, setLanguage } = useLanguage()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const current = LANGUAGES.find(l => l.code === language) ?? LANGUAGES[0]

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-semibold bg-gray-700 hover:bg-gray-600 text-gray-200 transition-colors"
        title="Changer de langue"
      >
        <span>{current.flag}</span>
        <span className="hidden sm:inline">{current.code.toUpperCase()}</span>
        <span className="text-gray-400 text-[10px]">▾</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-xl overflow-hidden z-50 min-w-[130px]">
          {LANGUAGES.map(({ code, flag, label }) => (
            <button
              key={code}
              onClick={() => { setLanguage(code); setOpen(false) }}
              className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors border-0 cursor-pointer ${
                language === code
                  ? 'bg-amber-800 text-white font-semibold'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              <span>{flag}</span>
              <span>{label}</span>
              {language === code && <span className="ml-auto text-amber-400 text-xs">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
