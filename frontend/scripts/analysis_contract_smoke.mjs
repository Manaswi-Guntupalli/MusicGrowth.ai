import fs from 'node:fs'
import path from 'node:path'

const requiredSoundDna = [
  'tempo',
  'energy',
  'danceability',
  'valence',
  'acousticness',
  'instrumentalness',
  'speechiness',
  'loudness',
  'liveness',
  'mfcc_mean_1',
  'mfcc_mean_2',
  'mfcc_mean_3',
  'mfcc_mean_4',
  'mfcc_mean_5',
  'production_style',
  'mood',
]

function defaultSample() {
  return {
    sound_dna: {
      tempo: 126.0,
      energy: 0.73,
      danceability: 0.68,
      valence: 0.44,
      acousticness: 0.18,
      instrumentalness: 0.12,
      speechiness: 0.07,
      loudness: -7.9,
      liveness: 0.2,
      mfcc_mean_1: -20.2,
      mfcc_mean_2: 9.7,
      mfcc_mean_3: 2.1,
      mfcc_mean_4: 6.4,
      mfcc_mean_5: -2.8,
      production_style: 'Balanced indie',
      mood: 'Reflective / balanced',
    },
    style_cluster: {
      cluster_id: 1,
      label: 'Balanced Indie - Mid Tempo / Synth Tilt / Neutral',
      confidence: 64.2,
      raw_confidence: 72.3,
    },
    top_similar: [
      { artist: 'Artist A', song: 'Track A', cluster: 'Balanced Indie', similarity: 82.1 },
    ],
    differences: [
      {
        feature: 'energy',
        tag: 'KEY_DIFFERENTIATOR',
        song_value: 0.73,
        reference_mean: 0.66,
        delta_percent: 7.0,
        interpretation: 'Higher than reference mean',
      },
    ],
    market_gaps: ['Moderate opportunity in current cluster.'],
    paths: [
      {
        id: 'A',
        title: 'Mainstream Acceleration',
        strategy: 'Move closer to high-discoverability profiles.',
        expected: 'Faster pickup.',
        tradeoff: 'Higher competition.',
        actions: ['Tighten hooks', 'Increase energy'],
      },
    ],
  }
}

function loadInput() {
  const samplePath = process.argv[2] || process.env.ANALYSIS_CONTRACT_SAMPLE
  if (!samplePath) {
    return defaultSample()
  }

  const resolved = path.resolve(samplePath)
  const raw = fs.readFileSync(resolved, 'utf-8')
  return JSON.parse(raw)
}

function validate(payload) {
  const errors = []

  if (!payload || typeof payload !== 'object') {
    errors.push('Payload must be an object')
    return errors
  }

  if (!payload.sound_dna || typeof payload.sound_dna !== 'object') {
    errors.push('Missing sound_dna object')
  } else {
    for (const key of requiredSoundDna) {
      if (!(key in payload.sound_dna)) {
        errors.push(`sound_dna missing key: ${key}`)
      }
    }
  }

  if (!payload.style_cluster || typeof payload.style_cluster !== 'object') {
    errors.push('Missing style_cluster object')
  } else {
    for (const key of ['cluster_id', 'label', 'confidence', 'raw_confidence']) {
      if (!(key in payload.style_cluster)) {
        errors.push(`style_cluster missing key: ${key}`)
      }
    }
  }

  if (!Array.isArray(payload.top_similar)) {
    errors.push('top_similar must be an array')
  } else if (payload.top_similar.length > 0) {
    for (const key of ['artist', 'song', 'cluster', 'similarity']) {
      if (!(key in payload.top_similar[0])) {
        errors.push(`top_similar[0] missing key: ${key}`)
      }
    }
  }

  if (!Array.isArray(payload.differences)) {
    errors.push('differences must be an array')
  } else if (payload.differences.length > 0) {
    for (const key of ['feature', 'tag', 'song_value', 'reference_mean', 'delta_percent', 'interpretation']) {
      if (!(key in payload.differences[0])) {
        errors.push(`differences[0] missing key: ${key}`)
      }
    }
  }

  if (!Array.isArray(payload.market_gaps)) {
    errors.push('market_gaps must be an array')
  }

  if (!Array.isArray(payload.paths)) {
    errors.push('paths must be an array')
  } else if (payload.paths.length > 0) {
    for (const key of ['id', 'title', 'strategy', 'expected', 'tradeoff', 'actions']) {
      if (!(key in payload.paths[0])) {
        errors.push(`paths[0] missing key: ${key}`)
      }
    }
  }

  return errors
}

function main() {
  const payload = loadInput()
  const errors = validate(payload)

  if (errors.length > 0) {
    console.error('Analysis contract smoke FAILED')
    for (const err of errors) {
      console.error(`- ${err}`)
    }
    process.exit(1)
  }

  console.log('Analysis contract smoke PASSED')
}

main()
