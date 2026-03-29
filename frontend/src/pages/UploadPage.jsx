import { useState } from 'react'

const API_BASE = '/api'

export default function UploadPage({ token, onAnalysisComplete }) {
  const [file, setFile] = useState(null)
  const [segmentMode, setSegmentMode] = useState('best')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

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
      console.log(`Sending analyze request to ${API_BASE}/analyze?segment_mode=${segmentMode}`)
      const res = await fetch(`${API_BASE}/analyze?segment_mode=${segmentMode}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })

      console.log('Analyze response status:', res.status)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        console.error('Analyze error response:', body)
        throw new Error(body.detail || 'Analysis failed')
      }

      const data = await res.json()
      console.log('Analyze success response:', data)
      onAnalysisComplete(data)
    } catch (err) {
      console.error('Analyze error:', err)
      const message = err?.message || 'Could not analyze this file.'
      if (/empty|silent|valid music audio|audio file appears empty/i.test(message)) {
        setError('Please upload a valid music audio file (not empty or silent).')
      } else {
        setError(message)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-content fade-in">
      <section className="upload-section">
        <div className="upload-header">
          <h2>Upload Your Track</h2>
          <p>Analyze your music and discover your unique sound signature</p>
        </div>

        <form onSubmit={handleAnalyze} className="upload-form">
          <div className="file-upload-zone">
            <label className="file-input-label">
              <div className="file-input-visual">
                <span className="upload-icon">🎵</span>
                <span className="upload-text">
                  {file ? file.name : 'Drag & drop or click to select'}
                </span>
              </div>
              <input
                type="file"
                accept=".mp3,.wav,.m4a,.flac,.ogg"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="hidden-input"
              />
            </label>
          </div>

          <div className="segment-options">
            <label className="segment-item">
              <input
                type="radio"
                name="segment"
                value="best"
                checked={segmentMode === 'best'}
                onChange={(e) => setSegmentMode(e.target.value)}
              />
              <span className="segment-label">
                <span className="segment-title">Best 30s Segment</span>
                <span className="segment-desc">Analyzes the most energetic part</span>
              </span>
            </label>
            <label className="segment-item">
              <input
                type="radio"
                name="segment"
                value="full"
                checked={segmentMode === 'full'}
                onChange={(e) => setSegmentMode(e.target.value)}
              />
              <span className="segment-label">
                <span className="segment-title">Full Audio</span>
                <span className="segment-desc">Analyzes the entire track</span>
              </span>
            </label>
          </div>

          <button 
            type="submit" 
            disabled={loading || !file}
            className="analyze-btn"
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Analyzing your sound...
              </>
            ) : (
              <>
                <span className="btn-icon">🚀</span>
                Analyze My Sound
              </>
            )}
          </button>

          {error && <div className="error-message">{error}</div>}
        </form>
      </section>

      <section className="info-section">
        <div className="info-grid">
          <div className="info-card">
            <span className="info-icon">🎨</span>
            <h3>Sound DNA</h3>
            <p>Get a 14-dimensional analysis of your sound profile</p>
          </div>
          <div className="info-card">
            <span className="info-icon">🔍</span>
            <h3>Comparisons</h3>
            <p>See how you compare to similar artists</p>
          </div>
          <div className="info-card">
            <span className="info-icon">🧭</span>
            <h3>Strategic Paths</h3>
            <p>Discover growth opportunities for your music</p>
          </div>
        </div>
      </section>
    </div>
  )
}
