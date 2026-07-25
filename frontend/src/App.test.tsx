import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App, MAX_LOG_CHARACTERS } from './App'
import { mockAnalysis } from './test/mockAnalysis'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('LeanCI workbench', () => {
  it('shows the empty and disconnected demo state', () => {
    render(<App />)

    expect(screen.getAllByText('Demo data — Paritok not connected')).toHaveLength(2)
    expect(screen.getByText('Your diagnosis will assemble here.')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Paste CI failure log' })).toHaveAttribute(
      'maxlength',
      String(MAX_LOG_CHARACTERS),
    )
  })

  it('loads a bounded sample log', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: /load sample/i }))

    const textarea = screen.getByRole<HTMLTextAreaElement>('textbox', {
      name: 'Paste CI failure log',
    })
    expect(textarea.value).toContain('error TS2345')
  })

  it('moves through loading into the complete success result', async () => {
    const user = userEvent.setup()
    let resolveRequest: ((value: Response) => void) | undefined
    const request = new Promise<Response>((resolve) => {
      resolveRequest = resolve
    })
    vi.stubGlobal('fetch', vi.fn(() => request))

    render(<App />)
    await user.click(screen.getByRole('button', { name: /load sample/i }))
    await user.click(screen.getByRole('button', { name: /analyze failure/i }))

    expect(screen.getByText('Tracing the failure signal…')).toBeInTheDocument()

    resolveRequest?.(
      new Response(JSON.stringify(mockAnalysis), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    expect(await screen.findByText(mockAnalysis.summary)).toBeInTheDocument()
    expect(screen.getByText(mockAnalysis.root_cause)).toBeInTheDocument()
    expect(screen.getByText('94%')).toBeInTheDocument()
    expect(screen.getByText('No token counts are estimated or generated in demo mode.')).toBeInTheDocument()
  })

  it('shows a useful error state when the API is unavailable', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network unavailable.')))

    render(<App />)
    await user.click(screen.getByRole('button', { name: /load sample/i }))
    await user.click(screen.getByRole('button', { name: /analyze failure/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Network unavailable.')
    })
  })

  it('rejects an empty log before making a request', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await user.click(screen.getByRole('button', { name: /analyze failure/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Paste a CI log or load the sample before starting analysis.',
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
