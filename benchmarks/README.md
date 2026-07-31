# Benchmarks

This directory contains the frozen, auditable results for five deterministic CI
failure cases:

- `results.json`: structured runs, model output, deterministic scores, and human
  review fields.
- `results.csv`: the same required fields in a flat format.
- `report.md`: methodology, every result row, limitations, cost assumptions, and
  reproduction commands.

## Fairness controls

Each case runs in this fixed order:

1. `baseline_uncompressed`
2. `paritok`

Both routes use the same `deepseek-v4-flash` model, initial messages, sample
content, system and user prompts, `max_tokens=4096`, disabled thinking mode, and
JSON Object configuration. `initial_messages_sha256` must match for each pair.
The only intended variable is whether the request passes through Paritok.

Baseline rows do not pass through Paritok, so their `original_tokens`,
`compressed_tokens`, `tokens_saved`, and `compression_ratio` values are `null`.
LeanCI never substitutes DeepSeek usage or character counts for Paritok metrics.
Paritok token fields are populated only when the request-scoped `/stats` delta
proves compression occurred.

Paritok may intentionally pass through low-yield input. A request confirmed by the
official trace as `below_refusal_threshold` is recorded as
`skipped_low_yield`; its compression fields remain `null`, not zero. If that
request still returns valid structured output, its quality is scored normally.

Quality is scored against each case's `ground_truth.json`, without an LLM judge:

- root cause: 40 points
- evidence: 20 points
- relevant files: 15 points
- fix direction: 15 points
- valid strict JSON: 10 points

No result row is filtered out. Unavailable and upstream-failed rows keep a `null`
quality score when no valid diagnosis exists. Every row also contains a
`human_review` field.

## Run the benchmark

Start the Paritok proxy and confirm the hosted GPU preflight first. Every command
below is a paid, opt-in operation. It normally makes two model requests; each route
allows at most one JSON repair, for a hard limit of four requests per command.
Network retries are disabled.

```powershell
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case python-pytest
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case typescript-build
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case docker-build
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case dependency-resolution
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case github-actions-environment
```

Without `--confirm-cost`, the command makes zero model requests. A complete
five-case run normally makes ten requests and has a hard limit of twenty if every
route needs its one allowed JSON repair.

## Frozen result

The controlled run on 2026-07-26 made ten model requests, with no JSON repair,
network retry, or timeout. All ten rows are preserved:

- five completed baseline rows
- two `compressed` Paritok rows (Python and Docker)
- three `skipped_low_yield` Paritok rows
- no unavailable or upstream-failed rows

Across the two rows where compression actually occurred, mean token savings were
`85.53%`. Across the five valid baseline/Paritok quality pairs, the deterministic
score changed from `73.00/100` to `54.00/100` (`-19.00` points).

These results do **not** support claims that all five cases were compressed, that
quality was preserved, that the service is production-ready, or that the estimated
USD value is an actual bill reduction.

The artifact verification test locks the ten-row shape, required fields, matching
message and schema hashes, fixed inputs, status/token null semantics, averaging
denominator, quality pairing, and cost disclaimer. Frozen artifacts retain their
run-time pricing snapshot date of 2026-07-25.
