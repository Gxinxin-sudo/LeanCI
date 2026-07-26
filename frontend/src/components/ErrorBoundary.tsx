import { Component, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = { hasError: false }

  public static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  public render(): ReactNode {
    if (this.state.hasError) {
      return (
        <main className="grid min-h-screen place-items-center bg-ink px-6 text-fog">
          <section
            className="w-full max-w-xl border border-line bg-panel p-8 shadow-workbench"
            role="alert"
          >
            <p className="font-mono text-xs uppercase tracking-[0.24em] text-fault">
              Interface halted
            </p>
            <h1 className="mt-4 font-display text-3xl font-semibold text-white">
              The workbench could not render.
            </h1>
            <p className="mt-3 max-w-md text-sm leading-6 text-muted">
              Reload the page. If the problem continues, record the browser version and the
              last action, then report the issue without including CI logs or secrets.
            </p>
            <button
              className="mt-6 border border-signal bg-signal px-4 py-2 font-mono text-xs font-bold uppercase tracking-[0.14em] text-ink focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-signal"
              type="button"
              onClick={() => window.location.reload()}
            >
              Reload workbench
            </button>
          </section>
        </main>
      )
    }

    return this.props.children
  }
}
