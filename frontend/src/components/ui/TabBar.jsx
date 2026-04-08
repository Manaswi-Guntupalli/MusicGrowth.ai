import React from 'react'
import { cn } from '../../lib/cn'

function TabBar({ tabs, activeTab, onChange, onKeyDown }) {
  return (
    <div className="w-full border-b border-border-subtle overflow-x-auto no-scrollbar">
      <div className="min-w-[720px] flex h-12">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              id={`analysis-tab-${tab.id}`}
              role="tab"
              aria-selected={isActive}
              aria-controls={`analysis-panel-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => onChange(tab.id)}
              onKeyDown={(event) => onKeyDown?.(event, tab.id)}
              className={cn(
                'flex-1 min-w-[120px] inline-flex items-center justify-center border-b-2 text-[14px] font-medium transition-colors',
                isActive
                  ? 'border-primary text-primary'
                  : 'border-transparent text-text-muted hover:text-text-secondary',
              )}
            >
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default React.memo(TabBar)
