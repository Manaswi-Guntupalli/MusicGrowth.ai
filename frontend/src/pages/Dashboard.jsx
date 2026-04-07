import { useState, useEffect } from 'react'
import UploadPage from './UploadPage'
import AnalysisPage from './AnalysisPage'
import HistoryPage from './HistoryPage'
import HistoryDetailPage from './HistoryDetailPage'
import AnalysisSkeleton from '../components/AnalysisSkeleton'
import { requestJson } from '../lib/apiClient'

export default function Dashboard({ user, token, onLogout, theme, onToggleTheme }) {
  const [currentPage, setCurrentPage] = useState('upload')
  const [latestResult, setLatestResult] = useState(null)
  const [history, setHistory] = useState([])
  const [historyError, setHistoryError] = useState('')
  const [historyLoading, setHistoryLoading] = useState(false)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [selectedHistoryAnalysis, setSelectedHistoryAnalysis] = useState(null)

  useEffect(() => {
    fetchHistory()
  }, [token])

  useEffect(() => {
    if (currentPage === 'history') {
      fetchHistory()
    }
  }, [currentPage])

  async function fetchHistory() {
    try {
      setHistoryError('')
      setHistoryLoading(true)
      const data = await requestJson('/analyses', {
        token,
        timeoutMs: 10000,
        retries: 1,
      })
      setHistory(Array.isArray(data) ? data : [])
    } catch (err) {
      setHistoryError(err?.message || 'Failed to load history. Please try again.')
    } finally {
      setHistoryLoading(false)
    }
  }

  function handleAnalysisComplete(analysisResult) {
    if (!analysisResult || !analysisResult.sound_dna) {
      setAnalysisLoading(false)
      return
    }
    setLatestResult(analysisResult)
    setSelectedHistoryAnalysis(null)
    setCurrentPage('analysis')
    fetchHistory()
  }

  function handleAnalysisStateChange(isLoading) {
    setAnalysisLoading(Boolean(isLoading))
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
          <h1 className="logo">🎵 MusicGrowth.AI</h1>
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
            <>
              <div style={{ display: analysisLoading ? 'none' : 'block' }}>
                <UploadPage
                  token={token}
                  onAnalysisComplete={handleAnalysisComplete}
                  onAnalysisStateChange={handleAnalysisStateChange}
                />
              </div>
              {analysisLoading && <AnalysisSkeleton />}
            </>
          )}
          {currentPage === 'analysis' && analysisLoading && <AnalysisSkeleton />}
          {currentPage === 'analysis' && !analysisLoading && latestResult && (
            <AnalysisPage result={latestResult} theme={theme} token={token} />
          )}
          {currentPage === 'history' && (
            <HistoryPage
              history={history}
              onViewAnalysis={handleViewAnalysis}
              error={historyError}
              loading={historyLoading}
              onRetry={fetchHistory}
            />
          )}
          {currentPage === 'history-detail' && selectedHistoryAnalysis && (
            <HistoryDetailPage analysis={selectedHistoryAnalysis} onBack={handleBackToHistory} theme={theme} token={token} />
          )}
        </main>
      </div>
    </div>
  )
}
