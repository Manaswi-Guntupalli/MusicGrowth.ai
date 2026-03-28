import { useState, useEffect } from 'react'
import UploadPage from './UploadPage'
import AnalysisPage from './AnalysisPage'
import HistoryPage from './HistoryPage'
import HistoryDetailPage from './HistoryDetailPage'

const API_BASE = '/api'

export default function Dashboard({ user, token, onLogout, theme, onToggleTheme }) {
  const [currentPage, setCurrentPage] = useState('upload')
  const [latestResult, setLatestResult] = useState(null)
  const [history, setHistory] = useState([])
  const [historyError, setHistoryError] = useState('')
  const [selectedHistoryAnalysis, setSelectedHistoryAnalysis] = useState(null)

  useEffect(() => {
    fetchHistory()
  }, [])

  useEffect(() => {
    if (currentPage === 'history') {
      fetchHistory()
    }
  }, [currentPage])

  async function fetchHistory() {
    try {
      setHistoryError('')
      const res = await fetch(`${API_BASE}/analyses`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setHistory(data)
      } else {
        const body = await res.json().catch(() => ({}))
        setHistoryError(body.detail || 'Failed to load history.')
      }
    } catch (err) {
      console.error('Error fetching history:', err)
      setHistoryError('Failed to load history. Please try again.')
    }
  }

  function handleAnalysisComplete(analysisResult) {
    console.log('Analysis result received:', analysisResult)
    if (!analysisResult || !analysisResult.sound_dna) {
      console.error('Invalid analysis result structure:', analysisResult)
      return
    }
    setLatestResult(analysisResult)
    setSelectedHistoryAnalysis(null)
    setCurrentPage('analysis')
    fetchHistory()
  }

  function handleViewAnalysis(analysis) {
    if (!analysis || !analysis.result) return
    setSelectedHistoryAnalysis(analysis)
    setCurrentPage('history-detail')
  }

  function handleBackToHistory() {
    setCurrentPage('history')
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-left">
          <h1 className="logo">🎵 MusicGrowth</h1>
          <p className="tagline">Find your sound. Choose your path.</p>
        </div>
        <div className="header-right">
          <button className="theme-toggle" onClick={onToggleTheme}>
            {theme === 'dark' ? '☀ Light Mode' : '🌙 Dark Mode'}
          </button>
          <span className="user-name">Welcome, {user.name}</span>
          <button className="logout-btn" onClick={onLogout}>Logout</button>
        </div>
      </header>

      <div className="dashboard-container">
        <aside className="sidebar">
          <nav className="nav-menu">
            <button
              className={`nav-item ${currentPage === 'upload' ? 'active' : ''}`}
              onClick={() => setCurrentPage('upload')}
            >
              <span className="nav-icon">📤</span>
              <span className="nav-text">Upload</span>
            </button>
            {latestResult && (
              <button
                className={`nav-item ${currentPage === 'analysis' ? 'active' : ''}`}
                onClick={() => setCurrentPage('analysis')}
              >
                <span className="nav-icon">📊</span>
                <span className="nav-text">Analysis</span>
              </button>
            )}
            <button
              className={`nav-item ${currentPage === 'history' || currentPage === 'history-detail' ? 'active' : ''}`}
              onClick={() => setCurrentPage('history')}
            >
              <span className="nav-icon">📜</span>
              <span className="nav-text">History</span>
              {history.length > 0 && <span className="badge">{history.length}</span>}
            </button>
          </nav>
        </aside>

        <main className="dashboard-content">
          {currentPage === 'upload' && (
            <UploadPage token={token} onAnalysisComplete={handleAnalysisComplete} />
          )}
          {currentPage === 'analysis' && latestResult && (
            <AnalysisPage result={latestResult} theme={theme} />
          )}
          {currentPage === 'history' && (
            <HistoryPage
              history={history}
              onViewAnalysis={handleViewAnalysis}
              error={historyError}
              onRetry={fetchHistory}
            />
          )}
          {currentPage === 'history-detail' && selectedHistoryAnalysis && (
            <HistoryDetailPage analysis={selectedHistoryAnalysis} onBack={handleBackToHistory} theme={theme} />
          )}
        </main>
      </div>
    </div>
  )
}
