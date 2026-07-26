# LeanCI Benchmark Report

- Generated: `2026-07-26T06:47:05.291041+00:00`
- Model: `deepseek-v4-flash`
- Finalized: `true`
- Pricing snapshot: `2026-07-25`
- Fixed request configuration: `max_tokens=4096`, thinking disabled, JSON object, zero network retries
- Token metric policy: baseline and `compression_skipped` fields are null; Paritok Token fields exist only when isolated `/stats` proves compression.

## Summary

- Successful rows: **5/10**
- Normal low-benefit compression skips: **3**
- Failed rows retained: **2**
- Rows with actual compression proof: **2**
- Upstream DeepSeek timeouts: **1**
- Average Token savings across actual compression rows only: **91.70%**
- Baseline average quality: **73.00/100**
- Paritok average quality: **not applicable**
- Quality change: **not applicable**

On these five fixed cases, the run observed 91.70% average Token savings across 2 rows where compression actually occurred and no comparable Paritok quality average; 3 low-benefit compression skips and 2 failed rows remain included. This does not establish universal quality preservation, production reliability, or actual billing savings.

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
| python-pytest | baseline_uncompressed | success | — | — | — | — | 28579 | 713 | 65 | 6925 ms | — |
| python-pytest | paritok | failed | 10469 | 254 | 10215 | 97.57% | — | — | 0 | 62567 ms | DEEPSEEK_TIMEOUT: The DeepSeek request timed out. Check the network and try again. |
| typescript-build | baseline_uncompressed | success | — | — | — | — | 22955 | 715 | 50 | 6883 ms | — |
| typescript-build | paritok | compression_skipped | — | — | — | — | — | — | N/A | 20031 ms | — |
| docker-build | baseline_uncompressed | success | — | — | — | — | 8959 | 472 | 100 | 5103 ms | — |
| docker-build | paritok | failed | 543 | 77 | 466 | 85.82% | — | — | 0 | 18073 ms | ORIGINAL_TOKEN_MINIMUM_NOT_MET: The verified stats delta was below the fixed case minimum. |
| dependency-resolution | baseline_uncompressed | success | — | — | — | — | 19603 | 657 | 65 | 6607 ms | — |
| dependency-resolution | paritok | compression_skipped | — | — | — | — | — | — | N/A | 18861 ms | — |
| github-actions-environment | baseline_uncompressed | success | — | — | — | — | 20957 | 632 | 85 | 6798 ms | — |
| github-actions-environment | paritok | compression_skipped | — | — | — | — | — | — | N/A | 17919 ms | — |

## Failures and review

- Expected low-benefit skips (normal Paritok behavior, not an outage, cache hit, or stats defect):
  - `typescript-build` / `paritok`: `compression_skipped` (`below_refusal_threshold`); Token savings, compression ratio, and quality are not applicable.
  - `dependency-resolution` / `paritok`: `compression_skipped` (`below_refusal_threshold`); Token savings, compression ratio, and quality are not applicable.
  - `github-actions-environment` / `paritok`: `compression_skipped` (`below_refusal_threshold`); Token savings, compression ratio, and quality are not applicable.
- `python-pytest` / `paritok`: DEEPSEEK_TIMEOUT: The DeepSeek request timed out. Check the network and try again.
  - The isolated `/stats` delta was retained, but the upstream completion exceeded the fixed provider timeout. No response usage or analysis was invented.
- `docker-build` / `paritok`: ORIGINAL_TOKEN_MINIMUM_NOT_MET: The verified stats delta was below the fixed case minimum.
  - The verified `/stats` window recorded `543→77` tokens, below the fixed 5,000 original-Token acceptance gate. The returned analysis was discarded and scored zero.

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
