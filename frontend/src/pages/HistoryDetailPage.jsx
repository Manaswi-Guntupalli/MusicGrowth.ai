import AnalysisPage from './AnalysisPage'
import { motion } from 'framer-motion'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { typographyTokens } from '../theme/tokens'

export default function HistoryDetailPage({ analysis, onBack, theme, token }) {
  const createdAt = analysis?.created_at ? new Date(analysis.created_at) : null

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="space-y-6"
    >
      <Card className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className={typographyTokens.sectionHeader}>History Details</h2>
          <p className="mt-1 text-[13px] text-text-secondary">
            {analysis?.filename || 'Selected analysis'}
            {createdAt ? ` | ${createdAt.toLocaleDateString()} ${createdAt.toLocaleTimeString()}` : ''}
          </p>
        </div>
        <Button className="h-8 text-sm" onClick={onBack}>Back to History</Button>
      </Card>

      <AnalysisPage result={analysis?.result} theme={theme} token={token} />
    </motion.div>
  )
}