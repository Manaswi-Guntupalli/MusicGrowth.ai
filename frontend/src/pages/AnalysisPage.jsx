import { useState } from 'react'
import { Chart as ChartJS, RadarController, BarController, CategoryScale, LinearScale, RadialLinearScale, PointElement, LineElement, BarElement, Filler, Tooltip, Legend } from 'chart.js'
import { Radar, Bar } from 'react-chartjs-2'
import { jsPDF } from 'jspdf'
import html2canvas from 'html2canvas'

const API_BASE = '/api'

const FEATURE_ORDER = [
  'tempo',
  'energy',
  'danceability',
  'valence',
  'acousticness',
  'instrumentalness',
  'liveness',
  'speechiness',
  'loudness',
  'mfcc_mean_1',
  'mfcc_mean_2',
  'mfcc_mean_3',
  'mfcc_mean_4',
  'mfcc_mean_5',
]

const SIMULATOR_CONTROLS = [
  { feature: 'tempo', label: 'Tempo', min: -20, max: 20, step: 1, unit: 'bpm' },
  { feature: 'energy', label: 'Energy', min: -0.2, max: 0.2, step: 0.01, unit: '' },
  { feature: 'danceability', label: 'Danceability', min: -0.2, max: 0.2, step: 0.01, unit: '' },
  { feature: 'valence', label: 'Valence', min: -0.2, max: 0.2, step: 0.01, unit: '' },
  { feature: 'acousticness', label: 'Acousticness', min: -0.2, max: 0.2, step: 0.01, unit: '' },
  { feature: 'instrumentalness', label: 'Instrumentalness', min: -0.2, max: 0.2, step: 0.01, unit: '' },
  { feature: 'liveness', label: 'Liveness', min: -0.2, max: 0.2, step: 0.01, unit: '' },
  { feature: 'speechiness', label: 'Speechiness', min: -0.2, max: 0.2, step: 0.01, unit: '' },
  { feature: 'loudness', label: 'Loudness', min: -6, max: 6, step: 0.5, unit: 'dB' },
]

ChartJS.register(
  RadarController,
  BarController,
  CategoryScale,
  LinearScale,
  RadialLinearScale,
  PointElement,
  LineElement,
  BarElement,
  Filler,
  Tooltip,
  Legend
)

export default function AnalysisPage({ result, theme = 'dark', token }) {
  const [activeTab, setActiveTab] = useState('dna')
  const [exporting, setExporting] = useState(false)
  const [simLoading, setSimLoading] = useState(false)
  const [optLoading, setOptLoading] = useState(false)
  const [optObjective, setOptObjective] = useState('similarity')
  const [simError, setSimError] = useState('')
  const [simResult, setSimResult] = useState(null)
  const [optResult, setOptResult] = useState(null)
  const [adjustments, setAdjustments] = useState(() => {
    const initial = {}
    for (const control of SIMULATOR_CONTROLS) {
      initial[control.feature] = 0
    }
    return initial
  })

  const chartTextColor = theme === 'light' ? '#3b4260' : '#e0e7ff'
  const chartTickColor = theme === 'light' ? '#63708f' : '#94a3b8'
  const chartGridColor = theme === 'light' ? 'rgba(99, 112, 143, 0.18)' : 'rgba(255, 255, 255, 0.1)'

  // Safety checks
  if (!result || !result.sound_dna || !result.style_cluster) {
    return (
      <div className="page-content">
        <div className="error-message">
          <p>⚠️ Error loading analysis. Please try again.</p>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      </div>
    )
  }

  const baseFeatures = FEATURE_ORDER.reduce((acc, name) => {
    acc[name] = Number(result.sound_dna?.[name] ?? 0)
    return acc
  }, {})

  async function exportToPDF() {
    if (exporting) return
    setExporting(true)

    try {
      const element = document.querySelector('.page-content')
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: theme === 'light' ? '#ffffff' : '#0f172a',
      })

      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF('p', 'mm', 'a4')
      const imgWidth = 210 - 20
      const pageHeight = 297
      let heightLeft = canvas.height * (imgWidth / canvas.width)
      let position = 0

      // Add title page
      pdf.setFillColor(111, 92, 255)
      pdf.rect(0, 0, 210, 60, 'F')
      pdf.setTextColor(255, 255, 255)
      pdf.setFontSize(28)
      pdf.text('MusicGrowth Analysis', 105, 30, { align: 'center' })
      
      pdf.setTextColor(100, 100, 100)
      pdf.setFontSize(12)
      pdf.text(`${result.style_cluster.label} - ${result.sound_dna.mood}`, 105, 50, { align: 'center' })

      // Add metadata
      pdf.setTextColor(80, 80, 80)
      pdf.setFontSize(10)
      const date = new Date().toLocaleDateString()
      pdf.text(`Generated: ${date}`, 10, 75)
      pdf.text(`Confidence: ${result.style_cluster.confidence.toFixed(1)}%`, 10, 85)

      // Add analysis content
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 10, 10, imgWidth, (imgWidth / canvas.width) * canvas.height)
      heightLeft -= pageHeight

      while (heightLeft >= 0) {
        position = heightLeft - canvas.height
        pdf.addPage()
        pdf.addImage(imgData, 'PNG', 10, position, imgWidth, (imgWidth / canvas.width) * canvas.height)
        heightLeft -= pageHeight
      }

      pdf.save(`MusicGrowth-Analysis-${result.style_cluster.label}.pdf`)
    } catch (err) {
      console.error('PDF export error:', err)
      alert('Failed to export PDF. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  function formatDelta(feature, value) {
    const control = SIMULATOR_CONTROLS.find((item) => item.feature === feature)
    const suffix = control?.unit ? ` ${control.unit}` : ''
    const rounded = Math.abs(value) < 1 ? value.toFixed(2) : value.toFixed(1)
    return `${value >= 0 ? '+' : ''}${rounded}${suffix}`
  }

  function updateAdjustment(feature, rawValue) {
    const parsed = Number(rawValue)
    setAdjustments((prev) => ({ ...prev, [feature]: Number.isFinite(parsed) ? parsed : 0 }))
  }

  function resetSimulator() {
    const cleared = {}
    for (const control of SIMULATOR_CONTROLS) {
      cleared[control.feature] = 0
    }
    setAdjustments(cleared)
    setSimResult(null)
    setOptResult(null)
    setSimError('')
  }

  async function runAutoOptimize() {
    if (!token) {
      setSimError('Missing auth token. Please re-login to run auto-optimize.')
      return
    }

    setOptLoading(true)
    setSimError('')

    try {
      const res = await fetch(`${API_BASE}/optimize-trajectory`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_features: baseFeatures,
          objective: optObjective,
          adjustable_features: SIMULATOR_CONTROLS.map((item) => item.feature),
        }),
      })

      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(body.detail || 'Auto-optimize failed.')
      }

      const optimizedAdjustments = { ...adjustments }
      for (const control of SIMULATOR_CONTROLS) {
        optimizedAdjustments[control.feature] = 0
      }

      for (const row of body.recommended_adjustments || []) {
        if (row?.feature in optimizedAdjustments) {
          optimizedAdjustments[row.feature] = Number(row.delta || 0)
        }
      }

      setAdjustments(optimizedAdjustments)
      setOptResult(body)
      setSimResult(body.simulation)
    } catch (err) {
      setSimError(err?.message || 'Could not run auto-optimize.')
    } finally {
      setOptLoading(false)
    }
  }

  async function runSimulator() {
    if (!token) {
      setSimError('Missing auth token. Please re-login to run the simulator.')
      return
    }

    setSimLoading(true)
    setSimError('')

    const filteredAdjustments = {}
    for (const [feature, delta] of Object.entries(adjustments)) {
      if (Math.abs(Number(delta)) >= 1e-6) {
        filteredAdjustments[feature] = Number(delta)
      }
    }

    try {
      const res = await fetch(`${API_BASE}/simulate-trajectory`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_features: baseFeatures,
          adjustments: filteredAdjustments,
        }),
      })

      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(body.detail || 'A/B simulation failed.')
      }

      setSimResult(body)
    } catch (err) {
      setSimError(err?.message || 'Could not run trajectory simulation.')
    } finally {
      setSimLoading(false)
    }
  }

  const soundDnaData = {
    labels: ['Energy', 'Danceability', 'Valence', 'Acousticness', 'Instrumentalness', 'Liveness', 'Speechiness'],
    datasets: [
      {
        label: 'Your Sound',
        data: [
          result.sound_dna.energy || 0,
          result.sound_dna.danceability || 0,
          result.sound_dna.valence || 0,
          result.sound_dna.acousticness || 0,
          result.sound_dna.instrumentalness || 0,
          result.sound_dna.liveness || 0,
          result.sound_dna.speechiness || 0,
        ],
        borderColor: '#6f5cff',
        backgroundColor: 'rgba(111, 92, 255, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
      },
    ],
  }

  const differenceData = {
    labels: (result.differences || []).map(d => d.feature),
    datasets: [
      {
        label: 'Your Value',
        data: (result.differences || []).map(d => d.song_value),
        backgroundColor: '#6f5cff',
      },
      {
        label: 'Cluster Average',
        data: (result.differences || []).map(d => d.reference_mean),
        backgroundColor: '#29b6f6',
      },
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { display: true, labels: { color: chartTextColor } },
    },
    scales: {
      r: { beginAtZero: true, max: 1, ticks: { color: chartTickColor }, grid: { color: chartGridColor } },
    },
  }

  const barOptions = {
    responsive: true,
    maintainAspectRatio: true,
    indexAxis: 'y',
    plugins: {
      legend: { position: 'top', labels: { color: chartTextColor } },
    },
    scales: {
      x: { ticks: { color: chartTickColor }, grid: { color: chartGridColor } },
      y: { ticks: { color: chartTickColor } },
    },
  }

  return (
    <div className="page-content fade-in">
      {/* Export Button */}
      <div className="analysis-controls">
        <button 
          className={`export-btn ${exporting ? 'loading' : ''}`}
          onClick={exportToPDF}
          disabled={exporting}
          title="Export analysis as PDF"
        >
          <span className="export-icon">📥</span>
          {exporting ? 'Generating PDF...' : 'Export as PDF'}
        </button>
      </div>

      <section className="analysis-header">
        <div className="cluster-badge">
          <h2>{result.style_cluster.label}</h2>
          <div className="confidence-bar">
            <div className="confidence-fill" style={{ width: `${result.style_cluster.confidence}%` }}></div>
          </div>
          <p>{result.style_cluster.confidence.toFixed(1)}% Confidence</p>
        </div>
      </section>

      <div className="tabs-container">
        <div className="tabs">
          <button className={`tab ${activeTab === 'dna' ? 'active' : ''}`} onClick={() => setActiveTab('dna')}>
            🎨 Sound DNA
          </button>
          <button className={`tab ${activeTab === 'similar' ? 'active' : ''}`} onClick={() => setActiveTab('similar')}>
            🔍 Similar Artists
          </button>
          <button className={`tab ${activeTab === 'difference' ? 'active' : ''}`} onClick={() => setActiveTab('difference')}>
            ⚡ Differences
          </button>
          <button className={`tab ${activeTab === 'paths' ? 'active' : ''}`} onClick={() => setActiveTab('paths')}>
            🧭 Creative Paths
          </button>
          <button className={`tab ${activeTab === 'market' ? 'active' : ''}`} onClick={() => setActiveTab('market')}>
            📈 Market Gap
          </button>
          <button className={`tab ${activeTab === 'simulator' ? 'active' : ''}`} onClick={() => setActiveTab('simulator')}>
            🧪 A/B Simulator
          </button>
        </div>
      </div>

      <div className="tab-content">
        {activeTab === 'dna' && (
          <section className="tab-pane slide-up">
            <h3>Your Sound DNA Profile</h3>
            <p className="mood-style">
              Mood: <strong>{result.sound_dna.mood || 'Unknown'}</strong> | Production: <strong>{result.sound_dna.production_style || 'Unknown'}</strong>
            </p>
            <div className="chart-container">
              <Radar data={soundDnaData} options={chartOptions} />
            </div>
            <div className="features-grid">
              {Object.entries(result.sound_dna).map(([key, value]) => {
                if (['mood', 'production_style'].includes(key) || typeof value !== 'number') return null
                return (
                  <div key={key} className="feature-card">
                    <span className="feature-name">{key}</span>
                    <span className="feature-value">{value.toFixed(3)}</span>
                  </div>
                )
              })}
            </div>
          </section>
        )}

        {activeTab === 'similar' && (
          <section className="tab-pane slide-up">
            <h3>Top Similar Tracks</h3>
            <div className="similar-list">
              {(result.top_similar || []).map((item, idx) => (
                <div key={`${item.artist}-${item.song}-${idx}`} className="similar-item">
                  <div className="similar-rank">{idx + 1}</div>
                  <div className="similar-info">
                    <h4>{item.artist || 'Unknown'}</h4>
                    <p>{item.song || 'Unknown'}</p>
                    <span className="cluster-tag">{item.cluster || 'N/A'}</span>
                  </div>
                  <div className="similarity-score">
                    <div className="score-bar">
                      <div className="score-fill" style={{ width: `${item.similarity || 0}%` }}></div>
                    </div>
                    <span>{(item.similarity || 0).toFixed(1)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeTab === 'difference' && (
          <section className="tab-pane slide-up">
            <h3>How You Compare</h3>
            {(result.differences || []).length > 0 && (
              <div className="chart-container">
                <Bar data={differenceData} options={barOptions} />
              </div>
            )}
            <div className="difference-details">
              {(result.differences || []).map((diff) => (
                <div key={diff.feature} className={`diff-card diff-${diff.tag || 'NORMAL'}`}>
                  <div className="diff-header">
                    <h4>{diff.feature || 'Unknown'}</h4>
                    <span className="diff-tag">{diff.tag || 'NORMAL'}</span>
                  </div>
                  <p className="diff-values">You: {(diff.song_value || 0).toFixed(3)} | Ref: {(diff.reference_mean || 0).toFixed(3)} ({(diff.delta_percent || 0).toFixed(1)}%)</p>
                  <p className="diff-interpretation">{diff.interpretation || 'No interpretation available'}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeTab === 'paths' && (
          <section className="tab-pane slide-up">
            <h3>Your Creative Paths</h3>
            <div className="paths-grid">
              {(result.paths || []).map((path) => (
                <div key={path.id} className="path-card">
                  <div className="path-header">
                    <span className="path-number">{path.id || '1'}</span>
                    <h4>{path.title || 'Untitled Path'}</h4>
                  </div>
                  <p className="path-strategy"><strong>Strategy:</strong> {path.strategy || 'Strategy not available'}</p>
                  <p className="path-expected"><strong>Expected:</strong> {path.expected || 'Expected outcome not available'}</p>
                  <p className="path-tradeoff"><strong>Tradeoff:</strong> {path.tradeoff || 'Tradeoff not available'}</p>
                  <div className="path-actions">
                    <strong>Actions:</strong>
                    <ul>
                      {(path.actions || []).map((action, idx) => (
                        <li key={idx}>{action}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeTab === 'market' && (
          <section className="tab-pane slide-up">
            <h3>Market Opportunities</h3>
            <div className="market-gaps">
              {(result.market_gaps && result.market_gaps.length > 0) ? (
                <div className="gaps-list">
                  {result.market_gaps.map((gap, idx) => (
                    <div key={idx} className="gap-item">
                      <span className="gap-icon">💡</span>
                      <p>{gap || 'Opportunity not specified'}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="no-gaps">No market gaps detected for your current profile.</p>
              )}
            </div>
          </section>
        )}

        {activeTab === 'simulator' && (
          <section className="tab-pane slide-up">
            <h3>A/B Trajectory Simulator</h3>
            <p className="mood-style">Adjust selected features in small increments and simulate how your cluster fit, similarity, and market opportunity may shift before re-producing.</p>

            <div className="simulator-grid">
              {SIMULATOR_CONTROLS.map((control) => (
                <div className="sim-control" key={control.feature}>
                  <div className="sim-control-header">
                    <span>{control.label}</span>
                    <span className="sim-delta">{formatDelta(control.feature, adjustments[control.feature] || 0)}</span>
                  </div>
                  <div className="sim-control-base">
                    Baseline: {Number(baseFeatures[control.feature] ?? 0).toFixed(control.feature === 'tempo' ? 1 : 3)}
                  </div>
                  <input
                    type="range"
                    min={control.min}
                    max={control.max}
                    step={control.step}
                    value={adjustments[control.feature]}
                    onChange={(e) => updateAdjustment(control.feature, e.target.value)}
                    className="sim-slider"
                  />
                </div>
              ))}
            </div>

            <div className="simulator-actions">
              <div className="optimizer-panel">
                <label htmlFor="optimizer-objective" className="optimizer-label">Auto-optimize objective</label>
                <select
                  id="optimizer-objective"
                  className="optimizer-select"
                  value={optObjective}
                  onChange={(e) => setOptObjective(e.target.value)}
                  disabled={optLoading || simLoading}
                >
                  <option value="similarity">Max Similarity</option>
                  <option value="opportunity">Max Opportunity</option>
                </select>
                <button className="history-view-btn" onClick={runAutoOptimize} disabled={optLoading || simLoading}>
                  {optLoading ? 'Optimizing...' : 'Auto-optimize Deltas'}
                </button>
              </div>
              <button className="history-view-btn" onClick={runSimulator} disabled={simLoading}>
                {simLoading ? 'Running Simulation...' : 'Run A/B Simulation'}
              </button>
              <button className="sim-reset-btn" onClick={resetSimulator} disabled={simLoading || optLoading}>
                Reset Adjustments
              </button>
            </div>

            {simError && <div className="error-message">{simError}</div>}

            {optResult && (
              <div className="sim-insights" style={{ marginBottom: '1rem' }}>
                <h4>Auto-optimize Summary</h4>
                <ul>
                  <li>Objective: {optResult.objective === 'opportunity' ? 'Max Opportunity' : 'Max Similarity'}</li>
                  <li>Baseline Score: {Number(optResult.baseline_score || 0).toFixed(3)}</li>
                  <li>Optimized Score: {Number(optResult.optimized_score || 0).toFixed(3)}</li>
                  <li>
                    Improvement: {Number(optResult.improvement || 0) >= 0 ? '+' : ''}
                    {Number(optResult.improvement || 0).toFixed(3)}
                  </li>
                </ul>
              </div>
            )}

            {simResult && (
              <div className="sim-results">
                <div className="sim-kpi-grid">
                  <div className="sim-kpi-card">
                    <h4>Cluster</h4>
                    <p>{simResult.before.style_cluster.label}</p>
                    <span>→ {simResult.after.style_cluster.label}</span>
                  </div>
                  <div className="sim-kpi-card">
                    <h4>Avg Similarity</h4>
                    <p>{simResult.before.avg_similarity.toFixed(2)}%</p>
                    <span className={simResult.similarity_delta >= 0 ? 'sim-positive' : 'sim-negative'}>
                      {simResult.similarity_delta >= 0 ? '+' : ''}{simResult.similarity_delta.toFixed(2)}
                    </span>
                  </div>
                  <div className="sim-kpi-card">
                    <h4>Opportunity Score</h4>
                    <p>{simResult.before.opportunity_score.toFixed(3)}</p>
                    <span className={simResult.opportunity_delta >= 0 ? 'sim-positive' : 'sim-negative'}>
                      {simResult.opportunity_delta >= 0 ? '+' : ''}{simResult.opportunity_delta.toFixed(3)}
                    </span>
                  </div>
                </div>

                <div className="sim-insights">
                  <h4>Simulation Insights</h4>
                  <ul>
                    {(simResult.insights || []).map((line, idx) => (
                      <li key={idx}>{line}</li>
                    ))}
                  </ul>
                </div>

                <div className="sim-after-list">
                  <h4>Projected Top Similar Tracks (B)</h4>
                  {(simResult.after.top_similar || []).map((item, idx) => (
                    <div key={`${item.artist}-${item.song}-${idx}`} className="similar-item">
                      <div className="similar-rank">{idx + 1}</div>
                      <div className="similar-info">
                        <h4>{item.artist || 'Unknown'}</h4>
                        <p>{item.song || 'Unknown'}</p>
                        <span className="cluster-tag">{item.cluster || 'N/A'}</span>
                      </div>
                      <div className="similarity-score">
                        <div className="score-bar">
                          <div className="score-fill" style={{ width: `${item.similarity || 0}%` }}></div>
                        </div>
                        <span>{(item.similarity || 0).toFixed(1)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  )
}
