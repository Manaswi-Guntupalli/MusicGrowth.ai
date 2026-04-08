import React from 'react'
import { cn } from '../../lib/cn'

const variantClasses = {
  level1: 'bg-bg-surface border border-border-subtle',
  level2: 'bg-bg-elevated border border-border-default',
  level3: 'bg-primary/10 border border-primary/30',
}

function Card({
  children,
  className,
  as: Component = 'div',
  variant = 'level1',
  ...props
}) {
  return (
    <Component
      className={cn(
        'rounded-card p-6',
        variantClasses[variant] || variantClasses.level1,
        className,
      )}
      {...props}
    >
      {children}
    </Component>
  )
}

export default React.memo(Card)
