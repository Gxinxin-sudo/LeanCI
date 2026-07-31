# Deploying LeanCI on Railway

This guide describes a single-service Railway deployment. Railway's interface and
policies can change; check its current documentation for
[Dockerfiles](https://docs.railway.com/builds/dockerfiles),
[variables](https://docs.railway.com/variables),
[domains](https://docs.railway.com/networking/domains/working-with-domains),
[health checks](https://docs.railway.com/deployments/healthchecks), and
[rollback](https://docs.railway.com/deployments/deployment-actions).

## Topology

```text
Railway HTTPS domain -> FastAPI on 0.0.0.0:$PORT
                         |-- compiled React at /
                         `-- Paritok on 127.0.0.1:8080
                              -> hosted GPU -> DeepSeek
```

Do not create a public domain, TCP proxy, or port mapping for 8080. The Dockerfile
does not accept credentials as build arguments, and `.dockerignore` excludes
environment files.

## What counts as a verified deployment

A healthy deployment requires:

1. Railway builds the root `Dockerfile` for the intended commit.
2. Deploy logs show Paritok health before FastAPI starts.
3. The service remains active and `/api/health` returns the expected JSON.
4. `paritok_connected=true`, `hosted_gpu_available=true`, and
   `deepseek_called=false` on the health response.
5. The homepage and `/api/samples` share the same domain.
6. Port 8080 is not public.

Health does not prove that a paid analysis succeeded. A public analysis endpoint
also needs the authenticated gateway and shared abuse controls described below.

## 1. Verify the image locally

```powershell
docker build --progress=plain --tag leanci:latest .
$env:LEANCI_DOCKER_CLI = (Get-Command docker).Source
.\backend\.venv\Scripts\python.exe scripts\docker_smoke.py
```

The smoke test is free, ignores `.env`, and should return top-level
`"status":"passed"`.

## 2. Create the Railway service

1. Push the target commit to GitHub and confirm `.env` is absent.
2. In Railway, choose **New Project** and **Deploy from GitHub repo**.
3. Grant the Railway GitHub app access only to the required repository.
4. Select `LeanCI` and the `main` branch.
5. Create one web service. `docker-compose.yml` is for local use only.
6. Keep Root Directory at the repository root.

The checked-in `railway.json` selects the root Dockerfile and `/api/health`:

```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 60
  }
}
```

Do not add a custom start command. The image entrypoint must remain PID 1.

## 3. Add runtime variables

Add variables in the service's **Variables** page. Seal secret values when the
platform offers that option.

Required secrets:

| Variable | Purpose |
| --- | --- |
| `DEEPSEEK_API_KEY` | Dedicated DeepSeek key |
| `PARITOK_API_KEY` | Dedicated Paritok key |
| `PROXY_AUTH_SHARED_SECRET` | Random gateway-to-FastAPI secret for production |

Required non-secret configuration:

| Variable | Value or requirement |
| --- | --- |
| `LLM_PROVIDER` | `paritok` |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` |
| `ENVIRONMENT` | `production` for a public analysis service |
| `CORS_ALLOWED_ORIGINS` | Exact HTTPS frontend origin |
| `TRUSTED_PROXY_CIDRS` | Private CIDR of the authenticated gateway; never `0.0.0.0/0` |
| `DISTRIBUTED_RATE_LIMIT_REQUIRED` | `true` only after shared enforcement exists |
| `DAILY_ANALYSIS_REQUEST_BUDGET` | Approved positive UTC daily limit |
| `DATA_RETENTION_HOURS` | `24` or less |
| `PRICING_SNAPSHOT_DATE` | `2026-07-31` |

Railway injects `PORT`; do not normally set it yourself. Fixed Paritok and DeepSeek
URLs must not be overridden.

## Production boundary

A directly public Railway container supplies TLS termination but is not the
authenticated OIDC gateway required by LeanCI's production mode. It also does not
prove shared atomic rate limiting or a daily paid-request budget.

Therefore a direct Railway service can safely expose the static app and health
checks, but formal `POST /api/analyze` should remain unavailable until an upstream
gateway:

- authenticates the user;
- strips client-supplied internal headers;
- injects the shared secret and principal from a trusted private CIDR;
- enforces distributed rate limits and the UTC daily budget;
- prevents direct public access to the container.

Do not work around this boundary by publishing development mode, trusting all
CIDRs, or placing the shared secret in React, a cookie, a URL, or a browser request.
See [production deployment](PRODUCTION_DEPLOYMENT.md).

## 4. Inspect deployment logs

Expected startup order:

```text
LeanCI container starting Paritok on 127.0.0.1:8080 and FastAPI on 0.0.0.0:<PORT>.
Paritok process started with PID <pid>.
Paritok /health is ready; starting FastAPI.
FastAPI process started with PID <pid>.
LeanCI container services are ready.
```

Common failures:

| Log | Action |
| --- | --- |
| `Missing required runtime secret variables` | Add the missing variable name; do not print its value |
| `Paritok process could not be started` | Inspect image dependencies and build logs |
| `Paritok exited during startup` | Reject the deployment and inspect proxy configuration |
| `Paritok did not become healthy` | Confirm loopback port 8080 and runtime configuration |
| `FastAPI exited during startup` | Correct production environment validation errors |
| `Paritok exited unexpectedly` | PID 1 will stop FastAPI and fail the container |

Do not copy possible credential material into an issue. Revoke a key immediately if
a third-party log appears to contain it.

## 5. Create and verify the domain

In **Service -> Settings -> Networking**, generate one domain. Do not create a TCP
proxy. Update `CORS_ALLOWED_ORIGINS` to that exact HTTPS origin and redeploy.

Use bounded checks:

```powershell
$domain = "https://<your-domain>"
$health = Invoke-RestMethod "$domain/api/health" -TimeoutSec 30
$health | Select-Object status,service,paritok_connected,hosted_gpu_available,model,deepseek_called
Invoke-WebRequest "$domain/" -TimeoutSec 30 | Select-Object StatusCode
Invoke-RestMethod "$domain/api/samples" -TimeoutSec 30 | Measure-Object
```

Expected health fields:

```json
{
  "status": "ok",
  "service": "leanci-api",
  "paritok_connected": true,
  "hosted_gpu_available": true,
  "model": "deepseek-v4-flash",
  "deepseek_called": false
}
```

Do not publish port 8080 for diagnostics. Use bounded deployment logs instead.

## 6. Verify formal analysis only after the gateway

Once the production gateway and shared counters are active, run one fixed sample
at a time and wait no more than 115 seconds. Record only the request ID, timestamp,
HTTP status, fixed model, and request-scoped token proof. Do not record request
bodies or credentials.

A low-yield passthrough or hosted failure must not be presented as token savings.

## 7. Roll back safely

Roll back only to a deployment that was previously verified. After rollback:

1. inspect the new deployment logs;
2. confirm restored variables do not reference revoked keys or an old domain;
3. recheck `/api/health`, the homepage, and samples;
4. repeat one fixed analysis only if the production gateway is available.

If a credential leak caused the rollback, revoke and replace the key before
redeploying. Never restore a compromised secret.
