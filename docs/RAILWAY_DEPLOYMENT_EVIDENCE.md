# Railway deployment evidence

Snapshot date: 2026-07-28 (Asia/Shanghai)

This file records only non-secret deployment metadata. It intentionally excludes environment
variable values, request bodies, model output, authentication headers, payment information and
account credentials.

## Target

- Railway project: `fearless-quietude`
- Project ID: `2ccfcb2c-1d6f-40fd-90d0-9a48c6fb2a14`
- Environment: `production` (Railway environment name)
- Service: `LeanCI`
- Service ID: `f4f5279a-7982-4f08-95b6-ec490512ef60`
- Source: `Gxinxin-sudo/LeanCI`
- Branch: `main`
- Git commit: `76e265ec422a290ad68ff009302a1f35c5d6d450`
- Deployment ID: `228ab8b3-dd94-4b7b-9400-1df62814dd55`
- Instance ID: `3d08cdb5-99fc-4349-b7c8-63e35fee27c4`
- Image digest: `sha256:bf68e97c387cd0ae094069ca68cfe8f2b047a852107b13d08348194ef0a593ce`

## Verified state

- Deployment status: `SUCCESS`
- Instance status: `RUNNING`
- Builder: root `Dockerfile` selected by `/railway.json`
- Health path: `/api/health`
- Health timeout: 60 seconds
- Restart policy: `ON_FAILURE`, maximum 3 retries
- Application listener: `0.0.0.0:8000`, read from Railway `PORT`
- Internal Paritok listener: `127.0.0.1:8080`
- Startup log sequence verified: Paritok process, hosted GPU acceptance, Paritok `/health`,
  FastAPI process, application startup and combined services readiness
- Railway health gate passed: yes (the deployment reached `SUCCESS`)
- Public/custom service domains: none

Only `DEEPSEEK_API_KEY` and `PARITOK_API_KEY` were copied from the ignored local `.env`, through
`railway variable set --stdin --skip-deploys`. Their values were never printed or written here.
Railway `PORT=8000` resolves the platform default-port collision with internal Paritok.

## Security boundary

The Railway environment is named `production`, but the application is deliberately overridden to
`ENVIRONMENT=development` while there is no public domain and the user-selected deployment has no
OIDC gateway. This is an internal deployment and health verification only. It must not be described
or exposed as a production/public demo.

Before generating a domain:

1. rotate both provider keys and resync them without printing their values;
2. choose and review an equivalent trusted authentication boundary if OIDC remains out of scope;
3. implement distributed rate limiting and a UTC daily analysis budget;
4. change the application to validated production settings and use an exact HTTPS CORS origin;
5. verify the public `/api/health` JSON and authorized analysis path.

One failed startup before commit `76e265e` emitted a truncated environment-input fragment through
Pydantic's default validation error rendering. The fragment is not reproduced here. Commit
`76e265e` enables `hide_input_in_errors` and adds a regression test; provider-key rotation remains
required before public exposure because Railway's historical logs cannot be removed by this
repository.

## Failed attempts retained for audit

- Existing deployment `c29e851c-aa42-47c1-ad2a-af09c501854e`: Railway Metal builder rejected a
  BuildKit cache mount without an ID.
- Deployment `2f835783-f464-4fbd-a27d-bcba547707c9`: Railway required a private `cacheKey` ID
  convention, so the optional cache mount was removed instead of guessing platform syntax.
- Deployment `ef731753-27f9-4e9d-9860-a9cf9599164a`: Railway's default `PORT=8080` collided with
  internal Paritok; the service now supplies `PORT=8000`.
- Redeployment `c536e2dd-0121-4bdd-b5f9-0bb913535773`: production validation correctly rejected
  the missing HTTPS/gateway boundary and exposed the validation-error logging issue fixed in
  `76e265e`.

No failed attempt called the LeanCI analysis endpoint or intentionally invoked DeepSeek.
