import type { AnalysisResult, EvidenceItem } from '../types/api'

function locationLabel(item: EvidenceItem) {
  if (item.line_start === null) {
    return item.source
  }
  return item.line_end && item.line_end !== item.line_start
    ? `${item.source}:${item.line_start}–${item.line_end}`
    : `${item.source}:${item.line_start}`
}

function escapeMarkdownText(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/([\\`*_[\]{}()#+\-.!|])/g, '\\$1')
}

function fencedCode(value: string, language = ''): string {
  const longestRun = Math.max(
    0,
    ...Array.from(value.matchAll(/`+/g), (match) => match[0].length),
  )
  const fence = '`'.repeat(Math.max(3, longestRun + 1))
  return `${fence}${language}\n${value}\n${fence}`
}

export function reportMarkdown(result: AnalysisResult): string {
  const evidence = result.evidence
    .map(
      (item) =>
        `- **${escapeMarkdownText(locationLabel(item))}** — ${escapeMarkdownText(item.explanation)}\n\n${fencedCode(item.excerpt)}`,
    )
    .join('\n')
  const list = (items: string[]) =>
    items.map((item) => `- ${escapeMarkdownText(item)}`).join('\n') || '- None'
  const stats = result.compression_stats
  const telemetry =
    stats.available
      ? [
          `- Original Tokens: ${stats.original_tokens}`,
          `- Compressed Tokens: ${stats.compressed_tokens}`,
          `- Tokens Saved: ${stats.saved_tokens}`,
          `- Compression Ratio: ${(stats.compression_ratio * 100).toFixed(1)}%`,
          `- Estimated DeepSeek Input Cost Saved: $${stats.cost_estimate.estimated_input_cost_saved_usd.toFixed(8)}`,
          `- Paritok Status: Verified`,
          `- DeepSeek Model: ${stats.model}`,
          `- Analysis Time: ${result.analysis_time_ms} ms`,
          `- Pricing snapshot: ${stats.cost_estimate.pricing_snapshot_date}`,
          `- Disclaimer: ${stats.cost_estimate.disclaimer}`,
        ].join('\n')
      : '- Token metrics unavailable; no values were inferred.'

  return `# LeanCI diagnostic report

## Summary

${escapeMarkdownText(result.summary)}

## Root Cause

${escapeMarkdownText(result.root_cause)}

## Confidence

${Math.round(result.confidence * 100)}%

## Evidence

${evidence || '- None'}

## Relevant Files

${list(result.relevant_files)}

## Recommended Changes

${list(result.recommended_changes)}

## Patch

${fencedCode(result.patch, 'diff')}

## Verification Commands

${list(result.verification_commands)}

## Risks

${list(result.risks)}

## Missing Information

${list(result.missing_information)}

## Token telemetry

${telemetry}

## Privacy and execution boundary

LeanCI does not permanently store pasted logs or uploaded files. Inputs are processed in memory
and sent through Paritok and DeepSeek; provider retention policies still apply. Patches and
commands in this report are untrusted, inert text and require human review.
`
}
