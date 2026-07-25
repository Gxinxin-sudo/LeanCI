import type {
  AnalysisResult,
  ApiErrorEnvelope,
  CapturedSampleResult,
  HealthResponse,
  SamplePayload,
  UploadedTextFile,
} from '../types/api'

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

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch {
    throw new Error(
      'LeanCI API is unreachable. Start FastAPI on port 8000, then retry.',
    )
  }

  if (!response.ok) {
    let message = `LeanCI API returned HTTP ${response.status}.`

    try {
      const payload: unknown = await response.json()
      if (isApiErrorEnvelope(payload)) {
        message = `${payload.error.message} Request ID: ${payload.error.request_id}`
      }
    } catch {
      message = `LeanCI API returned HTTP ${response.status} without a public JSON error.`
    }

    throw new Error(message)
  }

  return (await response.json()) as T
}

export function getHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>('/health')
}

export function getSample(sampleId: string): Promise<SamplePayload> {
  return requestJson<SamplePayload>(`/samples/${encodeURIComponent(sampleId)}`)
}

export function getSampleCapture(sampleId: string): Promise<CapturedSampleResult> {
  return requestJson<CapturedSampleResult>(`/captures/${encodeURIComponent(sampleId)}`)
}

export function analyzeLog(
  logText: string,
  files: UploadedTextFile[],
): Promise<AnalysisResult> {
  return requestJson<AnalysisResult>('/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ log_text: logText, files }),
  })
}
