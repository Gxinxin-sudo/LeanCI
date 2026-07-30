# Paritok Hackathon Feedback Template

Use this as a draft for one focused `hackathon-feedback` issue. Recheck the latest Paritok version
before posting and remove any field that cannot be supported by a public reproduction. Never attach
API keys, authenticated URLs, private dashboard data, raw user logs, or ignored runtime traces.

## Title

`[hackathon-feedback] Expose request-level compression outcome and stats for safe attribution`

## Project and environment

- Project: LeanCI — long CI log diagnosis
- Public reproduction: `https://github.com/Gxinxin-sudo/LeanCI`
- Paritok integration baseline: `paritok[proxy]==1.2.7`
- Path: local OpenAI-compatible Proxy → hosted GPU → DeepSeek
- Model: `deepseek-v4-flash`
- OS/container: Windows development and Linux Docker runtime

## What worked well

- The OpenAI-compatible Proxy kept the DeepSeek integration small.
- Hosted GPU compression produced large, directly measurable reductions on noisy long-log cases.
- Cumulative `/stats` made it possible to independently verify that compression occurred.
- The hosted trace reason `below_refusal_threshold` clarified that `0→0` can be an intentional
  low-yield pass-through rather than an outage or cache hit.

## Reproducible friction

LeanCI needs to prove Token values for one user request. Because `/stats` is process-cumulative, the
application currently requires one worker, a process lock, before/after snapshots, monotonicity
checks, and request-count matching. Concurrent traffic can otherwise contaminate attribution.

In the frozen five-case run, two Paritok requests had measurable compression and three incremented
`total_requests` while Token counters remained `0→0`. Official trace diagnostics identified all
three as `below_refusal_threshold`. The application can classify this only after a separate trace
workflow; the ordinary Proxy response and stats snapshot do not expose the skip reason.

## Suggested improvement

Return a non-secret request identifier and a structured per-request outcome, for example:

```json
{
  "request_id": "opaque-id",
  "outcome": "compressed | skipped_low_yield | failed",
  "skip_reason": "below_refusal_threshold",
  "input_tokens_original": 10469,
  "input_tokens_compressed": 254,
  "tokens_saved": 10215
}
```

Possible delivery mechanisms:

1. response headers plus a request-scoped stats endpoint;
2. an opt-in response metadata object that is not forwarded to the upstream model;
3. an authenticated local event stream keyed by opaque request ID.

The fields should distinguish pass-through, cache behavior, hosted unavailability, and actual
compression. Documentation should state whether `total_requests` counts attempted, passed-through,
or compressed requests.

## Why it matters

Request-level telemetry would let applications safely support concurrency and multiple workers,
avoid treating an intentional skip as a failure, and report Token reduction without guessing from
text length or upstream usage. It would also make hackathon evidence easier for judges to audit.

## Public evidence

- `benchmarks/report.md` — all ten frozen rows and skip outcomes.
- `docs/ARCHITECTURE.md` — current stats isolation and fail-closed design.
- `backend/app/paritok.py` — strict cumulative snapshot/delta logic.

## Security and privacy note

Request identifiers should be opaque and must not encode the API key, prompt, upstream response, user
identity, or account data. Per-request metadata should have a documented retention policy.
