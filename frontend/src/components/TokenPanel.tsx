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
  return (
    <section className="border border-line bg-panel" aria-labelledby="token-panel-title">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <div>
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.22em] text-muted">
            Telemetry / unavailable
          </p>
          <h2 id="token-panel-title" className="mt-1 font-display text-lg font-semibold text-white">
            Token panel
          </h2>
        </div>
        <span className="status-dot status-dot-offline" aria-hidden="true" />
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

      <div className="border-t border-fault/30 bg-fault/8 px-5 py-4">
        <p className="flex items-start gap-3 text-xs leading-5 text-fault-soft">
          <span className="mt-1 h-1.5 w-1.5 shrink-0 bg-fault" aria-hidden="true" />
          {stats?.message ?? 'Demo data — Paritok not connected'}
        </p>
        <p className="mt-2 pl-4 text-xs leading-5 text-muted">
          No token counts are estimated or generated in demo mode.
        </p>
      </div>
    </section>
  )
}
