export default function AnalysisSkeleton() {
  return (
    <div className="page-content fade-in">
      {/* Header Skeleton */}
      <section className="analysis-header">
        <div className="cluster-badge skeleton-blob" style={{ height: '120px', marginBottom: '2rem' }}>
          <div className="skeleton-line" style={{ width: '60%', height: '2rem', marginBottom: '1rem' }}></div>
          <div className="skeleton-line" style={{ width: '100%', height: '8px', marginBottom: '0.5rem' }}></div>
          <div className="skeleton-line" style={{ width: '40%', height: '1rem' }}></div>
        </div>
      </section>

      {/* Tabs Skeleton */}
      <div className="tabs-container">
        <div className="tabs" style={{ gap: '1rem', marginBottom: '1rem' }}>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="skeleton-line" style={{ width: '100px', height: '2rem' }}></div>
          ))}
        </div>
      </div>

      {/* Sound DNA Section Skeleton */}
      <section className="tab-pane">
        <div style={{ marginBottom: '3rem' }}>
          <div className="skeleton-line" style={{ width: '30%', height: '1.5rem', marginBottom: '1rem' }}></div>
          
          {/* Mood/Style */}
          <div className="skeleton-line" style={{ width: '50%', height: '1rem', marginBottom: '2rem' }}></div>

          {/* Chart placeholder */}
          <div className="chart-container skeleton-blob" style={{ height: '350px', marginBottom: '2rem' }}></div>

          {/* Features Grid */}
          <div className="features-grid" style={{ marginTop: '2rem' }}>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
              <div key={i} className="feature-card skeleton-blob" style={{ height: '120px' }}></div>
            ))}
          </div>
        </div>
      </section>

      {/* Similar Items Skeleton */}
      <section className="tab-pane" style={{ marginTop: '2rem' }}>
        <div className="skeleton-line" style={{ width: '25%', height: '1.5rem', marginBottom: '1.5rem' }}></div>
        <div className="similar-list">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton-blob" style={{ height: '100px', marginBottom: '1rem' }}></div>
          ))}
        </div>
      </section>

      {/* Differences Skeleton */}
      <section className="tab-pane" style={{ marginTop: '2rem' }}>
        <div className="skeleton-line" style={{ width: '20%', height: '1.5rem', marginBottom: '1.5rem' }}></div>
        <div className="difference-details">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton-blob" style={{ height: '140px' }}></div>
          ))}
        </div>
      </section>

      {/* Paths Skeleton */}
      <section className="tab-pane" style={{ marginTop: '2rem' }}>
        <div className="skeleton-line" style={{ width: '25%', height: '1.5rem', marginBottom: '1.5rem' }}></div>
        <div className="paths-grid">
          {[1, 2].map((i) => (
            <div key={i} className="skeleton-blob" style={{ height: '220px' }}></div>
          ))}
        </div>
      </section>

      {/* Market Gaps Skeleton */}
      <section className="tab-pane" style={{ marginTop: '2rem' }}>
        <div className="skeleton-line" style={{ width: '25%', height: '1.5rem', marginBottom: '1.5rem' }}></div>
        <div className="gaps-list">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton-blob" style={{ height: '100px' }}></div>
          ))}
        </div>
      </section>
    </div>
  )
}
