import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
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
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={`flex h-screen overflow-hidden ${theme === 'dark' ? 'bg-[#0A0B14] text-white' : 'bg-[#F3F6FF] text-[#111827]'}`}
    >
      <aside className={`hidden w-[220px] flex-shrink-0 flex-col gap-2 px-4 py-6 md:flex ${theme === 'dark' ? 'border-r border-white/[0.07] bg-[#111827]' : 'border-r border-[#DCE3F2] bg-white'}`}>
        <div className="mb-6">
          <span className="text-[18px] font-semibold text-[#8B7CF6]">MusicGrowth.AI</span>
          <p className={`mt-0.5 text-[12px] ${theme === 'dark' ? 'text-[#5B6278]' : 'text-[#6B7280]'}`}>Find your sound. Choose your path.</p>
        </div>

        <button
          className={`flex h-12 w-full items-center gap-3 rounded-lg px-3 text-left text-[14px] transition-colors ${currentPage === 'upload' ? 'border-l-2 border-[#6C5CE7] bg-[#6C5CE7]/10 text-[#8B7CF6]' : theme === 'dark' ? 'border-l-2 border-transparent text-[#9CA3AF] hover:bg-white/5' : 'border-l-2 border-transparent text-[#6B7280] hover:bg-[#EEF2FF]'}`}
          onClick={() => setCurrentPage('upload')}
        >
          Upload
        </button>

        {latestResult ? (
          <button
            className={`flex h-12 w-full items-center gap-3 rounded-lg px-3 text-left text-[14px] transition-colors ${currentPage === 'analysis' ? 'border-l-2 border-[#6C5CE7] bg-[#6C5CE7]/10 text-[#8B7CF6]' : theme === 'dark' ? 'border-l-2 border-transparent text-[#9CA3AF] hover:bg-white/5' : 'border-l-2 border-transparent text-[#6B7280] hover:bg-[#EEF2FF]'}`}
            onClick={() => setCurrentPage('analysis')}
          >
            Analysis
          </button>
        ) : null}

        <button
          className={`flex h-12 w-full items-center gap-3 rounded-lg px-3 text-left text-[14px] transition-colors ${(currentPage === 'history' || currentPage === 'history-detail') ? 'border-l-2 border-[#6C5CE7] bg-[#6C5CE7]/10 text-[#8B7CF6]' : theme === 'dark' ? 'border-l-2 border-transparent text-[#9CA3AF] hover:bg-white/5' : 'border-l-2 border-transparent text-[#6B7280] hover:bg-[#EEF2FF]'}`}
          onClick={() => setCurrentPage('history')}
        >
          History
          {history.length > 0 ? (
            <span className={`ml-auto rounded-full px-2 py-0.5 text-[11px] ${theme === 'dark' ? 'bg-white/10 text-[#9CA3AF]' : 'bg-[#EEF2FF] text-[#4B5563]'}`}>{history.length}</span>
          ) : null}
        </button>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className={`flex h-[60px] flex-shrink-0 items-center justify-end gap-4 px-8 ${theme === 'dark' ? 'border-b border-white/[0.07] bg-[#111827]' : 'border-b border-[#DCE3F2] bg-white'}`}>
          <button
            className={`h-8 rounded-lg px-3 text-[13px] transition-colors ${theme === 'dark' ? 'border border-white/20 text-[#9CA3AF] hover:bg-white/5 hover:text-white' : 'border border-[#CBD5E1] text-[#4B5563] hover:bg-[#F3F4F6]'}`}
            onClick={onToggleTheme}
          >
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </button>
          <span className={`hidden text-[13px] sm:inline ${theme === 'dark' ? 'text-[#9CA3AF]' : 'text-[#4B5563]'}`}>{user.name}</span>
          <button
            className="h-8 rounded-lg border border-red-500/40 px-4 text-[13px] text-red-400 transition-colors hover:bg-red-500/10"
            onClick={onLogout}
          >
            Logout
          </button>
        </header>

        <main className="flex-1 overflow-y-auto px-10 py-10 pb-24 md:pb-10">
          <div className="max-w-[1200px] space-y-8">
            {currentPage === 'upload' ? (
              <>
                <div className={analysisLoading ? 'hidden' : 'block'}>
                  <UploadPage
                    token={token}
                    theme={theme}
                    onAnalysisComplete={handleAnalysisComplete}
                    onAnalysisStateChange={handleAnalysisStateChange}
                  />
                </div>
                {analysisLoading ? <AnalysisSkeleton /> : null}
              </>
            ) : null}

            {currentPage === 'analysis' && analysisLoading ? <AnalysisSkeleton /> : null}

            {currentPage === 'analysis' && !analysisLoading && latestResult ? (
              <AnalysisPage result={latestResult} theme={theme} token={token} />
            ) : null}

            {currentPage === 'history' ? (
              <HistoryPage
                history={history}
                onViewAnalysis={handleViewAnalysis}
                error={historyError}
                loading={historyLoading}
                onRetry={fetchHistory}
              />
            ) : null}

            {currentPage === 'history-detail' && selectedHistoryAnalysis ? (
              <HistoryDetailPage analysis={selectedHistoryAnalysis} onBack={handleBackToHistory} theme={theme} token={token} />
            ) : null}
          </div>
        </main>
      </div>

      <nav className={`fixed bottom-0 left-0 right-0 z-50 flex h-14 items-center justify-around border-t md:hidden ${theme === 'dark' ? 'border-white/[0.07] bg-[#111827]' : 'border-[#DCE3F2] bg-white'}`}>
        <button className={`flex flex-col items-center gap-1 px-4 text-[11px] transition-colors ${currentPage === 'upload' ? (theme === 'dark' ? 'text-white' : 'text-[#111827]') : (theme === 'dark' ? 'text-[#9CA3AF] hover:text-white' : 'text-[#6B7280] hover:text-[#111827]')}`} onClick={() => setCurrentPage('upload')}>
          Upload
        </button>
        <button className={`flex flex-col items-center gap-1 px-4 text-[11px] transition-colors ${currentPage === 'analysis' ? (theme === 'dark' ? 'text-white' : 'text-[#111827]') : (theme === 'dark' ? 'text-[#9CA3AF] hover:text-white' : 'text-[#6B7280] hover:text-[#111827]')}`} onClick={() => setCurrentPage('analysis')} disabled={!latestResult}>
          Analysis
        </button>
        <button className={`flex flex-col items-center gap-1 px-4 text-[11px] transition-colors ${(currentPage === 'history' || currentPage === 'history-detail') ? (theme === 'dark' ? 'text-white' : 'text-[#111827]') : (theme === 'dark' ? 'text-[#9CA3AF] hover:text-white' : 'text-[#6B7280] hover:text-[#111827]')}`} onClick={() => setCurrentPage('history')}>
          History
        </button>
      </nav>
    </motion.div>
  )
}
