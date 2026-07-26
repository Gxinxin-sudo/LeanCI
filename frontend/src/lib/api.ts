import type {
  AnalysisResult,
  ApiErrorEnvelope,
  BenchmarkArtifact,
  CapturedSampleResult,
  HealthResponse,
  SamplePayload,
  UploadedTextFile,
} from '../types/api'

const configuredApiBase = import.meta.env.VITE_API_BASE_URL ?? '/api'
const API_BASE_URL = configuredApiBase.replace(/\/$/, '')
const DEFAULT_REQUEST_TIMEOUT_MS = 15_000
const ANALYSIS_REQUEST_TIMEOUT_MS = 115_000

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

async function requestJson<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
): Promise<T> {
  let response: Response
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error(
        `LeanCI API timed out after ${Math.round(timeoutMs / 1000)} seconds. No result was accepted; check the route status and retry.`,
        { cause: error },
      )
    }
    throw new Error(
      'LeanCI API is unreachable. Start FastAPI on port 8000, then retry.',
      { cause: error },
    )
  } finally {
    window.clearTimeout(timeoutId)
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

export function getBenchmarkResults(): Promise<BenchmarkArtifact> {
  return requestJson<BenchmarkArtifact>('/benchmark/results')
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
  }, ANALYSIS_REQUEST_TIMEOUT_MS)
}
