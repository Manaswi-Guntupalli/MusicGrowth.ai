import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Chart as ChartJS, RadarController, BarController, CategoryScale, LinearScale, RadialLinearScale, PointElement, LineElement, BarElement, Filler, Tooltip, Legend } from 'chart.js'
import { Radar, Bar } from 'react-chartjs-2'
import { jsPDF } from 'jspdf'
import { requestJson } from '../lib/apiClient'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import ProgressBar from '../components/ui/ProgressBar'
import SliderInput from '../components/ui/SliderInput'
import TabBar from '../components/ui/TabBar'
import { typographyTokens } from '../theme/tokens'
import { buildBarOptions, buildRadarOptions, chartTheme } from '../theme/chartTheme'

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

const ANALYSIS_TABS = [
  { id: 'dna', label: 'Sound DNA' },
  { id: 'similar', label: 'Similar Artists' },
  { id: 'difference', label: 'Differences' },
  { id: 'paths', label: 'Creative Paths' },
  { id: 'simulator', label: 'A/B Simulator' },
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
  const [simulatorMode, setSimulatorMode] = useState(null)
  const [pathsAiLoading, setPathsAiLoading] = useState(false)
  const [pathsAiError, setPathsAiError] = useState('')
  const [pathsAiResult, setPathsAiResult] = useState(null)
  const [activePathCard, setActivePathCard] = useState(0)
  const [adjustments, setAdjustments] = useState(() => {
    const initial = {}
    for (const control of SIMULATOR_CONTROLS) {
      initial[control.feature] = 0
    }
    return initial
  })

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

  const clusterConfidence = Number(result.style_cluster?.confidence ?? 0)
  const confidenceLabel = clusterConfidence >= 75 ? 'High Certainty' : clusterConfidence >= 50 ? 'Medium Certainty' : 'Low Certainty'
  const clusterConfidenceTooltip = 'Confidence estimates how strongly this track matches its predicted style cluster.'
  const recommendationConfidenceTooltip = 'Heuristic confidence estimates how stable and trustworthy the recommendation explanation is, not the cluster assignment certainty.'
  const tabIds = useMemo(() => ANALYSIS_TABS.map((tab) => tab.id), [])

  const baseFeatures = useMemo(
    () => FEATURE_ORDER.reduce((acc, name) => {
      acc[name] = Number(result.sound_dna?.[name] ?? 0)
      return acc
    }, {}),
    [result.sound_dna]
  )

  useEffect(() => {
    setPathsAiLoading(false)
    setPathsAiError('')
    setPathsAiResult(null)
    setActivePathCard(0)
  }, [result?.analysis_id])

  async function exportToPDF() {
    if (exporting) return
    setExporting(true)

    try {
      const pdf = new jsPDF('p', 'mm', 'a4')
      const pageWidth = pdf.internal.pageSize.getWidth()
      const pageHeight = pdf.internal.pageSize.getHeight()
      const margin = 12
      const contentWidth = pageWidth - margin * 2
      let y = margin

      const ensureSpace = (needed = 8) => {
        if (y + needed > pageHeight - margin) {
          pdf.addPage()
          y = margin
        }
      }

      const writeWrapped = (text, fontSize = 10, color = [56, 65, 90], lineHeight = 5) => {
        const content = String(text || '').trim()
        if (!content) return
        pdf.setFontSize(fontSize)
        pdf.setTextColor(color[0], color[1], color[2])
        const lines = pdf.splitTextToSize(content, contentWidth)
        for (const line of lines) {
          ensureSpace(lineHeight)
          pdf.text(line, margin, y)
          y += lineHeight
        }
      }

      const writeSectionTitle = (title) => {
        ensureSpace(10)
        y += 1
        pdf.setFontSize(13)
        pdf.setTextColor(46, 53, 87)
        pdf.text(title, margin, y)
        y += 2.5
        pdf.setDrawColor(200, 210, 235)
        pdf.line(margin, y, pageWidth - margin, y)
        y += 5
      }

      const writeBullets = (items) => {
        for (const item of items) {
          const lines = pdf.splitTextToSize(String(item || ''), contentWidth - 4)
          if (lines.length === 0) continue
          ensureSpace(5)
          pdf.setFontSize(10)
          pdf.setTextColor(56, 65, 90)
          pdf.text('\u2022', margin, y)
          pdf.text(lines[0], margin + 4, y)
          y += 5
          for (const line of lines.slice(1)) {
            ensureSpace(5)
            pdf.text(line, margin + 4, y)
            y += 5
          }
        }
      }

      const writeKV = (label, value) => {
        ensureSpace(5)
        pdf.setFontSize(10)
        pdf.setTextColor(40, 48, 75)
        pdf.text(`${label}:`, margin, y)
        const lines = pdf.splitTextToSize(String(value || 'N/A'), contentWidth - 34)
        if (lines.length > 0) {
          pdf.setTextColor(70, 80, 110)
          pdf.text(lines[0], margin + 34, y)
          y += 5
          for (const line of lines.slice(1)) {
            ensureSpace(5)
            pdf.text(line, margin + 34, y)
            y += 5
          }
        } else {
          y += 5
        }
      }

      const writeExplainability = (title, block) => {
        if (!block) return
        writeSectionTitle(title)
        writeKV('Source', block.source === 'openai' ? 'OpenAI explanation layer' : 'ML local explanation')
        writeKV('Confidence', Number(block.confidence || 0).toFixed(3))
        writeWrapped(block.summary || 'No summary available.')
        y += 2
        if ((block.why_it_changed || []).length > 0) {
          writeWrapped('Why it changed:', 10, [40, 48, 75])
          writeBullets(block.why_it_changed)
        }
        if ((block.tradeoffs || []).length > 0) {
          writeWrapped('Tradeoffs:', 10, [40, 48, 75])
          writeBullets(block.tradeoffs)
        }
        if ((block.next_steps || []).length > 0) {
          writeWrapped('Recommended next steps:', 10, [40, 48, 75])
          writeBullets(block.next_steps)
        }
        if ((block.feature_notes || []).length > 0) {
          writeWrapped('Feature-level notes:', 10, [40, 48, 75])
          for (const note of block.feature_notes) {
            writeKV(
              `${note.feature} (${note.impact})`,
              note.explanation || 'No explanation provided.'
            )
          }
        }
        if (block.disclaimer) {
          y += 1
          writeWrapped(`Disclaimer: ${block.disclaimer}`, 9, [110, 116, 140])
        }
      }

      // Cover header
      pdf.setFillColor(111, 92, 255)
      pdf.rect(0, 0, pageWidth, 46, 'F')
      pdf.setTextColor(255, 255, 255)
      pdf.setFontSize(22)
      pdf.text('MusicGrowth.AI Strategic Analysis', pageWidth / 2, 21, { align: 'center' })
      pdf.setFontSize(11)
      pdf.text('ML decisions with explainable trajectory guidance', pageWidth / 2, 31, { align: 'center' })

      y = 56
      const generatedAt = new Date().toLocaleString()
      writeKV('Generated', generatedAt)
      writeKV('Cluster', result.style_cluster.label)
      writeKV('Cluster confidence', `${clusterConfidence.toFixed(1)}%`)
      writeKV('Mood / Production', `${result.sound_dna.mood} / ${result.sound_dna.production_style}`)

      writeSectionTitle('Sound DNA Snapshot')
      const dnaRows = [
        ['Tempo', `${Number(result.sound_dna.tempo || 0).toFixed(2)} bpm`],
        ['Energy', Number(result.sound_dna.energy || 0).toFixed(3)],
        ['Danceability', Number(result.sound_dna.danceability || 0).toFixed(3)],
        ['Valence', Number(result.sound_dna.valence || 0).toFixed(3)],
        ['Acousticness', Number(result.sound_dna.acousticness || 0).toFixed(3)],
        ['Instrumentalness', Number(result.sound_dna.instrumentalness || 0).toFixed(3)],
        ['Liveness', Number(result.sound_dna.liveness || 0).toFixed(3)],
        ['Speechiness', Number(result.sound_dna.speechiness || 0).toFixed(3)],
        ['Loudness', `${Number(result.sound_dna.loudness || 0).toFixed(3)} dB`],
      ]
      for (const [label, value] of dnaRows) {
        writeKV(label, value)
      }

      writeSectionTitle('Top Similar References')
      const similarRows = (result.top_similar || []).slice(0, 5)
      if (similarRows.length === 0) {
        writeWrapped('No similar references found in the current output.')
      } else {
        let rank = 1
        for (const item of similarRows) {
          writeKV(
            `#${rank}`,
            `${item.artist} - ${item.song} | ${item.cluster} | Similarity ${Number(item.similarity || 0).toFixed(2)}%`
          )
          rank += 1
        }
      }

      writeSectionTitle('Key Differences vs Cluster')
      const differences = [...(result.differences || [])]
        .sort((a, b) => Math.abs(Number(b.delta_percent || 0)) - Math.abs(Number(a.delta_percent || 0)))
        .slice(0, 6)
      if (differences.length === 0) {
        writeWrapped('No difference insights are available.')
      } else {
        for (const diff of differences) {
          const diffTagLabel = displayDiffTag(diff.tag)
          writeKV(
            `${diff.feature} [${diffTagLabel}]`,
            `You ${Number(diff.song_value || 0).toFixed(3)} vs Ref ${Number(diff.reference_mean || 0).toFixed(3)} (${Number(diff.delta_percent || 0).toFixed(1)}%)`
          )
          writeWrapped(diff.interpretation || '', 9, [88, 96, 124], 4.5)
        }
      }

      writeSectionTitle('Strategic Paths')
      for (const path of result.paths || []) {
        writeKV(`${path.id} - ${path.title}`, path.strategy)
        writeWrapped(`Expected: ${path.expected}`, 9, [88, 96, 124], 4.5)
        writeWrapped(`Tradeoff: ${path.tradeoff}`, 9, [88, 96, 124], 4.5)
        writeBullets(path.actions || [])
      }

      if (simResult || optResult) {
        writeSectionTitle('Trajectory Simulation Summary')
        if (optResult) {
          writeKV('Objective', optResult.objective === 'opportunity' ? 'Max Opportunity' : 'Max Similarity')
          writeKV(
            'Score improvement',
            optResult.objective === 'opportunity'
              ? formatOpportunity(optResult.improvement)
              : Number(optResult.improvement || 0).toFixed(3)
          )
        }

        const sim = simResult || optResult?.simulation
        if (sim) {
          writeKV('Cluster transition', `${sim.before.style_cluster.label} -> ${sim.after.style_cluster.label}`)
          writeKV('Similarity delta', `${Number(sim.similarity_delta || 0).toFixed(2)}`)
          writeKV('Opportunity delta', formatOpportunity(sim.opportunity_delta || 0))
          writeWrapped('Simulation insights:')
          writeBullets(sim.insights || [])

          if ((sim.adjustments_applied || []).length > 0) {
            writeWrapped('Applied adjustments:')
            for (const row of sim.adjustments_applied) {
              writeKV(
                row.feature,
                `${Number(row.before || 0).toFixed(3)} -> ${Number(row.after || 0).toFixed(3)} (delta ${Number(row.delta || 0).toFixed(3)})`
              )
            }
          }
        }
      }

      writeExplainability('Trajectory Explainability', simResult?.explainability || optResult?.explainability)

      // Footer with page numbers
      const totalPages = pdf.getNumberOfPages()
      for (let page = 1; page <= totalPages; page += 1) {
        pdf.setPage(page)
        pdf.setFontSize(9)
        pdf.setTextColor(120, 126, 150)
        pdf.text(`Page ${page} of ${totalPages}`, pageWidth - margin, pageHeight - 6, { align: 'right' })
      }

      const safeLabel = String(result.style_cluster.label || 'analysis').replace(/[^a-z0-9_-]+/gi, '_')
      pdf.save(`MusicGrowth.AI-Report-${safeLabel}.pdf`)
    } catch (err) {
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

  function normalizeDiffTag(rawTag) {
    return String(rawTag || 'NORMAL')
      .trim()
      .toUpperCase()
      .replace(/\s+/g, '_') || 'NORMAL'
  }

  function displayDiffTag(rawTag) {
    return normalizeDiffTag(rawTag).replace(/_/g, ' ')
  }

  function formatOpportunity(value) {
    return Number(value || 0).toFixed(5)
  }

  function renderExplainability(explainability) {
    if (!explainability) return null

    return (
      <div className="explainability-panel">
        <div className="explainability-header">
          <h4>Why this recommendation?</h4>
          <Badge variant="local">Local analysis</Badge>
        </div>

        <p className="explainability-summary">{explainability.summary || 'No explanation summary available.'}</p>

        <div className="explainability-grid">
          <div className="explainability-card">
            <h5>Why it changed</h5>
            <ul>
              {(explainability.why_it_changed || []).map((line, idx) => (
                <li key={idx}>{line}</li>
              ))}
            </ul>
          </div>

          <div className="explainability-card">
            <h5>Tradeoffs</h5>
            <ul>
              {(explainability.tradeoffs || []).map((line, idx) => (
                <li key={idx}>{line}</li>
              ))}
            </ul>
          </div>

          <div className="explainability-card">
            <h5>Next steps</h5>
            <ul>
              {(explainability.next_steps || []).map((line, idx) => (
                <li key={idx}>{line}</li>
              ))}
            </ul>
          </div>
        </div>

        {(explainability.feature_notes || []).length > 0 && (
          <div className="feature-notes-grid">
            {(explainability.feature_notes || []).map((note, idx) => (
              <div key={`${note.feature}-${idx}`} className="feature-note-card">
                <div className="feature-note-head">
                  <strong>{note.feature || 'Feature'}</strong>
                  <span className={`feature-note-pill ${note.impact === 'increase' ? 'pill-up' : 'pill-down'}`}>
                    {note.impact === 'increase' ? 'Increased' : 'Decreased'}
                  </span>
                </div>
                <p>{note.explanation || 'No feature note available.'}</p>
              </div>
            ))}
          </div>
        )}

        <p className="explainability-footer">
          <span className="tooltip-wrap">
            <span className="tooltip-label" tabIndex={0} aria-describedby="recommendation-confidence-tip">
              Recommendation Confidence (Heuristic)
            </span>
            <span className="tooltip-bubble" id="recommendation-confidence-tip" role="tooltip">
              {recommendationConfidenceTooltip}
            </span>
          </span>
          : <strong>{Number(explainability.confidence || 0).toFixed(3)}</strong> | {explainability.disclaimer || 'ML explanation only.'}
        </p>
      </div>
    )
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
    setSimulatorMode(null)
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
      const body = await requestJson('/optimize-trajectory', {
        method: 'POST',
        token,
        body: {
          base_features: baseFeatures,
          objective: optObjective,
          adjustable_features: SIMULATOR_CONTROLS.map((item) => item.feature),
        },
        timeoutMs: 20000,
        retries: 0,
      })

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
      setSimResult(null)
      setSimulatorMode('optimize')
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
      const body = await requestJson('/simulate-trajectory', {
        method: 'POST',
        token,
        body: {
          base_features: baseFeatures,
          adjustments: filteredAdjustments,
        },
        timeoutMs: 20000,
        retries: 0,
      })

      setSimResult(body)
      setSimulatorMode('simulate')
    } catch (err) {
      setSimError(err?.message || 'Could not run trajectory simulation.')
    } finally {
      setSimLoading(false)
    }
  }

  function moveCreativePathCard(direction) {
    const cards = pathsAiResult?.cards || []
    if (cards.length <= 1) return

    setActivePathCard((prev) => {
      const next = prev + direction
      if (next < 0) return cards.length - 1
      if (next >= cards.length) return 0
      return next
    })
  }

  async function runCreativePathsAiSummary() {
    if (!token) {
      setPathsAiError('Missing auth token. Please re-login to generate AI summary.')
      return
    }

    if (!(result.paths || []).length) {
      setPathsAiError('No creative paths are available for summarization.')
      return
    }

    setPathsAiLoading(true)
    setPathsAiError('')

    try {
      const body = await requestJson('/creative-paths-ai-summary', {
        method: 'POST',
        token,
        body: {
          sound_dna: result.sound_dna,
          style_cluster: result.style_cluster,
          paths: result.paths || [],
          differences: (result.differences || []).slice(0, 6),
        },
        timeoutMs: 20000,
        retries: 0,
      })

      setPathsAiResult(body)
      setActivePathCard(0)
    } catch (err) {
      setPathsAiError(err?.message || 'Could not generate AI summary for creative paths.')
    } finally {
      setPathsAiLoading(false)
    }
  }

  const creativePathCards = pathsAiResult?.cards || []
  const activeCreativePath = creativePathCards[activePathCard] || null
  const optimizeProjection = optResult?.simulation || null

  const differences = useMemo(() => result.differences || [], [result.differences])
  const soundDnaEntries = useMemo(
    () => Object.entries(result.sound_dna || {}),
    [result.sound_dna]
  )
  const numericSoundDnaEntries = useMemo(
    () => soundDnaEntries.filter(([key, value]) => !['mood', 'production_style'].includes(key) && typeof value === 'number'),
    [soundDnaEntries]
  )

  const soundDnaData = useMemo(() => ({
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
        borderColor: chartTheme.radar.stroke,
        backgroundColor: chartTheme.radar.fill,
        borderWidth: chartTheme.radar.borderWidth,
        fill: true,
        tension: 0.4,
        pointRadius: chartTheme.radar.pointRadius,
        pointBackgroundColor: chartTheme.radar.point,
        pointBorderColor: chartTheme.radar.point,
      },
    ],
  }), [result.sound_dna])

  const differenceData = useMemo(() => ({
    labels: differences.map((d) => d.feature),
    datasets: [
      {
        label: 'Your Value',
        data: differences.map((d) => d.song_value),
        backgroundColor: chartTheme.bar.yourValue,
        borderRadius: 4,
        barThickness: 20,
      },
      {
        label: 'Cluster Average',
        data: differences.map((d) => d.reference_mean),
        backgroundColor: chartTheme.bar.clusterValue,
        borderRadius: 4,
        barThickness: 20,
      },
    ],
  }), [differences])

  const chartOptions = useMemo(() => buildRadarOptions(), [])

  const barOptions = useMemo(() => buildBarOptions(), [])

  function handleTabsKeyDown(event, currentTabId) {
    const currentIndex = tabIds.indexOf(currentTabId)
    if (currentIndex < 0) return

    const activateAndFocus = (nextTabId) => {
      setActiveTab(nextTabId)
      requestAnimationFrame(() => {
        const target = document.getElementById(`analysis-tab-${nextTabId}`)
        if (target instanceof HTMLElement) {
          target.focus()
        }
      })
    }

    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      event.preventDefault()
      const nextIndex = (currentIndex + 1) % tabIds.length
      activateAndFocus(tabIds[nextIndex])
    }

    if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      event.preventDefault()
      const prevIndex = (currentIndex - 1 + tabIds.length) % tabIds.length
      activateAndFocus(tabIds[prevIndex])
    }

    if (event.key === 'Home') {
      event.preventDefault()
      activateAndFocus(tabIds[0])
    }

    if (event.key === 'End') {
      event.preventDefault()
      activateAndFocus(tabIds[tabIds.length - 1])
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="space-y-6"
    >
      <div className="flex justify-end">
        <Button
          variant="primary"
          className="h-10"
          onClick={exportToPDF}
          disabled={exporting}
          title="Export analysis as PDF"
        >
          {exporting ? 'Generating PDF...' : 'Export as PDF'}
        </Button>
      </div>

      <Card variant="level3" className="space-y-3">
        <h2 className={typographyTokens.sectionHeader}>{result.style_cluster.label}</h2>
        <div className="h-2 w-full rounded-full bg-white/10 overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-primary to-accent" style={{ width: `${clusterConfidence}%` }}></div>
        </div>
        <p className="text-[13px] text-text-secondary">
          {clusterConfidence.toFixed(1)}%
          {' '}
          <span className="tooltip-wrap">
            <span className="tooltip-label" tabIndex={0} aria-describedby="cluster-confidence-tip">
              Cluster Confidence
            </span>
            <span className="tooltip-bubble" id="cluster-confidence-tip" role="tooltip">
              {clusterConfidenceTooltip}
            </span>
          </span>
          {` | ${confidenceLabel}`}
        </p>
      </Card>

      <TabBar
        tabs={ANALYSIS_TABS}
        activeTab={activeTab}
        onChange={setActiveTab}
        onKeyDown={handleTabsKeyDown}
      />

      <div>
        {activeTab === 'dna' && (
          <section className="tab-pane" role="tabpanel" id="analysis-panel-dna" aria-labelledby="analysis-tab-dna" tabIndex={0}>
            <h3>Your Sound DNA Profile</h3>
            <p className="mood-style">
              Mood: <strong>{result.sound_dna.mood || 'Unknown'}</strong> | Production: <strong>{result.sound_dna.production_style || 'Unknown'}</strong>
            </p>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="chart-container"
            >
              <Radar data={soundDnaData} options={chartOptions} />
            </motion.div>
            <div className="features-grid">
              {numericSoundDnaEntries.map(([key, value]) => (
                <div key={key} className="feature-card">
                  <span className="feature-name">{key}</span>
                  <span className="feature-value">{value.toFixed(3)}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeTab === 'similar' && (
          <section className="tab-pane" role="tabpanel" id="analysis-panel-similar" aria-labelledby="analysis-tab-similar" tabIndex={0}>
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
                    <ProgressBar value={item.similarity || 0} />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeTab === 'difference' && (
          <section className="tab-pane" role="tabpanel" id="analysis-panel-difference" aria-labelledby="analysis-tab-difference" tabIndex={0}>
            <h3>How You Compare</h3>
            {differences.length > 0 && (
              <div className="chart-container">
                <Bar data={differenceData} options={barOptions} />
              </div>
            )}
            <div className="difference-details">
              {differences.map((diff, idx) => {
                const tagKey = normalizeDiffTag(diff.tag)
                const tagLabel = displayDiffTag(diff.tag)
                return (
                  <div key={`${diff.feature}-${idx}`} className={`diff-card diff-${tagKey}`}>
                    <div className="diff-header">
                      <h4>{diff.feature || 'Unknown'}</h4>
                      <span className="diff-tag">{tagLabel}</span>
                    </div>
                    <p className="diff-values">You: {(diff.song_value || 0).toFixed(3)} | Ref: {(diff.reference_mean || 0).toFixed(3)} ({(diff.delta_percent || 0).toFixed(1)}%)</p>
                    <p className="diff-interpretation">{diff.interpretation || 'No interpretation available'}</p>
                  </div>
                )
              })}
            </div>
          </section>
        )}

        {activeTab === 'paths' && (
          <section className="tab-pane" role="tabpanel" id="analysis-panel-paths" aria-labelledby="analysis-tab-paths" tabIndex={0}>
            <h3>Your Creative Paths</h3>
            <div className="paths-grid">
              {(result.paths || []).map((path, index) => (
                <motion.div key={path.id} whileHover={{ scale: 1.01, transition: { duration: 0.15 } }}>
                  <div className="path-card">
                    <div className={`path-accent ${index === 0 ? 'path-accent-a' : index === 1 ? 'path-accent-b' : 'path-accent-c'}`}></div>
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
                </motion.div>
              ))}
            </div>

            <div className="creative-ai-actions">
              <Button onClick={runCreativePathsAiSummary} disabled={pathsAiLoading}>
                {pathsAiLoading ? 'Generating AI Summary...' : 'AI Summary For All 3 Paths'}
              </Button>
            </div>

            {pathsAiError && <div className="error-message">{pathsAiError}</div>}

            {activeCreativePath && (
              <div className="creative-ai-slider-panel">
                <div className="creative-ai-slider-top">
                  <h4>AI Summary: Creative Paths</h4>
                  <Badge variant="local">Local analysis</Badge>
                </div>

                <div className="creative-ai-slider-shell">
                  <button
                    className="creative-ai-nav"
                    onClick={() => moveCreativePathCard(-1)}
                    disabled={creativePathCards.length <= 1}
                    aria-label="Previous creative path summary"
                  >
                    Prev
                  </button>

                  <article className="creative-ai-card">
                    <div className="creative-ai-card-header">
                      <span className="path-number">{activeCreativePath.id || String(activePathCard + 1)}</span>
                      <h5>{activeCreativePath.title || 'Creative Path'}</h5>
                    </div>

                    <p className="creative-ai-line"><strong>Summary:</strong> {activeCreativePath.summary || 'No summary available.'}</p>
                    <p className="creative-ai-line"><strong>Rationale:</strong> {activeCreativePath.rationale || 'No rationale available.'}</p>

                    <div className="creative-ai-grid">
                      <div className="creative-ai-block">
                        <h6>Immediate actions</h6>
                        <ul>
                          {(activeCreativePath.immediate_actions || []).map((row, idx) => (
                            <li key={`action-${idx}`}>{row}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="creative-ai-block">
                        <h6>Caution points</h6>
                        <ul>
                          {(activeCreativePath.caution_points || []).map((row, idx) => (
                            <li key={`caution-${idx}`}>{row}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="creative-ai-block">
                        <h6>Success KPIs</h6>
                        <ul>
                          {(activeCreativePath.success_kpis || []).map((row, idx) => (
                            <li key={`kpi-${idx}`}>{row}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </article>

                  <button
                    className="creative-ai-nav"
                    onClick={() => moveCreativePathCard(1)}
                    disabled={creativePathCards.length <= 1}
                    aria-label="Next creative path summary"
                  >
                    Next
                  </button>
                </div>

                {creativePathCards.length > 1 && (
                  <div className="creative-ai-dots">
                    {creativePathCards.map((card, idx) => (
                      <button
                        key={`${card.id || card.title || 'path'}-${idx}`}
                        className={`creative-ai-dot ${idx === activePathCard ? 'active' : ''}`}
                        onClick={() => setActivePathCard(idx)}
                        aria-label={`Show summary card ${idx + 1}`}
                      />
                    ))}
                  </div>
                )}

                <p className="creative-ai-disclaimer">Local analysis</p>
              </div>
            )}
          </section>
        )}

        {activeTab === 'simulator' && (
          <section className="tab-pane" role="tabpanel" id="analysis-panel-simulator" aria-labelledby="analysis-tab-simulator" tabIndex={0}>
            <h3>A/B Trajectory Simulator</h3>
            <p className="mood-style">Adjust selected features in small increments and simulate how your cluster fit, similarity, and market opportunity may shift before re-producing.</p>

            <div className="simulator-grid">
              {SIMULATOR_CONTROLS.map((control) => (
                <SliderInput
                  key={control.feature}
                  id={`slider-${control.feature}`}
                  label={control.label}
                  value={adjustments[control.feature]}
                  min={control.min}
                  max={control.max}
                  step={control.step}
                  detail={formatDelta(control.feature, adjustments[control.feature] || 0)}
                  onChange={(e) => updateAdjustment(control.feature, e.target.value)}
                />
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
                <Button onClick={runAutoOptimize} disabled={optLoading || simLoading}>
                  {optLoading ? 'Optimizing...' : 'Auto-optimize Deltas'}
                </Button>
              </div>
              <Button variant="primary" onClick={runSimulator} disabled={simLoading}>
                {simLoading ? 'Running Simulation...' : 'Run A/B Simulation'}
              </Button>
              <Button className="sim-reset-btn" onClick={resetSimulator} disabled={simLoading || optLoading}>
                Reset Adjustments
              </Button>
            </div>

            {simError && <div className="error-message">{simError}</div>}

            {simulatorMode === 'optimize' && optResult && (
              <div className="sim-results">
                <div className="sim-insights mb-4">
                  <h4>Auto-optimize Projection</h4>
                  <ul>
                    <li>Objective: {optResult.objective === 'opportunity' ? 'Max Opportunity' : 'Max Similarity'}</li>
                    <li>Baseline Score: {optResult.objective === 'opportunity' ? formatOpportunity(optResult.baseline_score) : Number(optResult.baseline_score || 0).toFixed(3)}</li>
                    <li>Optimized Score: {optResult.objective === 'opportunity' ? formatOpportunity(optResult.optimized_score) : Number(optResult.optimized_score || 0).toFixed(3)}</li>
                    <li>
                      Improvement: {Number(optResult.improvement || 0) >= 0 ? '+' : ''}
                      {optResult.objective === 'opportunity' ? formatOpportunity(optResult.improvement) : Number(optResult.improvement || 0).toFixed(3)}
                    </li>
                  </ul>

                  {optimizeProjection && (
                    <>
                      <div className="sim-kpi-grid mt-4">
                        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }} className="sim-kpi-card">
                          <h4>Cluster</h4>
                          <p>{optimizeProjection.before.style_cluster.label}</p>
                          <span>to {optimizeProjection.after.style_cluster.label}</span>
                        </motion.div>
                        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28, delay: 0.08 }} className="sim-kpi-card">
                          <h4>Avg Similarity</h4>
                          <p>{optimizeProjection.before.avg_similarity.toFixed(2)}%</p>
                          <span className={optimizeProjection.similarity_delta >= 0 ? 'sim-positive' : 'sim-negative'}>
                            {optimizeProjection.similarity_delta >= 0 ? '+' : ''}{optimizeProjection.similarity_delta.toFixed(2)}
                          </span>
                        </motion.div>
                        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28, delay: 0.16 }} className="sim-kpi-card">
                          <h4>Opportunity Score</h4>
                          <p>{formatOpportunity(optimizeProjection.before.opportunity_score)}</p>
                          <span className={optimizeProjection.opportunity_delta >= 0 ? 'sim-positive' : 'sim-negative'}>
                            {optimizeProjection.opportunity_delta >= 0 ? '+' : ''}{formatOpportunity(optimizeProjection.opportunity_delta)}
                          </span>
                        </motion.div>
                      </div>

                      <h5 className="mt-4">Projected insights</h5>
                      <ul>
                        {(optimizeProjection.insights || []).map((line, idx) => (
                          <li key={idx}>{line}</li>
                        ))}
                      </ul>
                    </>
                  )}

                  {renderExplainability(optResult.explainability)}
                </div>

                {optimizeProjection && (
                  <div className="sim-after-list">
                    <h4>Projected Top Similar Tracks (Optimized B)</h4>
                    {(optimizeProjection.after.top_similar || []).map((item, idx) => (
                      <div key={`${item.artist}-${item.song}-${idx}`} className="similar-item">
                        <div className="similar-rank">{idx + 1}</div>
                        <div className="similar-info">
                          <h4>{item.artist || 'Unknown'}</h4>
                          <p>{item.song || 'Unknown'}</p>
                          <span className="cluster-tag">{item.cluster || 'N/A'}</span>
                        </div>
                        <div className="similarity-score">
                          <ProgressBar value={item.similarity || 0} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {simulatorMode === 'simulate' && simResult && (
              <div className="sim-results">
                <div className="sim-kpi-grid">
                  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }} className="sim-kpi-card">
                    <h4>Cluster</h4>
                    <p>{simResult.before.style_cluster.label}</p>
                    <span>to {simResult.after.style_cluster.label}</span>
                  </motion.div>
                  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28, delay: 0.08 }} className="sim-kpi-card">
                    <h4>Avg Similarity</h4>
                    <p>{simResult.before.avg_similarity.toFixed(2)}%</p>
                    <span className={simResult.similarity_delta >= 0 ? 'sim-positive' : 'sim-negative'}>
                      {simResult.similarity_delta >= 0 ? '+' : ''}{simResult.similarity_delta.toFixed(2)}
                    </span>
                  </motion.div>
                  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28, delay: 0.16 }} className="sim-kpi-card">
                    <h4>Opportunity Score</h4>
                    <p>{formatOpportunity(simResult.before.opportunity_score)}</p>
                    <span className={simResult.opportunity_delta >= 0 ? 'sim-positive' : 'sim-negative'}>
                      {simResult.opportunity_delta >= 0 ? '+' : ''}{formatOpportunity(simResult.opportunity_delta)}
                    </span>
                  </motion.div>
                </div>

                <div className="sim-insights">
                  <h4>Simulation Insights</h4>
                  <ul>
                    {(simResult.insights || []).map((line, idx) => (
                      <li key={idx}>{line}</li>
                    ))}
                  </ul>
                  {renderExplainability(simResult.explainability)}
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
                        <ProgressBar value={item.similarity || 0} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}
      </div>
    </motion.div>
  )
}
