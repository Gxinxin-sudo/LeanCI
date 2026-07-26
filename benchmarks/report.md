# LeanCI Benchmark Report

- Generated: `2026-07-26T06:07:05.921069+00:00`
- Model: `deepseek-v4-flash`
- Finalized: `true`
- Pricing snapshot: `2026-07-26`
- Fixed request configuration: `max_tokens=4096`, thinking disabled, JSON object, zero network retries
- Token metric policy: baseline compression fields are null; Paritok original/compressed/saved fields come only from isolated `/stats` deltas.

## Summary

- Successful rows: **0/10**
- Failed rows retained: **10**
- Average Token savings: **unavailable**
- Baseline average quality: **0.00/100**
- Paritok average quality: **0.00/100**
- Quality change: **+0.00 points**

No benchmark or promotional claim is supported: all 10 planned rows failed before a valid model result was recorded. The failures remain visible.

## Fixed quality rubric

| Check | Points | Method |
| --- | ---: | --- |
| Root cause | 40 | Required ground-truth term groups in `root_cause` |
| Evidence | 20 | Expected source plus supplied-evidence anchors |
| Relevant files | 15 | Required filenames all present |
| Fix direction | 15 | Required direction term groups in changes/patch |
| JSON completeness | 10 | Strict `DiagnosticAnalysis` validation |

The model never scores itself. Every row keeps `human_review.status=pending` so a reviewer can confirm or override the deterministic result without rewriting it.

## Results

| Case | Mode | Success | Original | Compressed | Saved | Saved % | Quality | Latency | Error |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| python-pytest | baseline_uncompressed | false | — | — | — | — | 0 | 0 ms | PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent. |
| python-pytest | paritok | false | — | — | — | — | 0 | 0 ms | PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent. |
| typescript-build | baseline_uncompressed | false | — | — | — | — | 0 | 0 ms | PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent. |
| typescript-build | paritok | false | — | — | — | — | 0 | 0 ms | PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent. |
| docker-build | baseline_uncompressed | false | — | — | — | — | 0 | 0 ms | PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent. |
| docker-build | paritok | false | — | — | — | — | 0 | 0 ms | PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent. |
| dependency-resolution | baseline_uncompressed | false | — | — | — | — | 0 | 0 ms | PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent. |
| dependency-resolution | paritok | false | — | — | — | — | 0 | 0 ms | PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent. |
| github-actions-environment | baseline_uncompressed | false | — | — | — | — | 0 | 0 ms | PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent. |
| github-actions-environment | paritok | false | — | — | — | — | 0 | 0 ms | PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent. |

## Failures and review

- `python-pytest` / `baseline_uncompressed`: PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent.
- `python-pytest` / `paritok`: PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent.
- `typescript-build` / `baseline_uncompressed`: PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent.
- `typescript-build` / `paritok`: PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent.
- `docker-build` / `baseline_uncompressed`: PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent.
- `docker-build` / `paritok`: PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent.
- `dependency-resolution` / `baseline_uncompressed`: PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent.
- `dependency-resolution` / `paritok`: PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent.
- `github-actions-environment` / `baseline_uncompressed`: PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent.
- `github-actions-environment` / `paritok`: PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was unavailable after the bounded preflight; no DeepSeek request was sent.

A quality score below 100 is not hidden and should be reviewed against the stored `analysis` object and the case's `ground_truth.json`.

## Cost interpretation

- Cache-hit input scenario: `$0.0028/1M` tokens.
- Cache-miss input scenario: `$0.14/1M` tokens.
- Output estimate: `$0.28/1M` tokens.
- These are configured estimates, not an actual bill.
- No Paritok `estimated_cost_saved_usd` value is used.

## Reproduce

Start the local Paritok Proxy, then run each fixed case with explicit cost consent:

```powershell
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case python-pytest
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case typescript-build
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case docker-build
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case dependency-resolution
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case github-actions-environment
```

Each command makes two expected model calls (baseline then Paritok), allows at most one JSON repair per mode, performs no network retry, and keeps failed rows.
