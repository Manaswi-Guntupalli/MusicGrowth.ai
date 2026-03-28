import { useEffect, useState } from 'react'
import LandingPage from './pages/LandingPage'
import Dashboard from './pages/Dashboard'

const API_BASE = '/api'
const TOKEN_KEY = 'musicgrowth_token'
const THEME_KEY = 'musicgrowth_theme'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || '')
  const [user, setUser] = useState(null)
  const [theme, setTheme] = useState(localStorage.getItem(THEME_KEY) || 'dark')

  useEffect(() => {
    document.body.setAttribute('data-theme', theme)
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  useEffect(() => {
    if (!token) return
    fetchMe(token)
  }, [token])

  async function fetchMe(accessToken) {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      if (!res.ok) throw new Error('Session expired')
      const me = await res.json()
      setUser(me)
    } catch {
      logout()
    }
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    setToken('')
    setUser(null)
  }

  function handleLogin(newToken, newUser) {
    localStorage.setItem(TOKEN_KEY, newToken)
    setToken(newToken)
    setUser(newUser)
  }

  function handleToggleTheme() {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  if (!token || !user) {
    return <LandingPage onLogin={handleLogin} theme={theme} onToggleTheme={handleToggleTheme} />
  }

  return (
    <Dashboard
      user={user}
      token={token}
      onLogout={logout}
      theme={theme}
      onToggleTheme={handleToggleTheme}
    />
  )
}
