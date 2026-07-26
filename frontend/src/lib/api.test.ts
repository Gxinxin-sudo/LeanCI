import { afterEach, describe, expect, it, vi } from 'vitest'

import { analyzeLog } from './api'

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
