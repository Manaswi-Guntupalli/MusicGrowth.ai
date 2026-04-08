import { colorTokens } from './tokens'

export const chartTheme = Object.freeze({
  radar: {
    stroke: colorTokens.primary,
    fill: 'rgba(108, 92, 231, 0.12)',
    point: colorTokens.primary,
    pointRadius: 4,
    borderWidth: 2,
    rings: 5,
    grid: 'rgba(255,255,255,0.08)',
  },
  bar: {
    yourValue: colorTokens.primary,
    clusterValue: colorTokens.accent,
    zeroLine: 'rgba(255,255,255,0.2)',
    grid: 'rgba(255,255,255,0.08)',
  },
  label: {
    primary: colorTokens.textPrimary,
    secondary: colorTokens.textSecondary,
    muted: colorTokens.textMuted,
  },
})

export function buildRadarOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: chartTheme.label.secondary,
          font: { size: 12 },
        },
      },
    },
    scales: {
      r: {
        beginAtZero: true,
        max: 1,
        ticks: {
          display: false,
          stepSize: 0.2,
        },
        grid: { color: chartTheme.radar.grid },
        angleLines: { color: chartTheme.radar.grid },
        pointLabels: {
          color: chartTheme.label.secondary,
          font: { size: 12 },
          padding: 12,
        },
      },
    },
  }
}

export function buildBarOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: chartTheme.label.secondary,
          font: { size: 12 },
        },
      },
      tooltip: {
        backgroundColor: colorTokens.bgElevated,
        borderColor: colorTokens.borderDefault,
        borderWidth: 1,
        titleColor: chartTheme.label.primary,
        bodyColor: chartTheme.label.secondary,
      },
    },
    scales: {
      x: {
        min: -50,
        max: 50,
        ticks: {
          color: chartTheme.label.secondary,
          callback: (value) => `${value}%`,
        },
        grid: {
          color: chartTheme.bar.grid,
        },
        border: {
          color: chartTheme.bar.zeroLine,
        },
      },
      y: {
        ticks: {
          color: chartTheme.label.secondary,
          font: { size: 12 },
        },
        grid: {
          display: false,
        },
      },
    },
  }
}
