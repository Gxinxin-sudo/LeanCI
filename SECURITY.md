# LeanCI Security Policy

## Supported version

LeanCI is a hackathon MVP. Security fixes are applied to the current `main` branch only. There is
no long-term-support release line yet.

## Reporting a vulnerability

Until the public GitHub repository and private vulnerability reporting are enabled, do not publish
an exploitable report in a public issue. Contact the repository owner through a private channel and
include:

- the affected commit and component;
- a minimal, non-destructive reproduction;
- expected and observed behavior;
- impact and suggested mitigation, if known.

Never include API keys, access tokens, private CI logs, customer code, or other personal data in a
report. If a secret may have leaked, revoke it at the provider first; deleting it from the latest
commit is not sufficient because Git history and caches may retain it.

After the public repository exists, the owner must enable GitHub private vulnerability reporting
and replace this temporary contact procedure with the repository's private reporting URL.

## Security properties

LeanCI's formal analysis boundary is intentionally narrow:

- Formal analysis always follows FastAPI → local Paritok Proxy → Paritok hosted GPU → DeepSeek.
  It never falls back to a direct or Mock provider.
- Provider URLs, model names, execution modes, and filesystem paths cannot be supplied by an
  analysis request.
- API keys are read from runtime environment settings into `SecretStr` values and are never
  returned by public APIs.
- Logs and uploaded text are treated as untrusted data. They are role-isolated in the model
  request, and embedded instructions cannot replace the system policy.
- Model commands and patches are inert text. LeanCI has no shell, patch-application, repository
  clone, arbitrary-file-read, or user-URL-fetch endpoint.
- Analysis accepts only uncompressed UTF-8 `application/json` within fixed body, log, file-count,
  per-file, and aggregate-file limits. Server-side checks reject unsafe names, paths, extensions,
  control characters, invalid UTF-8, and binary or archive-like content.
- API responses receive a server-generated request ID, no-store and browser security headers.
  Errors use stable public messages and do not return headers, environment variables, stack traces,
  upstream bodies, or internal paths.
- CORS uses an explicit allowlist. A bounded in-memory rate limiter and a single active-analysis
  limit reject excess requests instead of building an unbounded paid-work queue.
- Access logs contain only request ID, method, a fixed route label, status, and duration. They do not
  log request headers, query strings, request bodies, uploaded content, or raw paths.
- Token metrics come only from the current request's verified Paritok `/stats` delta. LeanCI does
  not manufacture token data or substitute DeepSeek usage.
- The container runs as a fixed non-root user, exposes only FastAPI, keeps Paritok on loopback, and
  uses a fixed Python PID 1 to stop the sibling service if either child exits.

The detailed trust boundaries, abuse cases, controls, and residual risks are documented in
[`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).

## Privacy and data handling

LeanCI does not intentionally write pasted logs or uploaded files to permanent application storage.
The API processes them in memory. Formal analysis sends that content through Paritok and DeepSeek,
so their service terms, retention policies, and the operator's hosting/logging configuration still
apply. Do not submit secrets, credentials, personal data, or proprietary source unless you are
authorized to send it to both providers.

Downloaded reports and clipboard contents are created in the user's browser and remain under the
user's control. Local debug artifacts and browser-smoke artifacts are Git-ignored, but operators
must still protect or remove them according to their own retention policy.

## Safe testing

Use fixed repository samples or synthetic data. Do not test against systems, accounts, or data you
do not own. Do not run denial-of-service tests against hosted services, evade provider limits,
exfiltrate data, or trigger paid model calls without explicit authorization.

Before publishing a change, run:

```powershell
.\backend\.venv\Scripts\python.exe scripts\scan_secrets.py
.\backend\.venv\Scripts\python.exe -m pip_audit -r backend\requirements.txt
.\backend\.venv\Scripts\python.exe -m pip_audit -r backend\requirements-container.txt
.\backend\.venv\Scripts\python.exe -m pytest backend\tests

cd frontend
npm audit --omit=dev --audit-level=high
npm test
```
