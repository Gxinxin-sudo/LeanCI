export interface UploadedTextFile {
  name: string
  content: string
}

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
  analysis_time_ms: number
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  service: 'leanci-api'
  mode: 'paritok'
  paritok_connected: boolean
  hosted_gpu_available: boolean
  proxy_version: string | null
  model: 'deepseek-v4-flash'
  deepseek_called: false
  message: string
}

export interface SampleSummary {
  id: string
  title: string
  category: 'Python' | 'TypeScript' | 'Docker' | 'Dependencies' | 'GitHub Actions'
  description: string
  log_bytes: number
  file_count: number
}

export interface SamplePayload extends SampleSummary {
  log_text: string
  files: UploadedTextFile[]
}

export interface CapturedSampleResult {
  schema_version: 1
  sample_id: string
  captured_at: string
  capture_kind: 'real_paritok_stats_delta'
  analysis_result: AnalysisResult
}

export interface ApiErrorEnvelope {
  error: {
    code: string
    message: string
    request_id: string
  }
}

export type BenchmarkMode = 'baseline_uncompressed' | 'paritok'

export interface BenchmarkRow {
  case_id: string
  mode: BenchmarkMode
  success: boolean
  original_tokens: number | null
  compressed_tokens: number | null
  tokens_saved: number | null
  compression_ratio: number | null
  prompt_tokens: number | null
  completion_tokens: number | null
  prompt_cache_hit_tokens: number | null
  prompt_cache_miss_tokens: number | null
  latency_ms: number
  root_cause_correct: boolean
  evidence_correct: boolean
  relevant_files_correct: boolean
  fix_direction_correct: boolean
  json_valid: boolean
  quality_score: number
  error: string | null
  run_timestamp: string
  model: 'deepseek-v4-flash'
  pricing_snapshot_date: string
  initial_messages_sha256: string
  json_schema_sha256: string
  human_review: {
    status: 'pending' | 'confirmed' | 'overridden'
    reviewer: string | null
    notes: string | null
  }
  cost_estimate: {
    input_if_all_cache_hit_usd: number | null
    input_if_all_cache_miss_usd: number | null
    input_from_reported_cache_split_usd: number | null
    output_usd: number | null
    saved_input_if_cache_hit_usd: number | null
    saved_input_if_cache_miss_usd: number | null
    disclaimer: string
  }
}

export interface BenchmarkArtifact {
  schema_version: 1
  generated_at: string
  finalized: boolean
  case_ids: string[]
  configuration: {
    model: 'deepseek-v4-flash'
    max_tokens: number
    thinking: 'disabled'
    response_format: 'json_object'
    network_retries: 0
    execution_order: 'baseline_uncompressed_then_paritok'
    scoring_rule: '40+20+15+15+10'
    token_metric_policy: string
  }
  pricing: {
    snapshot_date: string
    input_cache_hit_usd_per_m_tokens: number
    input_cache_miss_usd_per_m_tokens: number
    output_usd_per_m_tokens: number
    note: string
  }
  summary: {
    expected_cases: number
    expected_rows: number
    completed_rows: number
    successful_rows: number
    failed_rows: number
    average_tokens_saved: number | null
    average_token_savings_percent: number | null
    baseline_average_quality: number
    paritok_average_quality: number
    quality_change_points: number
    supported_claim: string
  }
  rows: BenchmarkRow[]
}
