import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App, MAX_LOG_CHARACTERS } from './App'
import { mockAnalysis } from './test/mockAnalysis'
import type { CapturedSampleResult, HealthResponse, SamplePayload } from './types/api'

const healthy: HealthResponse = {
  status: 'ok',
  service: 'leanci-api',
  mode: 'paritok',
  paritok_connected: true,
  hosted_gpu_available: true,
  proxy_version: '1.2.7',
  model: 'deepseek-v4-flash',
  deepseek_called: false,
  message: 'Local Paritok Proxy and hosted GPU are available.',
}

const sample: SamplePayload = {
  id: 'python-pytest',
  title: 'Python pytest failure',
  category: 'Python',
  description: 'A deterministic retry failure.',
  log_bytes: 71_000,
  file_count: 2,
  log_text: 'FAILED tests/test_retry.py::test_retry_backoff_caps_at_maximum\nassert 15 == 16',
  files: [
    { name: 'retry.py', content: 'return min(base * 2**attempt - 1, maximum)' },
    { name: 'test_retry.py', content: 'assert policy.delay_for(4) == 16' },
  ],
}

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  window.history.replaceState({}, '', '/')
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('LeanCI workbench', () => {
  it('explains the value and exposes all three one-click samples', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(healthy)))
    render(<App />)

    expect(screen.getByText('Keep the failure.')).toBeInTheDocument()
    expect(screen.getByText('Cut the noise.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Python pytest failure/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /TypeScript build failure/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Docker build failure/i })).toBeInTheDocument()
    expect(screen.getByText('No code execution · No API keys shown')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Paste CI failure log' })).toHaveAttribute(
      'maxlength',
      String(MAX_LOG_CHARACTERS),
    )
    expect(await screen.findByText('Online')).toBeInTheDocument()
  })

  it('loads a complete bundled sample with one click', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        return Promise.resolve(url.endsWith('/health') ? jsonResponse(healthy) : jsonResponse(sample))
      }),
    )
    render(<App />)

    await user.click(screen.getByRole('button', { name: /Python pytest failure/i }))

    const textarea = screen.getByRole<HTMLTextAreaElement>('textbox', {
      name: 'Paste CI failure log',
    })
    expect(textarea.value).toContain('assert 15 == 16')
    expect(screen.getByText('retry.py')).toBeInTheDocument()
    expect(screen.getByText(/Python pytest failure loaded/)).toBeInTheDocument()
  })

  it('moves through loading into the complete result and real-token labels', async () => {
    const user = userEvent.setup()
    let resolveAnalysis: ((value: Response) => void) | undefined
    const analysisRequest = new Promise<Response>((resolve) => {
      resolveAnalysis = resolve
    })
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/health')) return Promise.resolve(jsonResponse(healthy))
        if (url.includes('/samples/')) return Promise.resolve(jsonResponse(sample))
        return analysisRequest
      }),
    )

    render(<App />)
    await user.click(screen.getByRole('button', { name: /Python pytest failure/i }))
    await user.click(screen.getByRole('button', { name: /Analyze failure/i }))

    expect(screen.getByText('Compressing context, then tracing evidence…')).toBeInTheDocument()

    resolveAnalysis?.(jsonResponse(mockAnalysis))

    expect(await screen.findByText(mockAnalysis.summary)).toBeInTheDocument()
    expect(screen.getByText(mockAnalysis.root_cause)).toBeInTheDocument()
    expect(screen.getByText('94%')).toBeInTheDocument()
    expect(screen.getByText('Tokens Saved')).toBeInTheDocument()
    expect(screen.getByText('6,000')).toBeInTheDocument()
    expect(screen.getByText('Estimated DeepSeek Input Cost Saved')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copy Patch' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Download Report' })).toBeInTheDocument()
  })

  it('loads a saved real-run capture directly for recording', async () => {
    const capture: CapturedSampleResult = {
      schema_version: 1,
      sample_id: 'python-pytest',
      captured_at: '2026-07-25T19:19:15.086253+00:00',
      capture_kind: 'real_paritok_stats_delta',
      analysis_result: mockAnalysis,
    }
    window.history.replaceState({}, '', '/?capture=python-pytest')
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/health')) return Promise.resolve(jsonResponse(healthy))
        if (url.includes('/captures/')) return Promise.resolve(jsonResponse(capture))
        return Promise.resolve(jsonResponse(sample))
      }),
    )

    render(<App />)

    expect(await screen.findByText('Saved real Paritok run')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'python-pytest' })).toBeInTheDocument()
    expect(screen.getByText(mockAnalysis.summary)).toBeInTheDocument()
    expect(screen.getByText('Tokens Saved')).toBeInTheDocument()
    expect(screen.getByText('6,000')).toBeInTheDocument()
  })

  it('shows a specific route error and allows retry', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/health')) return Promise.resolve(jsonResponse(healthy))
        return Promise.reject(new Error('Network unavailable.'))
      }),
    )

    render(<App />)
    await user.type(
      screen.getByRole('textbox', { name: 'Paste CI failure log' }),
      'pytest failed',
    )
    await user.click(screen.getByRole('button', { name: /Analyze failure/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'LeanCI API is unreachable. Start FastAPI on port 8000, then retry.',
      )
    })
    expect(screen.getByRole('button', { name: 'Retry analysis' })).toBeInTheDocument()
  })

  it('rejects an empty log before making an analysis request', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(healthy))
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await user.click(screen.getByRole('button', { name: /Analyze failure/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Paste a CI log or load one of the three samples before analyzing.',
    )
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('rejects archives during client-side upload validation', async () => {
    const user = userEvent.setup({ applyAccept: false })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(healthy)))
    render(<App />)

    const input = screen.getByLabelText('Add text files')
    await user.upload(input, new File(['not an archive'], 'context.zip'))

    expect(
      await screen.findByText(/only allowlisted source, config, log, and documentation/i),
    ).toBeInTheDocument()
    expect(screen.queryByText('context.zip', { selector: 'strong' })).not.toBeInTheDocument()
  })
})
