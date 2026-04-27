import React, { useState } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'

type View = 'login' | 'register' | 'forgot' | 'reset'

function getInitialView(): View {
  const params = new URLSearchParams(window.location.search)
  return params.get('reset_token') ? 'reset' : 'login'
}

function getTokenFromUrl(): string {
  const params = new URLSearchParams(window.location.search)
  return params.get('reset_token') ?? ''
}

export default function LoginPage() {
  const { login, register } = useAuth()
  const { t } = useLanguage()

  const [view, setView] = useState<View>(getInitialView)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [resetToken, setResetToken] = useState(getTokenFromUrl)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [resetUrl, setResetUrl] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const goTo = (v: View) => { setView(v); setError(null); setSuccess(null) }

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (view === 'register' && password !== confirmPassword) {
      setError(t('passwordMismatch'))
      return
    }
    if (password.length < 6) {
      setError(t('passwordTooShort'))
      return
    }
    setSubmitting(true)
    try {
      if (view === 'login') await login(email.trim(), password)
      else await register(email.trim(), password)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? t('authError'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleForgotSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setResetUrl(null)
    setSubmitting(true)
    try {
      const res = await axios.post<{ message: string; reset_url?: string; not_found?: boolean }>(
        '/api/auth/forgot-password',
        { email: email.trim() }
      )
      if (res.data.not_found) {
        setError(res.data.message)
      } else {
        setSuccess(res.data.message)
        if (res.data.reset_url) setResetUrl(res.data.reset_url)
      }
    } catch {
      setError(t('authError'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password !== confirmPassword) { setError(t('passwordMismatch')); return }
    if (password.length < 6) { setError(t('passwordTooShort')); return }
    setSubmitting(true)
    try {
      await axios.post('/api/auth/reset-password', { token: resetToken, password })
      setSuccess(t('passwordUpdated'))
      // Clear token from URL without reload
      window.history.replaceState({}, '', '/')
      setTimeout(() => goTo('login'), 2000)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? t('authError'))
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

        <div className="bg-gray-800 rounded-2xl border border-gray-700 p-6 shadow-xl">

          {/* ── LOGIN / REGISTER ── */}
          {(view === 'login' || view === 'register') && (
            <>
              <div className="flex rounded-lg overflow-hidden border border-gray-700 mb-6">
                <button type="button" onClick={() => goTo('login')}
                  className={`flex-1 py-2 text-sm font-semibold transition-colors ${view === 'login' ? 'bg-amber-700 text-white' : 'bg-gray-700 text-gray-400 hover:text-white'}`}>
                  {t('login')}
                </button>
                <button type="button" onClick={() => goTo('register')}
                  className={`flex-1 py-2 text-sm font-semibold transition-colors ${view === 'register' ? 'bg-amber-700 text-white' : 'bg-gray-700 text-gray-400 hover:text-white'}`}>
                  {t('register')}
                </button>
              </div>

              <form onSubmit={handleAuthSubmit} className="flex flex-col gap-4">
                <div>
                  <label className="block text-sm text-gray-300 mb-1">{t('email')}</label>
                  <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                    placeholder="vous@exemple.com"
                    className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:border-amber-500 focus:outline-none" />
                </div>
                <div>
                  <label className="block text-sm text-gray-300 mb-1">{t('password')}</label>
                  <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:border-amber-500 focus:outline-none" />
                </div>
                {view === 'register' && (
                  <div>
                    <label className="block text-sm text-gray-300 mb-1">{t('confirmPassword')}</label>
                    <input type="password" required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:border-amber-500 focus:outline-none" />
                  </div>
                )}

                {error && <p className="text-red-400 text-sm bg-red-900/30 border border-red-700/50 rounded-lg px-3 py-2">{error}</p>}

                <button type="submit" disabled={submitting}
                  className="w-full bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm">
                  {submitting ? t('loading') : view === 'login' ? t('loginBtn') : t('registerBtn')}
                </button>

                {view === 'login' && (
                  <button type="button" onClick={() => goTo('forgot')}
                    className="text-center text-xs text-gray-400 hover:text-amber-400 transition-colors">
                    {t('forgotPassword')}
                  </button>
                )}
              </form>
            </>
          )}

          {/* ── FORGOT PASSWORD ── */}
          {view === 'forgot' && (
            <>
              <h2 className="text-white font-semibold mb-1">{t('forgotPassword')}</h2>
              <p className="text-gray-400 text-sm mb-4">{t('forgotPasswordDesc')}</p>

              {success ? (
                <div className="flex flex-col gap-3">
                  <div className="bg-green-900/40 border border-green-700/50 rounded-lg px-3 py-3 text-green-300 text-sm">
                    {success}
                  </div>
                  {resetUrl && (
                    <div className="bg-amber-900/40 border border-amber-700/50 rounded-lg px-3 py-3">
                      <p className="text-amber-300 text-xs font-semibold mb-2">Lien de réinitialisation (email non envoyé) :</p>
                      <a href={resetUrl} className="text-amber-400 text-xs break-all underline hover:text-amber-300">
                        {resetUrl}
                      </a>
                    </div>
                  )}
                </div>
              ) : (
                <form onSubmit={handleForgotSubmit} className="flex flex-col gap-4">
                  <div>
                    <label className="block text-sm text-gray-300 mb-1">{t('email')}</label>
                    <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                      placeholder="vous@exemple.com"
                      className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:border-amber-500 focus:outline-none" />
                  </div>
                  {error && <p className="text-red-400 text-sm bg-red-900/30 border border-red-700/50 rounded-lg px-3 py-2">{error}</p>}
                  <button type="submit" disabled={submitting}
                    className="w-full bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm">
                    {submitting ? t('loading') : t('sendResetLink')}
                  </button>
                </form>
              )}

              <button type="button" onClick={() => goTo('login')}
                className="mt-4 text-xs text-gray-400 hover:text-amber-400 transition-colors">
                ← {t('backToLogin')}
              </button>
            </>
          )}

          {/* ── RESET PASSWORD ── */}
          {view === 'reset' && (
            <>
              <h2 className="text-white font-semibold mb-1">{t('newPassword')}</h2>
              <p className="text-gray-400 text-sm mb-4">{t('newPasswordDesc')}</p>

              {success ? (
                <div className="bg-green-900/40 border border-green-700/50 rounded-lg px-3 py-3 text-green-300 text-sm">
                  {success}
                </div>
              ) : (
                <form onSubmit={handleResetSubmit} className="flex flex-col gap-4">
                  <div>
                    <label className="block text-sm text-gray-300 mb-1">{t('password')}</label>
                    <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:border-amber-500 focus:outline-none" />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-300 mb-1">{t('confirmPassword')}</label>
                    <input type="password" required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:border-amber-500 focus:outline-none" />
                  </div>
                  {error && <p className="text-red-400 text-sm bg-red-900/30 border border-red-700/50 rounded-lg px-3 py-2">{error}</p>}
                  <button type="submit" disabled={submitting}
                    className="w-full bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm">
                    {submitting ? t('loading') : t('updatePassword')}
                  </button>
                </form>
              )}
            </>
          )}

        </div>
      </div>
    </div>
  )
}
