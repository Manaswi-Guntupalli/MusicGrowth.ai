import { useState } from 'react'
import { motion } from 'framer-motion'
import { requestJson } from '../lib/apiClient'

export default function UploadPage({ token, onAnalysisComplete, onAnalysisStateChange, theme = 'dark' }) {
  const [file, setFile] = useState(null)
  const [segmentMode, setSegmentMode] = useState('best')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [spokenWordWarning, setSpokenWordWarning] = useState('')

  function isSpokenWordGuardrailError(err) {
    const rawMessage = String(err?.message || '').trim()
    return /SPOKEN_WORD_DETECTED/i.test(rawMessage)
  }

  function toSpokenWordGuardrailMessage(err) {
    const rawMessage = String(err?.message || '').trim()
    const normalized = rawMessage.replace(/^SPOKEN_WORD_DETECTED:\s*/i, '').trim()
    return normalized || 'This audio appears to be spoken-word heavy. Music analysis may be unreliable for this upload.'
  }

  function toUploadErrorMessage(err) {
    const rawMessage = String(err?.message || '').trim()
    const status = Number(err?.status || 0)
    const code = String(err?.code || '')

    if (status === 413) {
      return 'File is too large. Please upload a track under 25 MB or increase the upload limit in settings.'
    }

    if (status === 415 || /unsupported file type|unsupported media format/i.test(rawMessage)) {
      return 'Unsupported format. Please upload MP3, WAV, FLAC, M4A, or OGG audio.'
    }

    if (status === 400 && /corrupted|could not be parsed|unsupported/i.test(rawMessage)) {
      return 'The file could not be decoded. Re-export it as MP3 or WAV and try again.'
    }

    if (/empty|silent|valid music audio|audio file appears empty/i.test(rawMessage)) {
      return 'Please upload a valid music audio file that contains audible content.'
    }

    if (code === 'TIMEOUT') {
      return 'Upload timed out. Check your connection and try a smaller file.'
    }

    if (code === 'NETWORK_ERROR') {
      return 'Network issue detected. Verify internet/backend connection and try again.'
    }

    return rawMessage || 'Could not analyze this file. Please try again.'
  }

  async function runAnalyze(allowSpokenWord = false) {
    if (!file) return

    setLoading(true)
    setError('')
    if (!allowSpokenWord) {
      setSpokenWordWarning('')
    }
    onAnalysisStateChange?.(true)

    const form = new FormData()
    form.append('file', file)

    try {
      const data = await requestJson(`/analyze?segment_mode=${segmentMode}&allow_spoken_word=${allowSpokenWord ? 'true' : 'false'}`, {
        method: 'POST',
        body: form,
        token,
        timeoutMs: 90000,
        retries: 0,
      })
      setSpokenWordWarning('')
      onAnalysisComplete(data)
    } catch (err) {
      if (isSpokenWordGuardrailError(err)) {
        setSpokenWordWarning(toSpokenWordGuardrailMessage(err))
      } else {
        setError(toUploadErrorMessage(err))
      }
    } finally {
      setLoading(false)
      onAnalysisStateChange?.(false)
    }
  }

  async function handleAnalyze(e) {
    e.preventDefault()
    if (!file) {
      setError('Please upload an audio file first.')
      return
    }

    await runAnalyze(false)
  }

  async function handleContinueAnyway() {
    if (!file || loading) return
    await runAnalyze(true)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="max-w-[900px]"
    >
      <h1 className={`mb-1 text-[28px] font-semibold ${theme === 'dark' ? 'text-white' : 'text-[#111827]'}`}>Upload Your Track</h1>
      <p className={`mb-8 text-[14px] ${theme === 'dark' ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>
        Analyze your music and discover your unique sound signature
      </p>

      <form onSubmit={handleAnalyze} className="space-y-6">
        <label className="block cursor-pointer">
          <div className={`mb-6 flex min-h-[200px] flex-col items-center justify-center rounded-xl border-2 border-dashed p-16 text-center transition-colors hover:border-[#6C5CE7]/50 ${theme === 'dark' ? 'border-white/10 bg-[#111827]' : 'border-[#CBD5E1] bg-white'}`}>
            <p className={`text-[14px] ${theme === 'dark' ? 'text-[#9CA3AF]' : 'text-[#4B5563]'}`}>{file ? file.name : 'Drag & drop or click to select a file'}</p>
            <p className={`mt-2 text-[12px] ${theme === 'dark' ? 'text-[#5B6278]' : 'text-[#6B7280]'}`}>Supported: MP3, WAV, FLAC, M4A, OGG</p>
          </div>
          <input
            type="file"
            accept=".mp3,.wav,.m4a,.flac,.ogg"
            onChange={(e) => {
              setFile(e.target.files?.[0] || null)
              setError('')
              setSpokenWordWarning('')
            }}
            className="hidden"
          />
        </label>

        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className={`flex cursor-pointer flex-col gap-1 rounded-xl border p-4 has-[:checked]:border-[#6C5CE7]/50 has-[:checked]:bg-[#6C5CE7]/5 ${theme === 'dark' ? 'border-white/10 bg-[#111827]' : 'border-[#CBD5E1] bg-white'}`}>
            <input
              type="radio"
              name="segment"
              value="best"
              checked={segmentMode === 'best'}
              onChange={(e) => setSegmentMode(e.target.value)}
              className="sr-only"
            />
            <span className={`text-[15px] font-medium ${theme === 'dark' ? 'text-white' : 'text-[#111827]'}`}>Best 30s Segment</span>
            <span className={`text-[13px] ${theme === 'dark' ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>Analyzes the most energetic part</span>
          </label>

          <label className={`flex cursor-pointer flex-col gap-1 rounded-xl border p-4 has-[:checked]:border-[#6C5CE7]/50 has-[:checked]:bg-[#6C5CE7]/5 ${theme === 'dark' ? 'border-white/10 bg-[#111827]' : 'border-[#CBD5E1] bg-white'}`}>
            <input
              type="radio"
              name="segment"
              value="full"
              checked={segmentMode === 'full'}
              onChange={(e) => setSegmentMode(e.target.value)}
              className="sr-only"
            />
            <span className={`text-[15px] font-medium ${theme === 'dark' ? 'text-white' : 'text-[#111827]'}`}>Full Audio</span>
            <span className={`text-[13px] ${theme === 'dark' ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>Analyzes the entire track</span>
          </label>
        </div>

        <button
          type="submit"
          disabled={loading || !file}
          className="h-12 w-full rounded-xl bg-gradient-to-r from-[#6C5CE7] to-[#00CEC9] text-[15px] font-medium text-white transition-all hover:opacity-90 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? 'Analyzing your sound...' : 'Analyze My Sound'}
        </button>

        {spokenWordWarning ? (
          <div className={`rounded-xl border p-4 ${theme === 'dark' ? 'border-amber-500/40 bg-amber-500/10' : 'border-amber-400/60 bg-amber-50'}`}>
            <p className={`text-[13px] ${theme === 'dark' ? 'text-amber-200' : 'text-amber-800'}`}>
              {spokenWordWarning}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={handleContinueAnyway}
                disabled={loading}
                className="h-9 rounded-lg bg-gradient-to-r from-[#F59E0B] to-[#F97316] px-4 text-[13px] font-medium text-white transition-all hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Continue Anyway
              </button>
              <button
                type="button"
                onClick={() => setSpokenWordWarning('')}
                disabled={loading}
                className={`h-9 rounded-lg border px-4 text-[13px] transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${theme === 'dark' ? 'border-white/20 text-[#D1D5DB] hover:bg-white/5' : 'border-[#CBD5E1] text-[#4B5563] hover:bg-[#F3F4F6]'}`}
              >
                Choose Another Audio
              </button>
            </div>
          </div>
        ) : null}

        {error ? <p className="text-[13px] text-[#E17055]">{error}</p> : null}
      </form>
    </motion.div>
  )
}
