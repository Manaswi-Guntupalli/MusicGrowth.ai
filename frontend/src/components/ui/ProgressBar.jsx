import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../lib/cn'

function ProgressBar({ value = 0, className, showValue = true }) {
  const clamped = Math.max(0, Math.min(100, Number(value) || 0))

  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div className="h-1 w-full rounded-full bg-white/10 overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
          initial={{ width: 0 }}
          animate={{ width: `${clamped}%` }}
          transition={{ duration: 0.6, ease: 'easeOut', delay: 0.1 }}
        />
      </div>
      {showValue ? (
        <span className="text-[13px] tabular-nums text-accent min-w-[52px] text-right">
          {clamped.toFixed(1)}%
        </span>
      ) : null}
    </div>
  )
}

export default React.memo(ProgressBar)
