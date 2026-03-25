import { useEffect, useMemo, useState } from 'react'

const API_BASE = 'http://127.0.0.1:8000/api'

const TOKEN_KEY = 'musicgrowth_token'

const featureOrder = [
  'tempo',
  'energy',
  'danceability',
  'valence',
  'acousticness',
  'instrumentalness',
  'speechiness',
  'loudness',
  'liveness',
]

function meter(name, value) {
  const normalized = name === 'tempo' ? value / 200 : value
  const width = Math.max(0, Math.min(100, normalized * 100))
  return `${width}%`
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || '')
  const [user, setUser] = useState(null)
  const [authMode, setAuthMode] = useState('login')
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [file, setFile] = useState(null)
  const [segmentMode, setSegmentMode] = useState('best')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '' })

  useEffect(() => {
    if (!token) return
    fetchMe(token)
    fetchHistory(token)
  }, [token])

  const sortedFeatures = useMemo(() => {
    if (!result?.sound_dna) return []
    return featureOrder.map((name) => ({ name, value: result.sound_dna[name] }))
  }, [result])

  async function authedFetch(path, options = {}) {
    return fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: `Bearer ${token}`,
      },
    })
  }

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

  async function fetchHistory(accessToken = token) {
    if (!accessToken) return
    const res = await fetch(`${API_BASE}/analyses`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    if (res.ok) {
      setHistory(await res.json())
    }
  }

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

      localStorage.setItem(TOKEN_KEY, body.access_token)
      setToken(body.access_token)
      setUser(body.user)
      setAuthForm({ name: '', email: '', password: '' })
      await fetchHistory(body.access_token)
    } catch (err) {
      setAuthError(err.message || 'Authentication failed')
    } finally {
      setAuthLoading(false)
    }
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    setToken('')
    setUser(null)
    setResult(null)
    setHistory([])
  }

  async function handleAnalyze(e) {
    e.preventDefault()
    if (!file) {
      setError('Please upload an audio file first.')
      return
    }

    setLoading(true)
    setError('')

    const form = new FormData()
    form.append('file', file)

    try {
      const res = await authedFetch(`/analyze?segment_mode=${segmentMode}`, {
        method: 'POST',
        body: form,
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || 'Analysis failed')
      }

      const data = await res.json()
      setResult(data)
      await fetchHistory()
    } catch (err) {
      setError(err.message || 'Could not analyze this file.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  if (!token || !user) {
    return (
      <div className="landing-page">
        <section className="hero-landing">
          <h1>MusicGrowth.ai</h1>
          <p>
            Discover where your music sits in the market, what makes it unique, and which path can
            grow your audience with intention.
          </p>
          <div className="hero-badges">
            <span>Sound DNA</span>
            <span>Difference Intelligence</span>
            <span>Strategic Paths</span>
          </div>
        </section>

        <section className="auth-card">
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
              />
            )}
            <input
              type="email"
              placeholder="Email"
              value={authForm.email}
              onChange={(e) => setAuthForm((p) => ({ ...p, email: e.target.value }))}
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={authForm.password}
              onChange={(e) => setAuthForm((p) => ({ ...p, password: e.target.value }))}
              required
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

  return (
    <div className="page">
      <header className="hero">
        <div className="hero-glow" />
        <h1>MusicGrowth Dashboard</h1>
        <p>
          Welcome {user.name}. Upload songs, compare your Sound DNA, and track saved analysis runs.
        </p>
        <button className="logout-btn" onClick={logout}>Logout</button>
      </header>

      <section className="card upload-card">
        <h2>Upload And Analyze</h2>
        <form onSubmit={handleAnalyze} className="upload-form">
          <label className="file-input pretty-file">
            <span className="file-chip">Choose File</span>
            <span className="file-name">{file ? file.name : 'No file selected'}</span>
            <input
              type="file"
              accept=".mp3,.wav,.m4a,.flac,.ogg"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>

          <div className="toggle-row">
            <label>
              <input
                type="radio"
                name="segment"
                value="best"
                checked={segmentMode === 'best'}
                onChange={(e) => setSegmentMode(e.target.value)}
              />
              Best 30s Segment
            </label>
            <label>
              <input
                type="radio"
                name="segment"
                value="full"
                checked={segmentMode === 'full'}
                onChange={(e) => setSegmentMode(e.target.value)}
              />
              Full Audio
            </label>
          </div>

          <button disabled={loading}>{loading ? 'Analyzing...' : 'Analyze Song'}</button>
        </form>
        {error && <p className="error">{error}</p>}
      </section>

      <section className="card">
        <h3>Saved Analyses</h3>
        <div className="list">
          {history.length === 0 && <p className="sub">No saved analyses yet.</p>}
          {history.map((h) => (
            <article key={h.id} className="list-item">
              <h4>{h.filename}</h4>
              <p>{new Date(h.created_at).toLocaleString()} | {h.segment_mode}</p>
              <p>{h.mood} | {h.production_style}</p>
            </article>
          ))}
        </div>
      </section>

      {result && (
        <main className="grid">
          <section className="card">
            <h3>ML Style Cluster</h3>
            <p className="sub">
              Predicted Group: <strong>{result.style_cluster.label}</strong>
            </p>
            <p>
              Cluster ID: <strong>{result.style_cluster.cluster_id}</strong>
            </p>
            <p>
              Confidence: <strong>{Number(result.style_cluster.confidence).toFixed(2)}%</strong>
            </p>
          </section>

          <section className="card">
            <h3>Sound DNA</h3>
            <p className="sub">
              Mood: <strong>{result.sound_dna.mood}</strong> | Production Style:{' '}
              <strong>{result.sound_dna.production_style}</strong>
            </p>
            <div className="meter-list">
              {sortedFeatures.map((f) => (
                <div key={f.name} className="meter-item">
                  <div className="meter-head">
                    <span>{f.name}</span>
                    <span>{Number(f.value).toFixed(3)}</span>
                  </div>
                  <div className="meter-bg">
                    <div className="meter-fill" style={{ width: meter(f.name, Number(f.value)) }} />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="card">
            <h3>Top Similar References</h3>
            <div className="list">
              {result.top_similar.map((item) => (
                <article key={`${item.artist}-${item.song}`} className="list-item">
                  <h4>{item.artist} - {item.song}</h4>
                  <p>{item.cluster}</p>
                  <strong>{item.similarity.toFixed(2)}% similar</strong>
                </article>
              ))}
            </div>
          </section>

          <section className="card">
            <h3>Difference Intelligence</h3>
            <div className="list">
              {result.differences.map((d) => (
                <article key={d.feature} className="list-item">
                  <h4>{d.feature}</h4>
                  <p>
                    Song {d.song_value.toFixed(3)} vs Ref {d.reference_mean.toFixed(3)} ({d.delta_percent.toFixed(1)}%)
                  </p>
                  <p>{d.interpretation}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="card">
            <h3>Market Gaps</h3>
            <ul className="bullets">
              {result.market_gaps.map((gap) => (
                <li key={gap}>{gap}</li>
              ))}
            </ul>
          </section>

          <section className="card full-width">
            <h3>Strategic Paths</h3>
            <div className="paths">
              {result.paths.map((path) => (
                <article key={path.id} className="path-card">
                  <span className="pill">Path {path.id}</span>
                  <h4>{path.title}</h4>
                  <p><strong>Strategy:</strong> {path.strategy}</p>
                  <p><strong>Expected:</strong> {path.expected}</p>
                  <p><strong>Tradeoff:</strong> {path.tradeoff}</p>
                  <ul className="bullets">
                    {path.actions.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          </section>
        </main>
      )}
    </div>
  )
}
