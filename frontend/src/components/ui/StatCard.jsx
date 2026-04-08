import React from 'react'
import Card from './Card'
import { cn } from '../../lib/cn'
import { typographyTokens } from '../../theme/tokens'

function StatCard({ label, value, helper, className }) {
  return (
    <Card className={cn('p-4', className)}>
      <p className={typographyTokens.label}>{label}</p>
      <p className={typographyTokens.metric}>{value}</p>
      {helper ? <p className={typographyTokens.caption}>{helper}</p> : null}
    </Card>
  )
}

export default React.memo(StatCard)
