export interface EvidenceItem {
  source: string
  line_start: number | null
  line_end: number | null
  excerpt: string
  explanation: string
}

export interface UnavailableCompressionStats {
  available: false
  paritok_connected: false
  original_tokens: number | null
  compressed_tokens: number | null
  saved_tokens: number | null
  compression_ratio: number | null
  message: string
}

export interface CumulativeParitokStats {
  total_requests: number
  input_tokens_original: number
  input_tokens_compressed: number
  compression_ratio: number
  tokens_saved: number
  tools_filtered: number
}

export interface VerifiedCompressionStats {
  available: true
  paritok_connected: true
  hosted_gpu_available: true
  verification: 'local_health+hosted_gpu_preflight+stats_delta'
  proxy_version: string
  model: 'deepseek-v4-flash'
  proxy_requests: number
  original_tokens: number
  compressed_tokens: number
  saved_tokens: number
  compression_ratio: number
  cumulative: CumulativeParitokStats
  cost_estimate: {
    estimated_input_cost_saved_usd: number
    input_cache_miss_usd_per_m_tokens: number
    pricing_snapshot_date: string
    disclaimer: string
  }
  message: string
}

export type CompressionStats = UnavailableCompressionStats | VerifiedCompressionStats

export interface AnalysisResult {
  summary: string
  root_cause: string
  confidence: number
  evidence: EvidenceItem[]
  relevant_files: string[]
  recommended_changes: string[]
  patch: string
  verification_commands: string[]
  risks: string[]
  missing_information: string[]
  compression_stats: CompressionStats
}

export interface ApiErrorEnvelope {
  error: {
    code: string
    message: string
    request_id: string
  }
}
