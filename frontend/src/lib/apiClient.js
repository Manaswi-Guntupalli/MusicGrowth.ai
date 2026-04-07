const API_BASE = '/api'

const RETRYABLE_STATUS_CODES = new Set([408, 425, 429, 500, 502, 503, 504])

export class ApiRequestError extends Error {
  constructor(message, options = {}) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = options.status ?? null
    this.code = options.code || 'UNKNOWN_ERROR'
    this.detail = options.detail ?? null
    this.retryable = Boolean(options.retryable)
    this.cause = options.cause
  }
}

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function normalizeHttpErrorMessage(status, detail) {
  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim()
  }

  switch (status) {
    case 400:
      return 'The request could not be processed. Please review your input and try again.'
    case 401:
      return 'Session expired. Please sign in again.'
    case 403:
      return 'You are not authorized to perform this action.'
    case 404:
      return 'Requested resource was not found.'
    case 413:
      return 'Upload is too large. Please choose a smaller file.'
    case 415:
      return 'Unsupported media format. Please upload a supported file type.'
    case 429:
      return 'Too many requests. Please wait a moment and retry.'
    default:
      if (status >= 500) {
        return 'Server temporarily unavailable. Please try again shortly.'
      }
      return 'Request failed. Please try again.'
  }
}

function toApiRequestError(error, timedOut) {
  if (error instanceof ApiRequestError) {
    return error
  }

  if (timedOut || error?.name === 'AbortError') {
    return new ApiRequestError('Request timed out. Please try again.', {
      code: 'TIMEOUT',
      retryable: true,
      cause: error,
    })
  }

  return new ApiRequestError('Network error. Please check your connection and try again.', {
    code: 'NETWORK_ERROR',
    retryable: true,
    cause: error,
  })
}

function shouldRetry(error, attempt, maxRetries) {
  if (attempt >= maxRetries) {
    return false
  }
  return Boolean(error?.retryable)
}

export async function requestJson(path, options = {}) {
  const method = String(options.method || 'GET').toUpperCase()
  const timeoutMs = Number.isFinite(options.timeoutMs) ? Number(options.timeoutMs) : 12000
  const retryDelayMs = Number.isFinite(options.retryDelayMs) ? Number(options.retryDelayMs) : 350
  const retries = Number.isFinite(options.retries)
    ? Number(options.retries)
    : method === 'GET'
      ? 1
      : 0

  let attempt = 0
  while (true) {
    const controller = new AbortController()
    let didTimeout = false
    const timeoutId = setTimeout(() => {
      didTimeout = true
      controller.abort()
    }, timeoutMs)

    try {
      const headers = { ...(options.headers || {}) }
      if (options.token) {
        headers.Authorization = `Bearer ${options.token}`
      }

      const body = options.body
      const hasFormDataBody = typeof FormData !== 'undefined' && body instanceof FormData
      if (body != null && !hasFormDataBody && !('Content-Type' in headers) && !('content-type' in headers)) {
        headers['Content-Type'] = 'application/json'
      }

      let payload = body
      if (body != null && !hasFormDataBody && typeof body === 'object') {
        payload = JSON.stringify(body)
      }

      const response = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: payload,
        credentials: options.credentials || 'same-origin',
        signal: controller.signal,
      })

      const contentType = response.headers.get('content-type') || ''
      const isJson = contentType.includes('application/json')
      const parsed = isJson
        ? await response.json().catch(() => null)
        : await response.text().catch(() => '')

      if (!response.ok) {
        const detail = parsed && typeof parsed === 'object' ? parsed.detail : parsed
        throw new ApiRequestError(normalizeHttpErrorMessage(response.status, detail), {
          status: response.status,
          code: `HTTP_${response.status}`,
          detail,
          retryable: RETRYABLE_STATUS_CODES.has(response.status),
        })
      }

      return parsed
    } catch (error) {
      const normalized = toApiRequestError(error, didTimeout)
      if (shouldRetry(normalized, attempt, retries)) {
        attempt += 1
        await delay(retryDelayMs * attempt)
        continue
      }
      throw normalized
    } finally {
      clearTimeout(timeoutId)
    }
  }
}
