import { motion } from 'framer-motion'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { typographyTokens } from '../theme/tokens'

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: (index) => ({
    opacity: 1,
    y: 0,
    transition: { delay: index * 0.07, duration: 0.3 },
  }),
}

export default function HistoryPage({ history, onViewAnalysis, error, onRetry, loading }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="space-y-6"
    >
      <section className="space-y-1">
        <h2 className={typographyTokens.sectionHeader}>Your Analysis History</h2>
        <p className={typographyTokens.caption}>View and compare all your previous analyses</p>
      </section>

      {error ? (
        <Card className="space-y-3">
          <p className="text-[13px] text-danger">{error}</p>
          <Button className="h-8 text-sm" onClick={onRetry}>Retry</Button>
        </Card>
      ) : null}

      <div className="space-y-3" aria-busy={loading ? 'true' : 'false'}>
        {loading ? (
          <>
            {[1, 2, 3].map((idx) => (
              <div key={idx} className="skeleton-blob min-h-[112px] p-5">
                <div className="grid gap-3 md:grid-cols-[1fr_220px_140px] md:items-center">
                  <div className="space-y-2">
                    <div className="skeleton-line h-5 w-2/5" />
                    <div className="skeleton-line h-4 w-1/3" />
                  </div>
                  <div className="space-y-2">
                    <div className="skeleton-line h-4 w-full" />
                    <div className="skeleton-line h-4 w-3/5" />
                  </div>
                  <div className="skeleton-line h-8 w-full" />
                </div>
              </div>
            ))}
          </>
        ) : history.length === 0 ? (
          <Card className="text-center">
            <p className="text-[14px] text-text-secondary">No analyses yet. Upload your first song to get started.</p>
          </Card>
        ) : (
          history.map((analysis, index) => (
            <motion.div
              key={analysis.id}
              custom={index}
              variants={itemVariants}
              initial="hidden"
              animate="visible"
              whileHover={{ scale: 1.01, transition: { duration: 0.15 } }}
            >
              <Card className="p-5">
                <div className="grid gap-4 md:grid-cols-[1fr_220px_220px] md:items-center">
                  <div>
                    <h3 className={typographyTokens.cardHeader}>{analysis.filename}</h3>
                    <p className="mt-1 text-[13px] text-text-muted">
                      {new Date(analysis.created_at).toLocaleDateString()} at {new Date(analysis.created_at).toLocaleTimeString()}
                    </p>
                  </div>

                  <div>
                    <p className="text-[13px] text-accent">{analysis.result?.style_cluster?.label || 'Unknown Cluster'}</p>
                    <p className="mt-1 text-[12px] text-text-muted">
                      {analysis.result?.style_cluster?.confidence?.toFixed(1) || '?'}% confidence
                    </p>
                  </div>

                  <div className="flex items-center justify-start gap-2 md:justify-end">
                    <Badge variant="subtle">{analysis.result?.sound_dna?.mood || 'Unknown'}</Badge>
                    <Badge variant="subtle">{analysis.result?.sound_dna?.production_style || 'Unknown'}</Badge>
                    <Button className="h-8 px-3 text-sm" onClick={() => onViewAnalysis(analysis)}>
                      View Details
                    </Button>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))
        )}
      </div>
    </motion.div>
  )
}
