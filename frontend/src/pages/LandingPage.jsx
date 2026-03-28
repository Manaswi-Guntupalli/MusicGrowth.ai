import { useState } from 'react'

const API_BASE = '/api'

export default function LandingPage({ onLogin, theme, onToggleTheme }) {
  const [authMode, setAuthMode] = useState('login')
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '' })

  async function handleAuth(e) {
    e.preventDefault()
    setAuthError('')
    setAuthLoading(true)
    try {
      const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register'
      const payload =
        authMode === 'login'
          ? { email: authForm.email, password: authForm.password }
          : { name: authForm.name, email: authForm.email, password: authForm.password }

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.detail || 'Authentication failed')

      onLogin(body.access_token, body.user)
      setAuthForm({ name: '', email: '', password: '' })
    } catch (err) {
      setAuthError(err.message || 'Authentication failed')
    } finally {
      setAuthLoading(false)
    }
  }

  return (
    <div className="landing-page">
      <button className="theme-toggle landing-theme-toggle" onClick={onToggleTheme}>
        {theme === 'dark' ? '☀ Light Mode' : '🌙 Dark Mode'}
      </button>
      <section className="hero-landing">
        <div className="hero-content-fade" />
        <h1 className="fade-in">MusicGrowth.ai</h1>
        <p className="fade-in delay-1">
          Discover where your music sits in the market, what makes it unique, and which path can
          grow your audience with intention.
        </p>
        <div className="hero-badges fade-in delay-2">
          <span className="badge-item">🎵 Sound DNA</span>
          <span className="badge-item">🔍 Difference Intelligence</span>
          <span className="badge-item">🧭 Strategic Paths</span>
        </div>
      </section>

      <section className="auth-card slide-up">
        <div className="auth-tabs">
          <button
            className={authMode === 'login' ? 'tab active' : 'tab'}
            onClick={() => setAuthMode('login')}
          >
            Login
          </button>
          <button
            className={authMode === 'register' ? 'tab active' : 'tab'}
            onClick={() => setAuthMode('register')}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleAuth} className="auth-form">
          {authMode === 'register' && (
            <input
              placeholder="Your Name"
              value={authForm.name}
              onChange={(e) => setAuthForm((p) => ({ ...p, name: e.target.value }))}
              required
              className="form-input"
            />
          )}
          <input
            type="email"
            placeholder="Email"
            value={authForm.email}
            onChange={(e) => setAuthForm((p) => ({ ...p, email: e.target.value }))}
            required
            className="form-input"
          />
          <input
            type="password"
            placeholder="Password"
            value={authForm.password}
            onChange={(e) => setAuthForm((p) => ({ ...p, password: e.target.value }))}
            required
            className="form-input"
          />
          <button className="auth-submit" disabled={authLoading}>
            {authLoading ? 'Please wait...' : authMode === 'login' ? 'Enter Dashboard' : 'Create Account'}
          </button>
          {authError && <p className="error">{authError}</p>}
        </form>
      </section>
    </div>
  )
}
