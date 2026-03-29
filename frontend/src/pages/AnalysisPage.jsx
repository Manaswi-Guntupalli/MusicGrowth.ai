import { useState } from 'react'
import { Chart as ChartJS, RadarController, BarController, CategoryScale, LinearScale, RadialLinearScale, PointElement, LineElement, BarElement, Filler, Tooltip, Legend } from 'chart.js'
import { Radar, Bar } from 'react-chartjs-2'
import { jsPDF } from 'jspdf'
import html2canvas from 'html2canvas'

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

export default function AnalysisPage({ result, theme = 'dark' }) {
  const [activeTab, setActiveTab] = useState('dna')
  const [exporting, setExporting] = useState(false)

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
      </div>
    </div>
  )
}
