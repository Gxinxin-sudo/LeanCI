import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { reportMarkdown } from '../lib/report'
import { mockAnalysis } from '../test/mockAnalysis'
import { ResultsPanel } from './ResultsPanel'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('safe report actions', () => {
  it('renders a model patch as text and never creates attacker-controlled elements', () => {
    const malicious = {
      ...mockAnalysis,
      patch: '```\\n<img src=x onerror=alert(1)>\\n<script>run()</script>',
    }

    const { container } = render(
      <ResultsPanel state={{ status: 'success', data: malicious }} onRetry={() => undefined} />,
    )

    expect(screen.getByText(malicious.patch)).toBeInTheDocument()
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('script')).toBeNull()
  })

  it('builds markdown with escaped prose and a non-breakable patch fence', () => {
    const malicious = {
      ...mockAnalysis,
      summary: '<img src="https://attacker.example/a.png"> [click](javascript:alert(1))',
      patch: '```\\n<script>run()</script>',
    }

    const report = reportMarkdown(malicious)

    expect(report).toContain('&lt;img src="https://attacker\\.example/a\\.png"&gt;')
    expect(report).not.toContain('<img src="https://attacker.example/a.png">')
    expect(report).toContain('````diff')
    expect(report).toContain('````')
    expect(report).toContain('Patches and')
    expect(report).toContain('commands in this report are untrusted, inert text')
  })

  it('copies the exact patch and downloads a generated report', async () => {
    const user = userEvent.setup()
    const writeText = vi.fn().mockResolvedValue(undefined)
    const createObjectURL = vi.fn().mockReturnValue('blob:leanci-report')
    const revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    const clipboardDescriptor = Object.getOwnPropertyDescriptor(navigator, 'clipboard')
    const createDescriptor = Object.getOwnPropertyDescriptor(URL, 'createObjectURL')
    const revokeDescriptor = Object.getOwnPropertyDescriptor(URL, 'revokeObjectURL')
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectURL,
    })
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectURL,
    })

    try {
      render(
        <ResultsPanel
          state={{ status: 'success', data: mockAnalysis }}
          onRetry={() => undefined}
        />,
      )

      await user.click(screen.getByRole('button', { name: 'Copy Patch' }))
      expect(writeText).toHaveBeenCalledWith(mockAnalysis.patch)
      expect(await screen.findByText('Patch copied')).toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: 'Download Report' }))
      expect(createObjectURL).toHaveBeenCalledOnce()
      expect(createObjectURL.mock.lastCall?.[0]).toBeInstanceOf(Blob)
      expect(click).toHaveBeenCalledOnce()
      expect(screen.getByText('Report downloaded')).toBeInTheDocument()
      await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith('blob:leanci-report'))
    } finally {
      if (clipboardDescriptor) {
        Object.defineProperty(navigator, 'clipboard', clipboardDescriptor)
      } else {
        Reflect.deleteProperty(navigator, 'clipboard')
      }
      if (createDescriptor) {
        Object.defineProperty(URL, 'createObjectURL', createDescriptor)
      } else {
        Reflect.deleteProperty(URL, 'createObjectURL')
      }
      if (revokeDescriptor) {
        Object.defineProperty(URL, 'revokeObjectURL', revokeDescriptor)
      } else {
        Reflect.deleteProperty(URL, 'revokeObjectURL')
      }
    }
  })
})
