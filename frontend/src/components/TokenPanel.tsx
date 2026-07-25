import type { CompressionStats } from '../types/api'

interface TokenPanelProps {
  stats?: CompressionStats
  loading: boolean
}

const tokenMetrics = [
  { label: 'Original', key: 'original_tokens' },
  { label: 'Compressed', key: 'compressed_tokens' },
  { label: 'Saved', key: 'saved_tokens' },
] as const

export function TokenPanel({ stats, loading }: TokenPanelProps) {
  const verified = stats?.available === true
  const ratio = verified ? `${(stats.compression_ratio * 100).toFixed(1)}%` : '—'

  return (
    <section className="border border-line bg-panel" aria-labelledby="token-panel-title">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <div>
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.22em] text-muted">
            {verified ? 'Telemetry / verified' : 'Telemetry / awaiting request'}
          </p>
          <h2 id="token-panel-title" className="mt-1 font-display text-lg font-semibold text-white">
            Token panel
          </h2>
        </div>
        <span
          className={`status-dot ${verified ? 'status-dot-online' : 'status-dot-offline'}`}
          aria-hidden="true"
        />
      </div>

      <div className="grid grid-cols-3 divide-x divide-line">
        {tokenMetrics.map((metric) => (
          <div className="px-4 py-5" key={metric.key}>
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-muted">
              {metric.label}
            </p>
            <p className="mt-3 font-mono text-2xl text-fog" aria-label={`${metric.label} tokens`}>
              {loading ? '···' : (stats?.[metric.key] ?? '—')}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 border-t border-line">
        <div className="border-r border-line px-4 py-4">
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-muted">
            Compressed / original
          </p>
          <p className="mt-2 font-mono text-lg text-signal">{loading ? '···' : ratio}</p>
        </div>
        <div className="px-4 py-4">
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-muted">
            Proxy requests
          </p>
          <p className="mt-2 font-mono text-lg text-fog">
            {loading ? '···' : verified ? stats.proxy_requests : '—'}
          </p>
        </div>
      </div>

      <div
        className={`border-t px-5 py-4 ${
          verified ? 'border-signal/30 bg-signal/8' : 'border-fault/30 bg-fault/8'
        }`}
      >
        <p className={`flex items-start gap-3 text-xs leading-5 ${verified ? 'text-fog' : 'text-fault-soft'}`}>
          <span
            className={`mt-1 h-1.5 w-1.5 shrink-0 ${verified ? 'bg-signal' : 'bg-fault'}`}
            aria-hidden="true"
          />
          {stats?.message ?? 'Run an analysis to read a verified Paritok stats delta.'}
        </p>
        {verified ? (
          <>
            <p className="mt-2 pl-4 text-xs leading-5 text-muted">
              Cumulative: {stats.cumulative.total_requests.toLocaleString('en-US')} requests ·{' '}
              {stats.cumulative.tokens_saved.toLocaleString('en-US')} tokens saved.
            </p>
            <p className="mt-2 pl-4 text-xs leading-5 text-muted">
              LeanCI estimate: ${stats.cost_estimate.estimated_input_cost_saved_usd.toFixed(8)}
              {' · '}DeepSeek cache-miss price snapshot {stats.cost_estimate.pricing_snapshot_date}.
              Not an actual bill.
            </p>
          </>
        ) : (
          <p className="mt-2 pl-4 text-xs leading-5 text-muted">
            Token values are never inferred when stats are unavailable.
          </p>
        )}
      </div>
    </section>
  )
}
