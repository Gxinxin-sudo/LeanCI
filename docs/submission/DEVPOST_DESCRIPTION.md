# LeanCI — Devpost Description

## Inspiration

CI failures often hide one useful clue inside tens of thousands of repetitive log lines. Sending the
entire log to an LLM increases input usage, latency, and cost, while manually searching the log slows
down incident response. We built LeanCI to test whether context compression can make this real
developer workflow leaner without hiding the evidence a human needs to verify the answer.

## What it does

LeanCI accepts a long CI log and up to five related text files. With one click, it returns a strict,
reviewable diagnosis containing:

- a summary, root cause, and confidence;
- exact log evidence and relevant files;
- recommended changes and a Git diff;
- verification commands, risks, and missing information; and
- request-specific original, compressed, and saved Token counts.

The application never runs the uploaded code, suggested commands, or generated patch.

## How we built it

The frontend is React, TypeScript strict mode, Vite, and Tailwind CSS. FastAPI and Pydantic enforce
the server-side input and output boundaries. The application is packaged as one non-root Docker
container containing the compiled frontend, FastAPI, and a loopback-only Paritok Proxy supervised by
a Python PID 1 process.

Five fixed CI cases cover pytest, TypeScript, Docker, dependency resolution, and GitHub Actions
environment failures. Each case includes a long log, a small set of relevant files, and ground truth
that is used only for deterministic evaluation and is never sent to the model.

## How Paritok is used

Formal analysis has one fixed route:

`FastAPI → local Paritok Proxy → Paritok hosted GPU → DeepSeek API`.

Before a request, LeanCI checks the local Proxy, the authenticated hosted GPU endpoint, and Paritok
`/stats`. After the model response, it reads `/stats` again under the same single-analysis lock.
Original, compressed, and saved Token counts are accepted only from the before/after counter delta,
and `/stats.total_requests` must match the actual Provider request count. If health or proof is
missing, LeanCI fails closed. It does not fall back to an uncompressed formal request, Direct
DeepSeek, or Mock.

Paritok's own `estimated_cost_saved_usd` field is deliberately excluded because it may not use the
project's DeepSeek pricing assumptions.

## How DeepSeek is used

LeanCI uses the fixed `deepseek-v4-flash` model in non-thinking JSON mode with a strict diagnostic
schema. The model sees the CI evidence as explicitly untrusted tool content. An empty or invalid
response can trigger at most one schema-repair request, still through Paritok. Network, model, and
upstream URLs cannot be overridden by an analysis request.

## Challenges

The hardest challenge was proving that Token numbers belonged to the current request. Paritok
`/stats` is cumulative, so LeanCI uses one worker, one active-analysis lock, before/after snapshots,
monotonicity checks, and request-count matching.

We also found that `0→0` does not always mean an outage. Paritok's hosted trace showed that three
fixed benchmark cases were intentionally passed through as `below_refusal_threshold`. We preserve
those rows as `skipped_low_yield` with Token metrics marked not applicable instead of reporting
0% savings.

Finally, compressed answers did not always retain the same deterministic quality score. We kept the
negative result visible rather than optimizing the report for a marketing claim.

## Accomplishments

- Three saved end-to-end demo captures through Paritok hosted GPU and DeepSeek, each with independent
  `/stats` proof.
- A reproducible five-case Baseline-versus-Paritok benchmark with all ten rows retained.
- Strict fail-closed behavior when Paritok, hosted GPU, or stats proof is unavailable.
- A non-root single-container build with static frontend hosting and supervised Proxy/API lifecycle.
- Security boundaries for path traversal, request limits, binary input, prompt injection, error
  leakage, concurrency, CORS, rate limiting, and command/patch non-execution.

## What we learned

Token efficiency is not a single average. Compression can be excellent on one long noisy log and be
skipped on another input that the compressor considers low yield. Quality must be measured
separately from Token reduction, and skipped inputs must remain visible.

We also learned that cumulative telemetry is not sufficient by itself for a public claim. The
application needs request isolation and explicit proof that the observed counter movement belongs to
the current analysis.

## Benchmark results

The frozen acceptance run was generated on 2026-07-26. It made 10 model requests: five
`baseline_uncompressed` and five Paritok requests. There were 0 JSON repair requests, 0 network
retries, and 0 timeouts.

- 2 Paritok rows were actually compressed.
- 3 Paritok rows were normal `skipped_low_yield` pass-throughs.
- Across the 2 compressed rows only, average Token savings were **85.53%**:
  - Python pytest: `10,469 → 254` (**97.57%** saved).
  - Docker build: `543 → 144` (**73.48%** saved).
- Across 5 valid quality pairs, the deterministic average was Baseline **73.00/100** and Paritok
  **54.00/100**, a **-19.00 point** change.

These results do not establish universal compression, quality preservation, production reliability,
or actual billing savings. Full rows and methodology are published in `benchmarks/report.md`.

The separate three-case demo captures recorded `23,906 → 332`, `20,542 → 847`, and
`8,325 → 117`. Those values are also per-request Paritok `/stats` deltas and are not mixed into the
five-case benchmark average.

## Security

The backend enforces a 4 MiB request limit, a 2 MiB UTF-8 log limit, and up to five allowlisted text
files. It rejects path traversal, duplicate or reserved names, archives, executable/script uploads,
binary input, invalid UTF-8, and disallowed control characters.

Secrets are runtime-only. Errors and access logs do not expose keys, headers, request bodies, model
content, stack traces, or internal absolute paths. LeanCI does not persist submitted evidence, but
formal analysis sends it to Paritok and DeepSeek, so users must follow those providers' data policies.
A public production deployment additionally requires a TLS/OIDC gateway, shared rate limiting, a UTC
daily request budget, and key rotation.

## What is next

Next we will add an auditable authenticated public gateway and shared budget controls, then publish a
live demo. We also plan to expand the human-reviewed CI dataset, improve chunking for low-yield
inputs, make Token attribution request-scoped for multi-instance deployment, and contribute
reproducible feedback about skip semantics and telemetry to Paritok.

## Links to paste into Devpost

- Project URL: `https://github.com/Gxinxin-sudo/LeanCI`
- Public repository: `https://github.com/Gxinxin-sudo/LeanCI`
- Demo video: `[FILL: public YouTube or Vimeo URL]`
- Social post: `[FILL: public post URL with #BuiltWithParitok]`
- Paritok account email: `[FILL IN DEVPOST ONLY — never commit the email if private]`
