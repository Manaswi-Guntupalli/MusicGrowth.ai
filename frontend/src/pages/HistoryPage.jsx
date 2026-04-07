export default function HistoryPage({ history, onViewAnalysis, error, onRetry, loading }) {
  return (
    <div className="page-content fade-in">
      <section className="history-header">
        <h2>Your Analysis History</h2>
        <p>View and compare all your previous analyses</p>
      </section>

      {error && (
        <div className="error-message" style={{ marginBottom: '16px' }}>
          <p>{error}</p>
          <button className="history-view-btn" onClick={onRetry} style={{ marginTop: '10px' }}>
            Retry
          </button>
        </div>
      )}

      <div className="history-list" aria-busy={loading ? 'true' : 'false'}>
        {loading ? (
          <>
            {[1, 2, 3].map((idx) => (
              <div key={idx} className="history-item skeleton-blob" style={{ minHeight: '112px' }}>
                <div className="history-main" style={{ width: '100%' }}>
                  <div style={{ flex: 1 }}>
                    <div className="skeleton-line" style={{ width: '45%', marginBottom: '0.7rem' }}></div>
                    <div className="skeleton-line" style={{ width: '30%', marginBottom: '0.7rem' }}></div>
                    <div className="skeleton-line" style={{ width: '50%' }}></div>
                  </div>
                  <div style={{ width: '180px' }}>
                    <div className="skeleton-line" style={{ width: '100%', marginBottom: '0.7rem' }}></div>
                    <div className="skeleton-line" style={{ width: '70%' }}></div>
                  </div>
                </div>
              </div>
            ))}
          </>
        ) : history.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">📭</span>
            <p>No analyses yet. Upload your first song to get started!</p>
          </div>
        ) : (
          history.map((analysis) => (
            <div key={analysis.id} className="history-item slide-up">
              <div className="history-main">
                <div className="history-info">
                  <h3>{analysis.filename}</h3>
                  <p className="history-timestamp">
                    {new Date(analysis.created_at).toLocaleDateString()} at {
                      new Date(analysis.created_at).toLocaleTimeString()
                    }
                  </p>
                  <p className="history-mood">
                    <span className="badge-mini mood">{analysis.result?.sound_dna?.mood || 'Unknown'}</span>
                    <span className="badge-mini style">{analysis.result?.sound_dna?.production_style || 'Unknown'}</span>
                  </p>
                </div>
                <div className="history-cluster">
                  <p className="cluster-label">{analysis.result?.style_cluster?.label || 'Unknown Cluster'}</p>
                  <p className="cluster-conf">{analysis.result?.style_cluster?.confidence?.toFixed(1) || '?'}% confidence</p>
                </div>
                <button 
                  className="history-view-btn"
                  onClick={() => onViewAnalysis(analysis)}
                >
                  View Details →
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
