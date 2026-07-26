# LeanCI Benchmark Report

- Generated: `2026-07-26T06:47:05.291041+00:00`
- Model: `deepseek-v4-flash`
- Finalized: `true`
- Pricing snapshot: `2026-07-25`
- Fixed request configuration: `max_tokens=4096`, thinking disabled, JSON object, zero network retries
- Token metric policy: baseline compression fields are null; Paritok original/compressed/saved fields come only from isolated `/stats` deltas.

## Summary

- Successful rows: **5/10**
- Failed rows retained: **5**
- Average Token savings: **unavailable**
- Baseline average quality: **73.00/100**
- Paritok average quality: **0.00/100**
- Quality change: **-73.00 points**

On these five fixed cases, the run observed no verified average Token savings and a -73.00-point deterministic quality change. All 5 failed rows remain included. This does not establish universal quality preservation, production reliability, or actual billing savings.

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

| Case | Mode | Success | Original | Compressed | Saved | Saved % | Prompt | Completion | Quality | Latency | Error |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| python-pytest | baseline_uncompressed | true | — | — | — | — | 28579 | 713 | 65 | 6925 ms | — |
| python-pytest | paritok | false | 10469 | 254 | 10215 | 97.57% | — | — | 0 | 62567 ms | DEEPSEEK_TIMEOUT: The DeepSeek request timed out. Check the network and try again. |
| typescript-build | baseline_uncompressed | true | — | — | — | — | 22955 | 715 | 50 | 6883 ms | — |
| typescript-build | paritok | false | 0 | 0 | 0 | — | — | — | 0 | 20031 ms | ORIGINAL_TOKEN_MINIMUM_NOT_MET: The verified stats delta was below the fixed case minimum. |
| docker-build | baseline_uncompressed | true | — | — | — | — | 8959 | 472 | 100 | 5103 ms | — |
| docker-build | paritok | false | 543 | 77 | 466 | 85.82% | — | — | 0 | 18073 ms | ORIGINAL_TOKEN_MINIMUM_NOT_MET: The verified stats delta was below the fixed case minimum. |
| dependency-resolution | baseline_uncompressed | true | — | — | — | — | 19603 | 657 | 65 | 6607 ms | — |
| dependency-resolution | paritok | false | 0 | 0 | 0 | — | — | — | 0 | 18861 ms | ORIGINAL_TOKEN_MINIMUM_NOT_MET: The verified stats delta was below the fixed case minimum. |
| github-actions-environment | baseline_uncompressed | true | — | — | — | — | 20957 | 632 | 85 | 6798 ms | — |
| github-actions-environment | paritok | false | 0 | 0 | 0 | — | — | — | 0 | 17919 ms | ORIGINAL_TOKEN_MINIMUM_NOT_MET: The verified stats delta was below the fixed case minimum. |

## Failures and review

- `python-pytest` / `paritok`: DEEPSEEK_TIMEOUT: The DeepSeek request timed out. Check the network and try again.
  - The isolated `/stats` delta was retained, but the upstream completion exceeded the fixed provider timeout. No response usage or analysis was invented.
- `typescript-build` / `paritok`: ORIGINAL_TOKEN_MINIMUM_NOT_MET: The verified stats delta was below the fixed case minimum.
  - The verified `/stats` window recorded `0→0` tokens, below the fixed 5,000 original-Token acceptance gate. The returned analysis was discarded and scored zero.
- `docker-build` / `paritok`: ORIGINAL_TOKEN_MINIMUM_NOT_MET: The verified stats delta was below the fixed case minimum.
  - The verified `/stats` window recorded `543→77` tokens, below the fixed 5,000 original-Token acceptance gate. The returned analysis was discarded and scored zero.
- `dependency-resolution` / `paritok`: ORIGINAL_TOKEN_MINIMUM_NOT_MET: The verified stats delta was below the fixed case minimum.
  - The verified `/stats` window recorded `0→0` tokens, below the fixed 5,000 original-Token acceptance gate. The returned analysis was discarded and scored zero.
- `github-actions-environment` / `paritok`: ORIGINAL_TOKEN_MINIMUM_NOT_MET: The verified stats delta was below the fixed case minimum.
  - The verified `/stats` window recorded `0→0` tokens, below the fixed 5,000 original-Token acceptance gate. The returned analysis was discarded and scored zero.

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
