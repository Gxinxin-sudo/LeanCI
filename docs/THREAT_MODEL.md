# LeanCI Threat Model

## 1. Scope and security goals

This threat model covers the React client, FastAPI API, local Paritok Proxy, Paritok hosted GPU,
DeepSeek, fixed sample/benchmark artifacts, reports, logs, and CI workflow. It focuses on preventing:

- credential or private-content disclosure;
- arbitrary code, command, patch, file, or URL execution;
- traversal outside fixed repository assets;
- model prompt injection changing application authority;
- forged Token/cost evidence or Mock results entering formal analysis;
- unbounded request size, paid-work queues, or accidental retries;
- sensitive values leaking through errors, logs, reports, or Git.

LeanCI is an unauthenticated hackathon MVP, not a multi-tenant production service. The controls below
reduce exposure but do not replace authentication, a distributed quota system, an API gateway, or a
provider data-processing agreement.

## 2. Assets and trust boundaries

| Asset or boundary | Trust level | Rule |
| --- | --- | --- |
| API keys and runtime configuration | Secret/trusted | Runtime-only; never returned, logged, documented, or committed |
| Browser input and uploaded files | Untrusted | Validate at FastAPI; frontend checks are only user feedback |
| Fixed samples and captures | Repository-trusted | Resolve only from constant ID mappings within the expected root |
| Model output | Untrusted | Validate schema; render commands and patches as inert text |
| Paritok `/stats` | Trusted only after request proof | Use before/after delta and request-count match for this request |
| Paritok and DeepSeek services | External processor | Fixed URLs, bounded timeout/retry, fail closed |
| Access/application logs | Sensitive operational data | Log fixed metadata only; never headers, bodies, raw paths, or model content |
| Downloaded report/clipboard | User-controlled output | Escape Markdown structure; never execute content |

Formal data flow:

```text
Browser
  → FastAPI validation, rate/concurrency limits, request ID
  → local Paritok Proxy
  → Paritok hosted GPU
  → DeepSeek deepseek-v4-flash
  → strict result schema and verified /stats delta
  → inert browser rendering, clipboard, or Markdown download
```

There is no formal request switch for Provider, model, upstream URL, filesystem path, shell command,
patch application, or Baseline. Mock is limited to local development/tests; the Baseline provider
is limited to the explicitly confirmed benchmark workflow and is labeled uncompressed.

## 3. Abuse-case review

| Check | Control and verification | Residual risk |
| --- | --- | --- |
| API key reads | Pydantic settings read `.env`/environment into `SecretStr`; values are unwrapped only for the fixed provider authorization points | Compromised host/process can read process memory or environment |
| Current files and Git history | `scripts/scan_secrets.py` scans tracked/unignored files and every Git patch with high-confidence and entropy detectors; CI uses full history | Pattern scanners cannot prove absence of every possible custom credential |
| `.gitignore` | Ignores `.env*` except the empty example, keys/certificates, credential files, debug/runtime traces, build output, and local environments | Newly named secret files still require review and scanning |
| Header logging | Access logs contain request ID, method, fixed route label, status, duration only | Reverse proxy or hosting platform logs are outside this repository |
| Exception leakage | Stable error envelopes and explicit `debug=False`; regression test injects environment-like secrets/paths and asserts they are absent | Third-party/platform error pages must also be configured safely |
| Upload limits | 4 MiB request, 2 MiB UTF-8 log, 5 files, 256 KiB each, 1 MiB aggregate; streaming body guard covers missing/false `Content-Length` | Distributed traffic volume still needs edge limits |
| Filename cleanup | Unicode normalization and safe basename rules; duplicate names after normalization rejected | Display confusables that are otherwise valid may still confuse a reviewer |
| Path traversal | Reject separators, drives, dot segments, reserved names; fixed sample paths must resolve under the sample root | A compromised repository itself is trusted input |
| Content-type spoofing | Analysis requires exactly one UTF-8 `application/json` content type and identity encoding; file extensions and decoded text are independently validated | Plain text cannot reliably identify every domain-specific malicious payload |
| Oversized requests | ASGI body limiter stops streamed bodies beyond the cap before model work | Edge/server should enforce matching limits before buffering |
| Prompt injection | Logs/files are delimited untrusted tool-role data; fixed system policy and strict output schema remain authoritative | LLMs are probabilistic; human review of recommendations remains required |
| System instructions in logs | Fake `system`, `developer`, boundary-closing tags remain inside tool messages in regression tests | Novel semantic injection can still affect answer quality, not application authority |
| Model command execution | No execution endpoint; tests monkeypatch shell/subprocess and verify dangerous returned commands remain text | A user can choose to run copied commands outside LeanCI |
| Patch handling | React text rendering, exact clipboard copy, and escaped Markdown report; malicious HTML/Markdown stays text | External Markdown viewers have their own security model |
| Network timeout/retry | Local stats/health 3 s, hosted preflight 10 s, DeepSeek 60 s, full analysis 110 s; network retry cap 2 and JSON repair cap 1 | A request can consume its full bounded timeout and provider charges may still occur |
| Concurrent paid work | One active analysis; excess requests receive `ANALYSIS_BUSY`; service lock protects `/stats` deltas | In-memory state requires exactly one worker and is reset on restart |
| Request rate | Per-socket-peer sliding windows: 120 API/min and 5 analyses/min by default; bucket count bounded | No authentication; multi-worker/distributed limits and fair proxy identity require an external gateway |
| Request IDs | Server-owned random 128-bit ID replaces caller spoofing and appears in response/errors/safe access log | Correlation across external provider logs needs separate privacy-safe integration |
| Security headers | API no-store, CSP deny-all, frame denial, nosniff, no-referrer, permissions restriction, COOP | Frontend hosting must add equivalent document headers in production |
| CORS | Explicit validated HTTP(S) origin allowlist; no wildcard and no credentials | CORS is a browser control, not authentication |
| Privacy | Visible notice: LeanCI keeps no permanent upload storage; content is processed in memory and sent to Paritok/DeepSeek | Provider/platform retention and local downloaded files remain outside LeanCI |
| Token authenticity | Only verified Paritok `/stats` delta; request-count proof; missing proof fails closed | Correctness still depends on the external stats service |
| Mock isolation | Formal Provider factory cannot select Mock/Direct; formal endpoint has no mode parameter | Developers must not expose test-only app instances as production |

## 4. Security and product acceptance

Automated tests cover the normal path, invalid media types and encodings, streamed oversize bodies,
binary/disguised extensions, Unicode/path/reserved-name attacks, normalized duplicates, prompt
injection boundaries, inert commands/patches, exception redaction, CORS, request IDs, response
headers, rate limiting, concurrency, and timeouts.

The local browser smoke test uses an isolated Mock FastAPI process and fixed local ports. It verifies:

- the first page explains the product and exposes all five samples;
- loading/analyzing controls have explicit disabled states;
- failures remain retryable and timed-out results are not accepted;
- capture pages expose copy-patch and download-report actions;
- the benchmark is read-only and visually labeled;
- desktop and 390 px mobile pages are nonblank without horizontal overflow;
- there are no console, runtime, browser-log, or failed-network entries.

The smoke test never invokes Paritok or DeepSeek and cannot validate current external provider
availability. Frozen stage-five Token values remain the evidence for real formal runs; they are not
regenerated during this audit.

## 5. Residual risks and deployment requirements

Before internet exposure:

1. Put FastAPI behind a trusted TLS reverse proxy/API gateway with matching body limits, bounded
   timeouts, authenticated or abuse-resistant identity, and distributed rate/paid-budget limits.
2. Keep Uvicorn at one worker unless the `/stats` isolation, concurrency lock, and rate limiter move
   to shared transactional storage.
3. Set `CORS_ALLOWED_ORIGINS` to exact production frontend origins. Do not use `*`.
4. Configure the frontend host with document security headers equivalent to the API headers.
5. Review Paritok, DeepSeek, proxy, and hosting retention/logging policies; obtain the necessary
   authorization before sending private source or personal data.
6. Enable private vulnerability reporting, secret scanning, dependency alerts, and branch
   protection in the future public repository.
7. Rotate a credential immediately if exposure is suspected, then scan the full Git history and
   provider/platform logs. Never rely only on deleting the latest file.
