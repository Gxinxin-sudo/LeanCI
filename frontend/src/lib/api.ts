import type { AnalysisResult, ApiErrorEnvelope } from '../types/api'

const configuredApiBase = import.meta.env.VITE_API_BASE_URL ?? '/api'
const API_BASE_URL = configuredApiBase.replace(/\/$/, '')

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (typeof value !== 'object' || value === null || !('error' in value)) {
    return false
  }

  const error = value.error
  return (
    typeof error === 'object' &&
    error !== null &&
    'message' in error &&
    typeof error.message === 'string'
  )
}

export async function analyzeLog(logText: string): Promise<AnalysisResult> {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ log_text: logText }),
  })

  if (!response.ok) {
    let message = 'The analysis request failed. Check that the API is running.'

    try {
      const payload: unknown = await response.json()
      if (isApiErrorEnvelope(payload)) {
        message = payload.error.message
      }
    } catch {
      // Keep the safe public fallback when the response is not JSON.
    }

    throw new Error(message)
  }

  return (await response.json()) as AnalysisResult
}
