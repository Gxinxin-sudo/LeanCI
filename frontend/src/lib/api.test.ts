import { afterEach, describe, expect, it, vi } from 'vitest'

import { analyzeLog, getHealth } from './api'

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('API timeouts', () => {
  it('aborts a stalled analysis before the 120 second command ceiling', async () => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'fetch',
      vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => {
            reject(new DOMException('aborted', 'AbortError'))
          })
        })
      }),
    )

    const request = analyzeLog('failed', [])
    const rejection = expect(request).rejects.toThrow(
      'LeanCI API timed out after 115 seconds. No result was accepted',
    )
    await vi.advanceTimersByTimeAsync(115_000)
    await rejection
  })
})

describe('health API', () => {
  it('preserves the structured component status when the local Proxy is disconnected', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            status: 'degraded',
            service: 'leanci-api',
            mode: 'paritok',
            paritok_connected: false,
            hosted_gpu_available: false,
            proxy_version: null,
            model: 'deepseek-v4-flash',
            deepseek_called: false,
            message: 'The local Paritok Proxy is unavailable.',
          }),
          {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      ),
    )

    await expect(getHealth()).resolves.toMatchObject({
      status: 'degraded',
      paritok_connected: false,
      hosted_gpu_available: false,
    })
  })
})
