import React from 'react'
import { useLanguage } from '../i18n/LanguageContext'
import type { Language } from '../i18n/translations'

const LANGUAGES: { code: Language; flag: string; label: string }[] = [
  { code: 'fr', flag: '🇫🇷', label: 'FR' },
  { code: 'en', flag: '🇬🇧', label: 'EN' },
]

export default function LanguageSelector() {
  const { language, setLanguage } = useLanguage()

  return (
    <div className="flex items-center gap-1">
      {LANGUAGES.map(({ code, flag, label }) => (
        <button
          key={code}
          onClick={() => setLanguage(code)}
          className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold transition-colors ${
            language === code
              ? 'bg-green-600 text-white'
              : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'
          }`}
          title={label}
        >
          <span>{flag}</span>
          <span>{label}</span>
        </button>
      ))}
    </div>
  )
}
