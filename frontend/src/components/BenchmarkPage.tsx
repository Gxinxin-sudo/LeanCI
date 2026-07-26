import { useEffect, useState } from 'react'

import { getBenchmarkResults } from '../lib/api'
import type { BenchmarkArtifact, BenchmarkRow } from '../types/api'

type BenchmarkState =
  | { status: 'loading' }
  | { status: 'ready'; data: BenchmarkArtifact }
  | { status: 'error'; message: string }

const CASE_LABELS: Record<string, string> = {
  'python-pytest': 'Python pytest failure',
  'typescript-build': 'TypeScript type error',
  'docker-build': 'Docker build failure',
  'dependency-resolution': 'Dependency resolution failure',
  'github-actions-environment': 'GitHub Actions environment failure',
}

function formatInteger(value: number | null): string {
  return value === null ? 'N/A' : value.toLocaleString('en-US')
}

function formatMoney(value: number | null): string {
  return value === null ? 'N/A' : `$${value.toFixed(8)}`
}

function savedPercent(row: BenchmarkRow): string {
  return row.compression_ratio === null
    ? 'N/A'
    : `${((1 - row.compression_ratio) * 100).toFixed(2)}%`
}

function QualityChecks({ row }: { row: BenchmarkRow }) {
  if (row.quality_score === null) {
    return <div className="quality-checks quality-na">Not scored — compression skipped</div>
  }
  const checks = [
    ['Root', row.root_cause_correct, 40],
    ['Evidence', row.evidence_correct, 20],
    ['Files', row.relevant_files_correct, 15],
    ['Fix', row.fix_direction_correct, 15],
    ['JSON', row.json_valid, 10],
  ] as const

  return (
    <div className="quality-checks" aria-label={`Quality checks: ${row.quality_score} points`}>
      {checks.map(([label, passed, points]) => (
        <span className={passed ? 'quality-pass' : 'quality-fail'} key={label}>
          <i aria-hidden="true">{passed ? '✓' : '×'}</i>
          {label} <small>{points}</small>
        </span>
      ))}
    </div>
  )
}

function BenchmarkLedger({ artifact }: { artifact: BenchmarkArtifact }) {
  return (
    <section className="benchmark-ledger" aria-labelledby="ledger-title">
      <div className="benchmark-section-heading">
        <div>
          <p className="eyebrow">All fixed cases · no cherry-picking</p>
          <h2 id="ledger-title">Evidence ledger</h2>
        </div>
        <p>
          Baseline compression fields stay blank because only Paritok <code>/stats</code>
          deltas may populate them.
        </p>
      </div>

      <div className="ledger-head" aria-hidden="true">
        <span>Case / route</span>
        <span>Token proof</span>
        <span>Quality</span>
        <span>Timing / review</span>
      </div>

      {artifact.case_ids.map((caseId) => {
        const rows = artifact.rows.filter((row) => row.case_id === caseId)
        return (
          <article className="ledger-case" key={caseId}>
            <header>
              <span>{String(artifact.case_ids.indexOf(caseId) + 1).padStart(2, '0')}</span>
              <div>
                <h3>{CASE_LABELS[caseId] ?? caseId}</h3>
                <code>{caseId}</code>
              </div>
            </header>
            <div className="ledger-pair">
              {rows.map((row) => (
                <div
                  className={`ledger-row ${
                    row.status === 'failed'
                      ? 'ledger-row-failed'
                      : row.status === 'compression_skipped'
                        ? 'ledger-row-skipped'
                        : ''
                  }`}
                  key={row.mode}
                >
                  <div className="ledger-route">
                    <strong>
                      {row.mode === 'baseline_uncompressed' ? 'A · Baseline' : 'B · Paritok'}
                    </strong>
                    <span
                      className={
                        row.status === 'failed'
                          ? 'result-failed'
                          : row.status === 'compression_skipped'
                            ? 'result-skipped'
                            : 'result-ok'
                      }
                    >
                      {row.status === 'success'
                        ? 'Completed'
                        : row.status === 'compression_skipped'
                          ? 'Compression skipped · expected low benefit'
                          : 'Failed · retained'}
                    </span>
                    <small>
                      {row.mode === 'baseline_uncompressed'
                        ? 'Uncompressed mode'
                        : row.status === 'compression_skipped'
                          ? `Normal passthrough · ${row.compression_skip_reason}`
                          : 'Verified /stats delta'}
                    </small>
                  </div>
                  <dl className="ledger-token-grid">
                    <div><dt>Original</dt><dd>{formatInteger(row.original_tokens)}</dd></div>
                    <div><dt>Compressed</dt><dd>{formatInteger(row.compressed_tokens)}</dd></div>
                    <div><dt>Saved</dt><dd>{formatInteger(row.tokens_saved)}</dd></div>
                    <div><dt>Saved %</dt><dd>{savedPercent(row)}</dd></div>
                    <div><dt>Prompt</dt><dd>{formatInteger(row.prompt_tokens)}</dd></div>
                    <div><dt>Completion</dt><dd>{formatInteger(row.completion_tokens)}</dd></div>
                  </dl>
                  <div className="ledger-quality">
                    <strong>
                      {row.quality_score === null ? 'N/A' : row.quality_score}
                      {row.quality_score !== null && <small>/100</small>}
                    </strong>
                    <QualityChecks row={row} />
                  </div>
                  <div className="ledger-meta">
                    <dl>
                      <div><dt>Latency</dt><dd>{row.latency_ms.toLocaleString('en-US')} ms</dd></div>
                      <div><dt>Human review</dt><dd>{row.human_review.status}</dd></div>
                      <div><dt>Cache-hit input</dt><dd>{formatMoney(row.cost_estimate.input_if_all_cache_hit_usd)}</dd></div>
                      <div><dt>Cache-miss input</dt><dd>{formatMoney(row.cost_estimate.input_if_all_cache_miss_usd)}</dd></div>
                    </dl>
                    {row.error && <p role="alert">{row.error}</p>}
                  </div>
                </div>
              ))}
            </div>
          </article>
        )
      })}
    </section>
  )
}

function BenchmarkContent({ artifact }: { artifact: BenchmarkArtifact }) {
  const savings = artifact.summary.average_token_savings_percent
  const change = artifact.summary.quality_change_points
  const baselineQuality = artifact.summary.baseline_average_quality
  const paritokQuality = artifact.summary.paritok_average_quality
  return (
    <>
      <section className="benchmark-hero">
        <div>
          <p className="eyebrow">Fixed benchmark · generated {new Date(artifact.generated_at).toLocaleDateString()}</p>
          <h1>Every row stays.</h1>
          <p>
            Five known CI failures. Two byte-identical initial prompts per case.
            Deterministic scoring against ground truth, with failed calls left in place.
          </p>
        </div>
        <aside className="benchmark-verdict">
          <p className="eyebrow">What this run supports</p>
          <p>{artifact.summary.supported_claim}</p>
        </aside>
      </section>

      <section className="benchmark-readout" aria-label="Benchmark summary">
        <div>
          <span>Average Token savings</span>
          <strong>{savings === null ? 'N/A' : `${savings.toFixed(2)}%`}</strong>
          <small>{artifact.summary.actual_compression_rows} actual compression rows only</small>
        </div>
        <div>
          <span>Quality change</span>
          <strong>{change === null ? 'N/A' : `${change > 0 ? '+' : ''}${change.toFixed(2)}`}</strong>
          <small>
            {baselineQuality === null ? 'N/A' : baselineQuality.toFixed(2)} baseline →{' '}
            {paritokQuality === null ? 'N/A' : paritokQuality.toFixed(2)} Paritok
          </small>
        </div>
        <div>
          <span>Normal low-benefit skips</span>
          <strong>{artifact.summary.compression_skipped_rows}</strong>
          <small>Expected Paritok behavior · excluded from averages</small>
        </div>
        <div className={artifact.summary.failed_rows > 0 ? 'readout-failed' : ''}>
          <span>Failed rows retained</span>
          <strong>{artifact.summary.failed_rows}</strong>
          <small>{artifact.summary.upstream_timeout_rows} upstream timeout</small>
        </div>
      </section>

      <section className="fairness-contract" aria-labelledby="fairness-title">
        <div>
          <p className="eyebrow">Comparison contract</p>
          <h2 id="fairness-title">One variable: compression route</h2>
        </div>
        <dl>
          <div><dt>Model</dt><dd>{artifact.configuration.model}</dd></div>
          <div><dt>Max output</dt><dd>{artifact.configuration.max_tokens.toLocaleString('en-US')}</dd></div>
          <div><dt>Thinking</dt><dd>{artifact.configuration.thinking}</dd></div>
          <div><dt>JSON</dt><dd>{artifact.configuration.response_format}</dd></div>
          <div><dt>Network retries</dt><dd>{artifact.configuration.network_retries}</dd></div>
          <div><dt>Scoring</dt><dd>{artifact.configuration.scoring_rule}</dd></div>
        </dl>
      </section>

      <BenchmarkLedger artifact={artifact} />

      <section className="benchmark-footnotes">
        <div>
          <p className="eyebrow">Price scenarios · not a bill</p>
          <h2>Cache behavior changes the estimate.</h2>
        </div>
        <p>
          Snapshot {artifact.pricing.snapshot_date}: input cache hit ${artifact.pricing.input_cache_hit_usd_per_m_tokens}/1M,
          input cache miss ${artifact.pricing.input_cache_miss_usd_per_m_tokens}/1M, output ${artifact.pricing.output_usd_per_m_tokens}/1M.
          The ledger shows both input scenarios. LeanCI does not use Paritok’s unknown-model dollar estimate.
        </p>
      </section>
    </>
  )
}

export function BenchmarkPage() {
  const [state, setState] = useState<BenchmarkState>({ status: 'loading' })

  useEffect(() => {
    let active = true
    void getBenchmarkResults()
      .then((data) => {
        if (active) setState({ status: 'ready', data })
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            status: 'error',
            message: error instanceof Error ? error.message : 'Benchmark results are unavailable.',
          })
        }
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="benchmark-page">
      {state.status === 'loading' && (
        <section className="benchmark-state" aria-live="polite">
          <span className="loading-mark" aria-hidden="true" />
          <p>Loading the fixed benchmark artifact…</p>
        </section>
      )}
      {state.status === 'error' && (
        <section className="benchmark-state benchmark-state-error" role="alert">
          <p className="eyebrow">Artifact unavailable</p>
          <h1>The benchmark cannot be audited yet.</h1>
          <p>{state.message}</p>
        </section>
      )}
      {state.status === 'ready' && <BenchmarkContent artifact={state.data} />}
    </div>
  )
}
