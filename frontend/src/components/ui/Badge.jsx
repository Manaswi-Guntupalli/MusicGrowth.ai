import React from 'react'
import { cn } from '../../lib/cn'

const variantClasses = {
  normal: 'bg-white/10 text-text-secondary text-[11px] font-medium px-2 py-0.5 rounded-badge uppercase tracking-wider',
  opportunity: 'bg-accent-warm/15 text-accent-warm text-[11px] font-medium px-2 py-0.5 rounded-badge uppercase tracking-wider',
  subtle: 'bg-white/8 text-text-secondary text-[11px] font-medium px-2 py-0.5 rounded-full',
  local: 'text-[12px] font-medium text-text-muted uppercase tracking-wider',
}

function Badge({ children, className, variant = 'normal', ...props }) {
  return (
    <span className={cn(variantClasses[variant] || variantClasses.normal, className)} {...props}>
      {children}
    </span>
  )
}

export default React.memo(Badge)
