import type { CompressionStats } from '../types/api'

interface TokenPanelProps {
  stats?: CompressionStats
  analysisTimeMs?: number
  loading: boolean
}

function valueOrDash(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toLocaleString('en-US')
}

export function TokenPanel({ stats, analysisTimeMs, loading }: TokenPanelProps) {
  const verified = stats?.available === true
  const compressedPercent = verified ? stats.compression_ratio * 100 : 0
  const savedPercent = verified ? Math.max(0, 100 - compressedPercent) : 0

  return (
    <section className="telemetry-panel" aria-labelledby="token-panel-title">
      <div className="telemetry-heading">
        <div>
          <p className="eyebrow">{verified ? 'Verified request delta' : 'Awaiting real stats'}</p>
          <h2 id="token-panel-title">Token savings</h2>
        </div>
        <span className={`route-badge ${verified ? 'route-badge-ok' : ''}`}>
          {verified ? 'Paritok verified' : 'No result'}
        </span>
      </div>

      <div className="saved-readout">
        <div>
          <p className="metric-label">Tokens Saved</p>
          <p className="saved-number">
            {loading ? '···' : valueOrDash(stats?.saved_tokens)}
          </p>
        </div>
        <p className="saved-percent">{verified ? `${savedPercent.toFixed(1)}% less input` : '—'}</p>
      </div>

      <div className="compression-lane" aria-label="Original to compressed token flow">
        <div className="compression-lane-labels">
          <span>Original Tokens</span>
          <span>Compressed Tokens</span>
        </div>
        <div className="compression-lane-track">
          <span className="compression-lane-original" />
          <span
            className="compression-lane-compressed"
            style={{ width: verified ? `${Math.max(compressedPercent, 2)}%` : '0%' }}
          />
        </div>
        <div className="compression-lane-values">
          <strong>{loading ? '···' : valueOrDash(stats?.original_tokens)}</strong>
          <strong>{loading ? '···' : valueOrDash(stats?.compressed_tokens)}</strong>
        </div>
      </div>

      <dl className="telemetry-grid">
        <div>
          <dt>Compression Ratio</dt>
          <dd>{loading ? '···' : verified ? `${compressedPercent.toFixed(1)}%` : '—'}</dd>
        </div>
        <div>
          <dt>Estimated DeepSeek Input Cost Saved</dt>
          <dd>
            {loading
              ? '···'
              : verified
                ? `$${stats.cost_estimate.estimated_input_cost_saved_usd.toFixed(8)}`
                : '—'}
          </dd>
        </div>
        <div>
          <dt>Paritok Status</dt>
          <dd className={verified ? 'text-ok' : undefined}>
            {verified ? `Verified · ${stats.proxy_requests} request` : 'Not verified'}
          </dd>
        </div>
        <div>
          <dt>DeepSeek Model</dt>
          <dd>{verified ? stats.model : 'deepseek-v4-flash'}</dd>
        </div>
        <div>
          <dt>Analysis Time</dt>
          <dd>
            {loading
              ? '···'
              : analysisTimeMs === undefined
                ? '—'
                : `${(analysisTimeMs / 1000).toFixed(2)} s`}
          </dd>
        </div>
        <div>
          <dt>Stats proof</dt>
          <dd>{verified ? stats.verification.replaceAll('_', ' ') : '—'}</dd>
        </div>
      </dl>

      <div className={`telemetry-note ${verified ? 'telemetry-note-ok' : ''}`}>
        <span aria-hidden="true" />
        <div>
          <p>{stats?.message ?? 'Run an analysis to read a real Paritok /stats delta.'}</p>
          {verified && (
            <p className="telemetry-disclaimer">
              Price snapshot {stats.cost_estimate.pricing_snapshot_date}. Estimate only,
              not an actual bill. Cumulative proxy total: {stats.cumulative.total_requests.toLocaleString('en-US')} requests.
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
