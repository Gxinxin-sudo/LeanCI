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
  compression_stats: {
    available: false,
    paritok_connected: false,
    original_tokens: null,
    compressed_tokens: null,
    saved_tokens: null,
    compression_ratio: null,
    message: 'Demo data — Paritok not connected',
  },
}
