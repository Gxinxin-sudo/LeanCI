export interface EvidenceItem {
  source: string
  line_start: number | null
  line_end: number | null
  excerpt: string
  explanation: string
}

export interface CompressionStats {
  available: false
  paritok_connected: false
  original_tokens: number | null
  compressed_tokens: number | null
  saved_tokens: number | null
  compression_ratio: number | null
  message: string
}

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
