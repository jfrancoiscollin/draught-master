import React, { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

export interface AuthUser {
  id: number
  email: string
  lidraughts_username?: string | null
  // Display username used by Live PvP. Auto-populated from email
  // local-part on first /me call post-migration; user can edit.
  username?: string | null
}

interface AuthContextType {
  user: AuthUser | null
  setUser: (u: AuthUser | null) => void
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, username: string) => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      setLoading(false)
      return
    }
    axios
      .get<AuthUser>('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then(res => setUser(res.data))
      .catch(() => localStorage.removeItem('auth_token'))
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const res = await axios.post<{ token: string; user: AuthUser }>('/api/auth/login', {
      email,
      password,
    })
    localStorage.setItem('auth_token', res.data.token)
    setUser(res.data.user)
  }

  const register = async (email: string, password: string, username: string) => {
    const res = await axios.post<{ token: string; user: AuthUser }>('/api/auth/register', {
      email,
      password,
      username,
    })
    localStorage.setItem('auth_token', res.data.token)
    setUser(res.data.user)
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, setUser, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}
