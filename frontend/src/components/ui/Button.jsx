import React from 'react'
import { cn } from '../../lib/cn'

const variantClasses = {
  primary:
    'bg-gradient-to-r from-primary to-accent text-white font-medium rounded-button h-10 px-6 hover:opacity-90 active:scale-[0.98] transition-all',
  secondary:
    'border border-border-default text-text-secondary rounded-button h-10 px-4 hover:bg-white/5 transition-all',
  danger:
    'border border-danger/40 text-danger rounded-button h-8 px-4 text-sm hover:bg-danger/10 transition-all',
}

function Button({ children, className, variant = 'secondary', type = 'button', ...props }) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-2 disabled:opacity-55 disabled:cursor-not-allowed',
        variantClasses[variant] || variantClasses.secondary,
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}

export default React.memo(Button)
