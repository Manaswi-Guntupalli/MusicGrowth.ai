import { useState } from 'react'
import { motion } from 'framer-motion'
import { requestJson } from '../lib/apiClient'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { typographyTokens } from '../theme/tokens'

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

      const body = await requestJson(endpoint, {
        method: 'POST',
        body: payload,
        timeoutMs: 12000,
        retries: 0,
      })

      onLogin(body.access_token, body.user)
      setAuthForm({ name: '', email: '', password: '' })
    } catch (err) {
      setAuthError(err?.message || 'Authentication failed')
    } finally {
      setAuthLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="min-h-screen relative px-4 py-8 md:px-8"
    >
      <div className="mx-auto w-full max-w-content">
        <div className="mb-6 flex justify-end">
          <Button variant="secondary" onClick={onToggleTheme}>
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </Button>
        </div>

        <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-start">
          <Card variant="level2" className="relative overflow-hidden">
            <div className="absolute -top-24 -right-20 h-56 w-56 rounded-full bg-primary/20 blur-3xl" />
            <div className="absolute -bottom-24 -left-20 h-56 w-56 rounded-full bg-accent/20 blur-3xl" />
            <div className="relative space-y-6">
              <p className="text-[12px] font-medium text-text-muted uppercase tracking-wider">Music analytics platform</p>
              <h1 className={typographyTokens.pageTitle}>MusicGrowth.AI</h1>
              <p className={typographyTokens.body}>
                Discover where your music sits in the market, what makes it unique, and which path can
                grow your audience with intention.
              </p>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="bg-bg-surface border border-border-subtle rounded-badge px-3 py-2 text-[13px] text-text-secondary">Sound DNA</div>
                <div className="bg-bg-surface border border-border-subtle rounded-badge px-3 py-2 text-[13px] text-text-secondary">Difference Intelligence</div>
                <div className="bg-bg-surface border border-border-subtle rounded-badge px-3 py-2 text-[13px] text-text-secondary">Strategic Paths</div>
              </div>
            </div>
          </Card>

          <Card className="space-y-5">
            <div className="h-12 grid grid-cols-2 rounded-button border border-border-subtle bg-bg-elevated p-1">
              <button
                className={authMode === 'login' ? 'rounded-button bg-primary/20 text-primary text-[14px] font-medium' : 'rounded-button text-text-muted text-[14px] hover:text-text-secondary'}
                onClick={() => setAuthMode('login')}
              >
                Login
              </button>
              <button
                className={authMode === 'register' ? 'rounded-button bg-primary/20 text-primary text-[14px] font-medium' : 'rounded-button text-text-muted text-[14px] hover:text-text-secondary'}
                onClick={() => setAuthMode('register')}
              >
                Register
              </button>
            </div>

            <form onSubmit={handleAuth} className="space-y-4">
              {authMode === 'register' && (
                <input
                  placeholder="Your Name"
                  value={authForm.name}
                  onChange={(e) => setAuthForm((p) => ({ ...p, name: e.target.value }))}
                  required
                  className="h-11 w-full rounded-button border border-border-default bg-bg-elevated px-3 text-[14px] text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
                />
              )}
              <input
                type="email"
                placeholder="Email"
                value={authForm.email}
                onChange={(e) => setAuthForm((p) => ({ ...p, email: e.target.value }))}
                required
                className="h-11 w-full rounded-button border border-border-default bg-bg-elevated px-3 text-[14px] text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
              />
              <input
                type="password"
                placeholder="Password"
                value={authForm.password}
                onChange={(e) => setAuthForm((p) => ({ ...p, password: e.target.value }))}
                required
                className="h-11 w-full rounded-button border border-border-default bg-bg-elevated px-3 text-[14px] text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
              />
              <Button type="submit" variant="primary" className="w-full" disabled={authLoading}>
                {authLoading ? 'Please wait...' : authMode === 'login' ? 'Enter Dashboard' : 'Create Account'}
              </Button>
              {authError ? <p className="text-[13px] text-danger">{authError}</p> : null}
            </form>
          </Card>
        </div>
      </div>
    </motion.div>
  )
}
