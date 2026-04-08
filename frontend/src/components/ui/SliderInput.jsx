import React from 'react'
import { typographyTokens } from '../../theme/tokens'

function SliderInput({
  id,
  label,
  value,
  min,
  max,
  step,
  onChange,
  detail,
}) {
  const numericValue = Number(value)
  const safeMin = Number(min)
  const safeMax = Number(max)
  const ratio = ((numericValue - safeMin) / (safeMax - safeMin || 1)) * 100
  const progress = `${Math.max(0, Math.min(100, ratio))}%`

  return (
    <div className="bg-bg-elevated border border-border-default rounded-card p-4">
      <div className="flex items-start justify-between gap-3">
        <p className={typographyTokens.label}>{label}</p>
        <p className="text-[13px] text-text-primary tabular-nums">{detail}</p>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={onChange}
        className="mt-4 w-full sim-slider"
        style={{ '--progress': progress }}
      />
    </div>
  )
}

export default React.memo(SliderInput)
