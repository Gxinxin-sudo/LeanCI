# LeanCI production security runbook

LeanCI must not be exposed directly to the internet:

```text
Browser → HTTPS + OIDC gateway + distributed limits/budget → LeanCI container
                                                        ↳ localhost Paritok → hosted GPU → DeepSeek
```

The gateway is the only public endpoint. It terminates TLS, authenticates the browser, removes
client-provided internal identity headers, then inserts fresh headers before proxying to LeanCI.
FastAPI rejects `POST /api/analyze` unless the socket peer is in `TRUSTED_PROXY_CIDRS`, the
gateway shared secret matches, and `X-LeanCI-Principal` is a valid authenticated subject. This is
an application-side backstop; it does not replace gateway authentication.

## Required production environment

Set these values in the deployment platform's secret/environment manager, never in the repository:

```dotenv
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://app.example.com
TRUSTED_PROXY_CIDRS=<only the gateway's private CIDR(s)>
PROXY_AUTH_SHARED_SECRET=<new random secret, 32+ bytes>
PROXY_AUTH_HEADER=x-leanci-proxy-auth
PROXY_PRINCIPAL_HEADER=x-leanci-principal
DISTRIBUTED_RATE_LIMIT_REQUIRED=true
DAILY_ANALYSIS_REQUEST_BUDGET=<approved maximum analyses per UTC day>
DATA_RETENTION_HOURS=24
```

Production startup intentionally fails if the CORS origin is not HTTPS, the trusted proxy network
or internal secret is missing, distributed limiting is not declared, or the daily budget is zero.
`CORS_ALLOWED_ORIGINS` is an exact comma-separated origin allowlist: no wildcard, path, query,
credential, or trailing slash. CORS is not authentication.

## Gateway requirements

Configure the chosen managed gateway, reverse proxy, or service mesh with all of the following.

1. Force HTTPS and redirect HTTP; use an automatically renewed certificate. Do not publish the
   container port or Paritok port `8080` directly. Restrict container ingress to the gateway's
   private network/CIDR.
2. Require OIDC login (MFA where available) for `/api/analyze`; allow unauthenticated health
   probing only from the platform health checker. The gateway must validate issuer, audience,
   signature, expiry, and nonce/session protections supplied by the identity provider.
3. Before proxying, remove `X-LeanCI-Proxy-Auth` and `X-LeanCI-Principal` from the browser
   request. After successful authentication, set `X-LeanCI-Proxy-Auth` to the deployment secret
   and `X-LeanCI-Principal` to a stable non-email subject such as the OIDC `sub` claim. Do not put
   either value in browser JavaScript, local storage, URLs, access logs, or error pages.
4. Enforce request limits before buffering: 4 MiB total body, `POST /api/analyze` only, and no
   request-content logging. Set connect/read/write timeouts no higher than LeanCI's 110-second
   analysis timeout; use an upstream timeout of 115 seconds or less and return a generic timeout.
5. Use a shared Redis-compatible store or gateway-native distributed counter keyed by the
   authenticated subject, with a second IP-based abuse rule. Start conservatively: 5 analyses per
   subject per 60 seconds, 120 API requests per subject per 60 seconds, and a stricter unauthenticated
   health rule. Reject on storage failure; do not silently fall back to per-instance memory.
6. Enforce `DAILY_ANALYSIS_REQUEST_BUDGET` atomically in that shared store before proxying an
   analysis. Use a UTC-day key with expiry at the next UTC midnight, alert at 80% and 100%, and
   reject at 100% without calling the model. This is a request-count safety cap, not a financial
   invoice; set a provider-side hard spend limit independently.

Redis supports async clients and expiring keys, which is suitable for bounded distributed counters;
each counter key must have an expiry rather than being retained indefinitely. See the official
[Redis asyncio client guidance](https://redis.io/docs/latest/develop/clients/redis-py/async/) and
[key-expiration documentation](https://redis.io/docs/latest/commands/expire/).

## Data retention policy

LeanCI processes request bodies, files, prompts, and model responses in memory only. It must not
add application persistence for them. Configure every surrounding system explicitly:

| Data | Maximum retention | Required control |
| --- | ---: | --- |
| LeanCI request content and model output | 0 (not persisted) | Disable request/response/debug-body logs; keep `DEBUG_RESPONSE_DIR` unset in production. |
| Gateway access metadata | 24 hours | Log only timestamp, route class, status, duration, opaque request ID and pseudonymous principal hash; exclude bodies, headers, query strings and raw IP where possible. |
| Distributed rate/budget counters | `DATA_RETENTION_HOURS` or less | Store pseudonymous subject hashes only; attach TTL on creation; do not persist full identities. |
| Platform backups, traces and error reporting | 7 days or less | Disable payload capture, access-restrict, encrypt, and verify deletion/expiry with the provider. |
| Paritok and DeepSeek submitted content | Provider policy | Obtain approval for private source/personal data and document the provider's current retention terms before go-live. |

The operator must keep a deletion procedure for accidental debug artifacts or platform logs. Do not
attempt bulk deletion from this repository; use the hosting provider's audited retention controls.

## Release verification

1. Confirm direct public access to the container port is blocked.
2. Confirm spoofed internal headers outside `TRUSTED_PROXY_CIDRS` receive 401.
3. Confirm authenticated gateway requests are rate-limited by principal across two application instances.
4. Confirm a Redis/gateway outage fails closed and the daily counter rejects work at its limit.
5. Inspect proxy, platform and error-reporting settings to prove bodies, authorization headers,
   model responses, and internal headers are excluded; verify configured TTLs.
6. Test certificate renewal, health checks, provider spend cap, alert delivery, backup retention,
   and credential rotation. Record only request IDs and timestamps, never secrets.
