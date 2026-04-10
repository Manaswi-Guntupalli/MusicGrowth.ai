import { useState } from 'react'
import { motion } from 'framer-motion'
import { requestJson } from '../lib/apiClient'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'

const HERO_PILLS = ['Sound DNA', 'Difference Intelligence', 'Strategic Paths']

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
          <Button variant="primary" onClick={onToggleTheme}>
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </Button>
        </div>

        <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-start">
          <Card variant="level2" className="relative overflow-hidden min-h-[360px] p-8 md:min-h-[430px] md:p-12">
            <div className="absolute -top-24 -right-20 h-56 w-56 rounded-full bg-primary/20 blur-3xl" />
            <div className="absolute -bottom-24 -left-20 h-56 w-56 rounded-full bg-accent/20 blur-3xl" />
            <div className="relative flex h-full flex-col justify-between gap-10">
              <div className="space-y-6">
                <h1 className="max-w-[18ch] text-[36px] font-semibold leading-[1.04] tracking-[-0.02em] text-primary sm:text-[42px] md:text-[48px]">
                  MusicGrowth.AI
                </h1>
                <p className="max-w-[54ch] text-[17px] leading-relaxed text-text-primary sm:text-[20px] md:text-[22px] md:leading-[1.55]">
                  Discover where your music sits in the market, what makes it unique, and which path can
                  grow your audience with intention.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                {HERO_PILLS.map((pill) => (
                  <div
                    key={pill}
                    className="flex h-12 items-center rounded-badge border border-border-subtle bg-bg-surface px-4 text-[14px] font-medium tracking-[0.01em] text-text-secondary sm:text-[15px]"
                  >
                    {pill}
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <Card className="space-y-10 min-h-[340px] p-8 md:min-h-[400px] md:p-10">
            <div className="h-14 grid grid-cols-2 rounded-button border border-border-subtle bg-bg-elevated p-1">
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
