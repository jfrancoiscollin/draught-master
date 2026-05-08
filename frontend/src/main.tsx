import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { LanguageProvider } from './i18n/LanguageContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import LoginPage from './components/LoginPage.tsx'

function Root() {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="spinner" style={{ width: 32, height: 32 }} />
      </div>
    )
  }
  if (!user) return <LoginPage />
  return <App />
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <LanguageProvider>
      <AuthProvider>
        <Root />
      </AuthProvider>
    </LanguageProvider>
  </React.StrictMode>,
)
