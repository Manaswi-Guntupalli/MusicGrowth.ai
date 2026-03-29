import AnalysisPage from './AnalysisPage'

export default function HistoryDetailPage({ analysis, onBack, theme, token }) {
  const createdAt = analysis?.created_at ? new Date(analysis.created_at) : null

  return (
    <div className="page-content fade-in">
      <section className="history-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
          <div>
            <h2>History Details</h2>
            <p>
              {analysis?.filename || 'Selected analysis'}
              {createdAt ? ` • ${createdAt.toLocaleDateString()} ${createdAt.toLocaleTimeString()}` : ''}
            </p>
          </div>
          <button className="history-view-btn" onClick={onBack}>
            ← Back to History
          </button>
        </div>
      </section>

      <AnalysisPage result={analysis?.result} theme={theme} token={token} />
    </div>
  )
}