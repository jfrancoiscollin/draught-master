import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'

export default function LoginPage() {
  const { login, register } = useAuth()
  const { t } = useLanguage()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (mode === 'register' && password !== confirmPassword) {
      setError(t('passwordMismatch'))
      return
    }
    if (password.length < 6) {
      setError(t('passwordTooShort'))
      return
    }

    setSubmitting(true)
    try {
      if (mode === 'login') {
        await login(email.trim(), password)
      } else {
        await register(email.trim(), password)
      }
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || t('authError'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <span className="text-5xl">♟</span>
          <h1 className="text-2xl font-bold text-amber-500 mt-2">AI-Draught</h1>
          <p className="text-gray-400 text-sm mt-1">{t('appSubtitle')}</p>
        </div>

        {/* Card */}
        <div className="bg-gray-800 rounded-2xl border border-gray-700 p-6 shadow-xl">
          {/* Tab toggle */}
          <div className="flex rounded-lg overflow-hidden border border-gray-700 mb-6">
            <button
              type="button"
              onClick={() => { setMode('login'); setError(null) }}
              className={`flex-1 py-2 text-sm font-semibold transition-colors ${
                mode === 'login'
                  ? 'bg-amber-700 text-white'
                  : 'bg-gray-700 text-gray-400 hover:text-white'
              }`}
            >
              {t('login')}
            </button>
            <button
              type="button"
              onClick={() => { setMode('register'); setError(null) }}
              className={`flex-1 py-2 text-sm font-semibold transition-colors ${
                mode === 'register'
                  ? 'bg-amber-700 text-white'
                  : 'bg-gray-700 text-gray-400 hover:text-white'
              }`}
            >
              {t('register')}
            </button>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="block text-sm text-gray-300 mb-1">{t('email')}</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="vous@exemple.com"
                className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:border-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-300 mb-1">{t('password')}</label>
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:border-amber-500 focus:outline-none"
              />
            </div>

            {mode === 'register' && (
              <div>
                <label className="block text-sm text-gray-300 mb-1">{t('confirmPassword')}</label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:border-amber-500 focus:outline-none"
                />
              </div>
            )}

            {error && (
              <p className="text-red-400 text-sm bg-red-900/30 border border-red-700/50 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-amber-700 hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg transition-colors text-sm"
            >
              {submitting
                ? t('loading')
                : mode === 'login'
                  ? t('loginBtn')
                  : t('registerBtn')}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
