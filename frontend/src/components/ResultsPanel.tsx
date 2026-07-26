import { useState } from 'react'

import { reportMarkdown } from '../lib/report'
import type { AnalysisResult, EvidenceItem } from '../types/api'

interface ResultsPanelProps {
  state:
    | { status: 'idle' }
    | { status: 'loading' }
    | { status: 'success'; data: AnalysisResult }
    | { status: 'error'; message: string }
  onRetry: () => void
}

function locationLabel(item: EvidenceItem) {
  if (item.line_start === null) {
    return item.source
  }
  return item.line_end && item.line_end !== item.line_start
    ? `${item.source}:${item.line_start}–${item.line_end}`
    : `${item.source}:${item.line_start}`
}

async function copyText(value: string): Promise<void> {
  await navigator.clipboard.writeText(value)
}

function ActionButton({
  children,
  onClick,
}: {
  children: React.ReactNode
  onClick: () => void
}) {
  return (
    <button className="secondary-action" type="button" onClick={onClick}>
      {children}
    </button>
  )
}

function LoadingState() {
  return (
    <section className="result-state result-loading" aria-live="polite" aria-busy="true">
      <div className="loading-line">
        <span className="loading-mark" aria-hidden="true" />
        <div>
          <p className="eyebrow">Formal route in progress</p>
          <h2>Compressing context, then tracing evidence…</h2>
        </div>
      </div>
      <p>
        LeanCI is waiting for a verified Paritok stats delta before it will show any
        Token values. A model result without route proof is discarded.
      </p>
      <div className="loading-rails" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </section>
  )
}

function EmptyState() {
  return (
    <section className="result-state result-empty">
      <div className="result-empty-mark" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <p className="eyebrow">Ready for evidence</p>
      <h2>Load a fixed sample and get a reviewable diagnosis.</h2>
      <p>
        The report will keep the claim, quoted evidence, affected files, patch,
        verification commands, risks, and real Token delta together.
      </p>
    </section>
  )
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <section className="result-state result-error" role="alert" aria-live="assertive">
      <p className="eyebrow">Analysis stopped safely</p>
      <h2>LeanCI did not produce a diagnosis.</h2>
      <p className="error-message">{message}</p>
      <p>
        Check the route status above. Formal analysis does not fall back to Mock or
        direct DeepSeek.
      </p>
      <button className="primary-action primary-action-compact" type="button" onClick={onRetry}>
        Retry analysis
      </button>
    </section>
  )
}

function ListSection({
  title,
  items,
  tone,
}: {
  title: string
  items: string[]
  tone?: 'risk' | 'muted'
}) {
  return (
    <section className={`report-section report-list ${tone ? `report-${tone}` : ''}`}>
      <h3>{title}</h3>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="empty-value">None reported.</p>
      )}
    </section>
  )
}

function SuccessState({ result }: { result: AnalysisResult }) {
  const [copyStatus, setCopyStatus] = useState('')
  const confidence = Math.round(result.confidence * 100)

  const handleCopy = async (label: string, value: string) => {
    try {
      await copyText(value)
      setCopyStatus(`${label} copied`)
    } catch {
      setCopyStatus(`Could not copy ${label.toLowerCase()}`)
    }
  }

  const handleDownload = () => {
    const blob = new Blob([reportMarkdown(result)], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'leanci-report.md'
    anchor.hidden = true
    document.body.append(anchor)
    anchor.click()
    anchor.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 0)
    setCopyStatus('Report downloaded')
  }

  return (
    <article className="report" aria-live="polite">
      <section className="report-summary">
        <div className="report-summary-copy">
          <p className="eyebrow">Summary</p>
          <h2>{result.summary}</h2>
        </div>
        <div className="confidence-block">
          <span>Confidence</span>
          <strong>{confidence}%</strong>
        </div>
        <div className="report-root">
          <p className="eyebrow">Root Cause</p>
          <p>{result.root_cause}</p>
        </div>
      </section>

      <section className="report-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Quoted from supplied context</p>
            <h3>Evidence</h3>
          </div>
          <ActionButton
            onClick={() =>
              void handleCopy(
                'Evidence',
                result.evidence
                  .map((item) => `${locationLabel(item)}\n${item.excerpt}\n${item.explanation}`)
                  .join('\n\n'),
              )
            }
          >
            Copy evidence
          </ActionButton>
        </div>
        <div className="evidence-list">
          {result.evidence.map((item) => (
            <article className="evidence-item" key={`${item.source}-${item.line_start}`}>
              <p>{locationLabel(item)}</p>
              <pre><code>{item.excerpt}</code></pre>
              <span>{item.explanation}</span>
            </article>
          ))}
        </div>
      </section>

      <div className="report-grid-two">
        <section className="report-section report-list">
          <h3>Relevant Files</h3>
          <ul className="file-list">
            {result.relevant_files.map((file) => <li key={file}>{file}</li>)}
          </ul>
        </section>
        <section className="report-section report-list numbered-list">
          <h3>Recommended Changes</h3>
          <ol>
            {result.recommended_changes.map((change) => <li key={change}>{change}</li>)}
          </ol>
        </section>
      </div>

      <section className="report-section patch-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Review only · never applied</p>
            <h3>Patch</h3>
          </div>
          <div className="button-row">
            <ActionButton onClick={() => void handleCopy('Patch', result.patch)}>
              Copy Patch
            </ActionButton>
            <ActionButton onClick={handleDownload}>Download Report</ActionButton>
          </div>
        </div>
        <pre><code>{result.patch || 'No patch was returned.'}</code></pre>
        <p className="action-status" aria-live="polite">{copyStatus}</p>
      </section>

      <section className="report-section report-list command-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Human review required · never executed</p>
            <h3>Verification Commands</h3>
          </div>
          <ActionButton
            onClick={() =>
              void handleCopy('Verification commands', result.verification_commands.join('\n'))
            }
          >
            Copy commands
          </ActionButton>
        </div>
        <ul>
          {result.verification_commands.map((command) => (
            <li key={command}><code>$ {command}</code></li>
          ))}
        </ul>
      </section>

      <div className="report-grid-two">
        <ListSection title="Risks" items={result.risks} tone="risk" />
        <ListSection title="Missing Information" items={result.missing_information} tone="muted" />
      </div>
    </article>
  )
}

export function ResultsPanel({ state, onRetry }: ResultsPanelProps) {
  if (state.status === 'loading') {
    return <LoadingState />
  }
  if (state.status === 'error') {
    return <ErrorState message={state.message} onRetry={onRetry} />
  }
  if (state.status === 'success') {
    return <SuccessState result={state.data} />
  }
  return <EmptyState />
}
