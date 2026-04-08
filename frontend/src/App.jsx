import { useEffect, useState } from 'react'
import LandingPage from './pages/LandingPage'
import Dashboard from './pages/Dashboard'
import { requestJson } from './lib/apiClient'

const TOKEN_KEY = 'musicgrowth_token'
const THEME_KEY = 'musicgrowth_theme'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || '')
  const [user, setUser] = useState(null)
  const [theme, setTheme] = useState(localStorage.getItem(THEME_KEY) || 'dark')
  const [bootstrapping, setBootstrapping] = useState(true)

  useEffect(() => {
    document.body.setAttribute('data-theme', theme)
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  useEffect(() => {
    let cancelled = false

    async function bootstrapSession() {
      if (!token) {
        if (!cancelled) {
          setUser(null)
          setBootstrapping(false)
        }
        return
      }

      await fetchMe(token)
      if (!cancelled) {
        setBootstrapping(false)
      }
    }

    setBootstrapping(true)
    bootstrapSession()

    return () => {
      cancelled = true
    }
  }, [token])

  async function fetchMe(accessToken) {
    try {
      const me = await requestJson('/auth/me', {
        token: accessToken,
        timeoutMs: 10000,
        retries: 1,
      })
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

  if (bootstrapping) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6" role="status" aria-live="polite" aria-busy="true">
        <div className="skeleton-blob w-full max-w-md p-8">
          <div className="skeleton-line mb-3 h-6 w-44"></div>
          <div className="skeleton-line h-4 w-64"></div>
        </div>
      </div>
    )
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
