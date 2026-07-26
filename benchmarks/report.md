# LeanCI Benchmark Report

- Generated: `2026-07-26T14:13:42.299679+00:00`
- Model: `deepseek-v4-flash`
- Finalized: `true`
- Pricing snapshot: `2026-07-25`
- Fixed request configuration: `max_tokens=4096`, thinking disabled, JSON object, zero network retries
- Token metric policy: baseline, `skipped_low_yield`, and `unavailable` fields are null; metrics exist only when `/stats` proves compression.

## Summary

- Baseline completed rows: **5**
- Compressed rows: **2**
- Normal low-yield skips: **3**
- Unavailable rows: **0**
- Upstream failed rows: **0**
- Upstream DeepSeek timeouts: **0**
- Valid quality pairs: **5**
- Average Token savings across actual compression rows only: **85.53%**
- Baseline average quality across valid pairs: **73.00/100**
- Paritok average quality across valid pairs: **54.00/100**
- Quality change: **-19.00 points**

On these five fixed cases, the run observed 85.53% average Token savings across 2 rows where compression actually occurred and a -19.00-point deterministic quality change across 5 valid pairs; 3 low-yield skips, 0 unavailable rows, and 0 upstream failures remain included. This does not establish universal quality preservation, production reliability, or actual billing savings.

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

| Case | Mode | Status | Original | Compressed | Saved | Saved % | Prompt | Completion | Quality | Latency | Error |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| python-pytest | baseline_uncompressed | baseline_completed | — | — | — | — | 28579 | 532 | 65 | 5567 ms | — |
| python-pytest | paritok | compressed | 10469 | 254 | 10215 | 97.57% | 16531 | 472 | 10 | 11703 ms | — |
| typescript-build | baseline_uncompressed | baseline_completed | — | — | — | — | 22955 | 497 | 70 | 5649 ms | — |
| typescript-build | paritok | skipped_low_yield | — | — | — | — | 22955 | 548 | 70 | 10306 ms | — |
| docker-build | baseline_uncompressed | baseline_completed | — | — | — | — | 8959 | 454 | 100 | 6175 ms | — |
| docker-build | paritok | compressed | 543 | 144 | 399 | 73.48% | 8534 | 526 | 40 | 8376 ms | — |
| dependency-resolution | baseline_uncompressed | baseline_completed | — | — | — | — | 19603 | 640 | 65 | 6015 ms | — |
| dependency-resolution | paritok | skipped_low_yield | — | — | — | — | 19603 | 739 | 85 | 9768 ms | — |
| github-actions-environment | baseline_uncompressed | baseline_completed | — | — | — | — | 20957 | 634 | 65 | 6744 ms | — |
| github-actions-environment | paritok | skipped_low_yield | — | — | — | — | 20957 | 561 | 65 | 9034 ms | — |

## Failures and review

- Expected low-benefit skips (normal Paritok behavior, not an outage, cache hit, or stats defect):
  - `typescript-build` / `paritok`: `skipped_low_yield` (`below_refusal_threshold`); Token savings and compression ratio are not applicable. Quality is shown only when a valid structured analysis exists.
  - `dependency-resolution` / `paritok`: `skipped_low_yield` (`below_refusal_threshold`); Token savings and compression ratio are not applicable. Quality is shown only when a valid structured analysis exists.
  - `github-actions-environment` / `paritok`: `skipped_low_yield` (`below_refusal_threshold`); Token savings and compression ratio are not applicable. Quality is shown only when a valid structured analysis exists.

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
