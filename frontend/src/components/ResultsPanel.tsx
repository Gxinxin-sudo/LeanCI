import type { AnalysisResult } from '../types/api'

interface ResultsPanelProps {
  state:
    | { status: 'idle' }
    | { status: 'loading' }
    | { status: 'success'; data: AnalysisResult }
    | { status: 'error'; message: string }
}

function locationLabel(source: string, lineStart: number | null, lineEnd: number | null) {
  if (lineStart === null) {
    return source
  }
  return lineEnd && lineEnd !== lineStart
    ? `${source}:${lineStart}–${lineEnd}`
    : `${source}:${lineStart}`
}

function LoadingState() {
  return (
    <section
      className="min-h-[34rem] border border-line bg-panel p-6"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="flex items-center gap-3">
        <span className="loading-mark" aria-hidden="true" />
        <div>
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.22em] text-signal">
            Mock analysis running
          </p>
          <h2 className="mt-1 font-display text-xl font-semibold text-white">
            Tracing the failure signal…
          </h2>
        </div>
      </div>
      <div className="mt-8 space-y-3">
        <div className="skeleton-line w-2/5" />
        <div className="skeleton-line w-full" />
        <div className="skeleton-line w-4/5" />
      </div>
      <div className="mt-10 grid gap-3 sm:grid-cols-2">
        <div className="skeleton-block" />
        <div className="skeleton-block" />
      </div>
    </section>
  )
}

function EmptyState() {
  return (
    <section className="empty-grid grid min-h-[34rem] place-items-center border border-line bg-panel px-6 py-14">
      <div className="max-w-md text-center">
        <div className="mx-auto grid h-14 w-14 place-items-center border border-line-bright bg-ink">
          <svg aria-hidden="true" className="h-6 w-6 text-signal" viewBox="0 0 24 24" fill="none">
            <path d="M5 7h14M5 12h9M5 17h6" stroke="currentColor" strokeWidth="1.5" />
            <path d="m17 15 2 2 3-4" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        </div>
        <p className="mt-6 font-mono text-[0.65rem] uppercase tracking-[0.24em] text-muted">
          Awaiting evidence
        </p>
        <h2 className="mt-3 font-display text-2xl font-semibold text-white">
          Your diagnosis will assemble here.
        </h2>
        <p className="mt-3 text-sm leading-6 text-muted">
          Paste a failing CI log or load the sample, then run the mock analysis to inspect
          every response field.
        </p>
      </div>
    </section>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <section
      className="min-h-[34rem] border border-fault/50 bg-panel p-6"
      role="alert"
      aria-live="assertive"
    >
      <p className="font-mono text-[0.65rem] uppercase tracking-[0.22em] text-fault">
        Analysis interrupted
      </p>
      <h2 className="mt-3 font-display text-2xl font-semibold text-white">
        The failure could not be analyzed.
      </h2>
      <p className="mt-4 max-w-lg border-l-2 border-fault pl-4 text-sm leading-6 text-fault-soft">
        {message}
      </p>
      <p className="mt-6 text-xs leading-5 text-muted">
        Confirm that the FastAPI server is available at port 8000, then try again.
      </p>
    </section>
  )
}

function SuccessState({ result }: { result: AnalysisResult }) {
  const confidence = Math.round(result.confidence * 100)

  return (
    <article className="space-y-4" aria-live="polite">
      <section className="border border-line bg-panel">
        <div className="grid gap-5 border-b border-line px-5 py-5 sm:grid-cols-[1fr_auto]">
          <div>
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.22em] text-signal">
              Diagnosis assembled
            </p>
            <h2 className="mt-2 font-display text-2xl font-semibold text-white">
              {result.summary}
            </h2>
          </div>
          <div className="min-w-28 border-l border-line pl-5">
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-muted">
              Confidence
            </p>
            <p className="mt-2 font-mono text-3xl text-signal">{confidence}%</p>
          </div>
        </div>
        <div className="px-5 py-5">
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.2em] text-muted">
            Root cause
          </p>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-fog">{result.root_cause}</p>
        </div>
      </section>

      <section className="border border-line bg-panel px-5 py-5" aria-labelledby="evidence-title">
        <div className="flex items-center justify-between">
          <h3 id="evidence-title" className="font-display text-lg font-semibold text-white">
            Evidence
          </h3>
          <span className="font-mono text-[0.65rem] text-muted">{result.evidence.length} SIGNALS</span>
        </div>
        <div className="mt-4 space-y-3">
          {result.evidence.map((item) => (
            <div className="border-l-2 border-signal bg-ink/65 px-4 py-4" key={`${item.source}-${item.line_start}`}>
              <p className="font-mono text-xs text-signal">
                {locationLabel(item.source, item.line_start, item.line_end)}
              </p>
              <code className="mt-3 block overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-6 text-fog">
                {item.excerpt}
              </code>
              <p className="mt-3 text-xs leading-5 text-muted">{item.explanation}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="border border-line bg-panel px-5 py-5">
          <h3 className="font-display text-lg font-semibold text-white">Recommended changes</h3>
          <ol className="mt-4 space-y-3">
            {result.recommended_changes.map((change, index) => (
              <li className="grid grid-cols-[1.6rem_1fr] gap-3 text-sm leading-6 text-fog" key={change}>
                <span className="font-mono text-xs text-signal">{String(index + 1).padStart(2, '0')}</span>
                {change}
              </li>
            ))}
          </ol>
        </section>
        <section className="border border-line bg-panel px-5 py-5">
          <h3 className="font-display text-lg font-semibold text-white">Relevant files</h3>
          <ul className="mt-4 space-y-2">
            {result.relevant_files.map((file) => (
              <li className="border border-line bg-ink px-3 py-2 font-mono text-xs text-fog" key={file}>
                {file}
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="overflow-hidden border border-line bg-terminal" aria-labelledby="patch-title">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h3 id="patch-title" className="font-display text-lg font-semibold text-white">
            Suggested patch
          </h3>
          <span className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-muted">
            Display only
          </span>
        </div>
        <pre className="max-h-80 overflow-auto p-5 font-mono text-xs leading-6 text-fog">
          <code>{result.patch}</code>
        </pre>
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="border border-line bg-panel px-5 py-5">
          <h3 className="font-display text-base font-semibold text-white">Verification commands</h3>
          <ul className="mt-4 space-y-2">
            {result.verification_commands.map((command) => (
              <li className="bg-ink px-3 py-2 font-mono text-xs leading-5 text-signal" key={command}>
                $ {command}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[0.68rem] leading-5 text-muted">
            Review before running. LeanCI never executes commands.
          </p>
        </section>
        <section className="border border-fault/30 bg-panel px-5 py-5">
          <h3 className="font-display text-base font-semibold text-white">Risks</h3>
          <ul className="mt-4 space-y-3 text-xs leading-5 text-fault-soft">
            {result.risks.map((risk) => (
              <li className="border-l border-fault pl-3" key={risk}>
                {risk}
              </li>
            ))}
          </ul>
        </section>
        <section className="border border-line bg-panel px-5 py-5">
          <h3 className="font-display text-base font-semibold text-white">Missing information</h3>
          <ul className="mt-4 space-y-3 text-xs leading-5 text-muted">
            {result.missing_information.map((item) => (
              <li className="border-l border-line-bright pl-3" key={item}>
                {item}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </article>
  )
}

export function ResultsPanel({ state }: ResultsPanelProps) {
  if (state.status === 'loading') {
    return <LoadingState />
  }
  if (state.status === 'error') {
    return <ErrorState message={state.message} />
  }
  if (state.status === 'success') {
    return <SuccessState result={state.data} />
  }
  return <EmptyState />
}
