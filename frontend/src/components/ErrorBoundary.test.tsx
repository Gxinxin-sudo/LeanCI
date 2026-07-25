import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ErrorBoundary } from './ErrorBoundary'

function BrokenComponent(): never {
  throw new Error('render failure')
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders a recovery action when a child fails', () => {
    render(
      <ErrorBoundary>
        <BrokenComponent />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('The workbench could not render.')
    expect(screen.getByRole('button', { name: 'Reload workbench' })).toBeInTheDocument()
  })
})
