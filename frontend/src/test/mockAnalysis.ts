import type { AnalysisResult } from '../types/api'

export const mockAnalysis: AnalysisResult = {
  summary: 'The TypeScript build stops on a strict type mismatch.',
  root_cause: 'An optional environment value is passed to a required string parameter.',
  confidence: 0.94,
  evidence: [
    {
      source: 'ci.log',
      line_start: 8,
      line_end: 9,
      excerpt: "Type 'undefined' is not assignable to type 'string'.",
      explanation: 'The compiler identifies the nullable argument.',
    },
  ],
  relevant_files: ['src/services/report.ts'],
  recommended_changes: ['Validate REPORT_BUCKET at startup.'],
  patch: 'diff --git a/src/config/env.ts b/src/config/env.ts',
  verification_commands: ['npm run typecheck'],
  risks: ['Deployments must define the variable.'],
  missing_information: ['Deployment variables were not supplied.'],
  analysis_time_ms: 1_324,
  compression_stats: {
    available: true,
    paritok_connected: true,
    hosted_gpu_available: true,
    verification: 'local_health+hosted_gpu_preflight+stats_delta',
    proxy_version: '1.0.0',
    model: 'deepseek-v4-flash',
    proxy_requests: 1,
    original_tokens: 8_000,
    compressed_tokens: 2_000,
    saved_tokens: 6_000,
    compression_ratio: 0.25,
    cumulative: {
      total_requests: 12,
      input_tokens_original: 80_000,
      input_tokens_compressed: 20_000,
      compression_ratio: 0.25,
      tokens_saved: 60_000,
      tools_filtered: 0,
    },
    cost_estimate: {
      estimated_input_cost_saved_usd: 0.00084,
      input_cache_miss_usd_per_m_tokens: 0.14,
      pricing_snapshot_date: '2026-07-31',
      disclaimer: "Estimate from LeanCI's configured DeepSeek price; not an actual bill.",
    },
    message:
      "Verified through Paritok; Token metrics come only from this request's stats delta.",
  },
}
