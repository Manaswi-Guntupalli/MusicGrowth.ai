import { useState } from 'react'
import { requestJson } from '../lib/apiClient'

export default function UploadPage({ token, onAnalysisComplete, onAnalysisStateChange }) {
  const [file, setFile] = useState(null)
  const [segmentMode, setSegmentMode] = useState('best')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function toUploadErrorMessage(err) {
    const rawMessage = String(err?.message || '').trim()
    const status = Number(err?.status || 0)
    const code = String(err?.code || '')

    if (status === 413) {
      return 'File is too large. Please upload a track under 25 MB or increase the upload limit in settings.'
    }

    if (status === 415 || /unsupported file type|unsupported media format/i.test(rawMessage)) {
      return 'Unsupported format. Please upload MP3, WAV, FLAC, M4A, or OGG audio.'
    }

    if (status === 400 && /corrupted|could not be parsed|unsupported/i.test(rawMessage)) {
      return 'The file could not be decoded. Re-export it as MP3 or WAV and try again.'
    }

    if (/empty|silent|valid music audio|audio file appears empty/i.test(rawMessage)) {
      return 'Please upload a valid music audio file that contains audible content.'
    }

    if (code === 'TIMEOUT') {
      return 'Upload timed out. Check your connection and try a smaller file.'
    }

    if (code === 'NETWORK_ERROR') {
      return 'Network issue detected. Verify internet/backend connection and try again.'
    }

    return rawMessage || 'Could not analyze this file. Please try again.'
  }

  async function handleAnalyze(e) {
    e.preventDefault()
    if (!file) {
      setError('Please upload an audio file first.')
      return
    }

    setLoading(true)
    setError('')
    onAnalysisStateChange?.(true)

    const form = new FormData()
    form.append('file', file)

    try {
      const data = await requestJson(`/analyze?segment_mode=${segmentMode}`, {
        method: 'POST',
        body: form,
        token,
        timeoutMs: 90000,
        retries: 0,
      })
      onAnalysisComplete(data)
    } catch (err) {
      setError(toUploadErrorMessage(err))
    } finally {
      setLoading(false)
      onAnalysisStateChange?.(false)
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
              <div className={`file-input-visual ${loading ? 'analyzing' : ''}`}>
                {loading && (
                  <div className="upload-note-cloud" aria-hidden="true">
                    <span className="upload-note n1">♪</span>
                    <span className="upload-note n2">♫</span>
                    <span className="upload-note n3">♪</span>
                    <span className="upload-note n4">♫</span>
                    <span className="upload-note n5">♪</span>
                    <span className="upload-note n6">♫</span>
                  </div>
                )}
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
