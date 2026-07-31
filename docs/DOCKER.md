# Docker build and verification

The LeanCI image contains the compiled React application, FastAPI, and a loopback
Paritok proxy:

```text
Browser -> FastAPI + static React on the platform PORT
                     |
                     v
             Paritok on 127.0.0.1:8080
                     |
                     v
             Hosted GPU -> DeepSeek
```

The image runs as the fixed non-root user `10001:10001`. A Python PID 1 starts one
Paritok proxy and one Uvicorn worker. If either child exits, PID 1 terminates the
other and exits the container. Only the FastAPI port is exposed.

## Requirements

- Docker Desktop with the engine running.
- A Git-ignored root `.env` for live analysis.
- Both `DEEPSEEK_API_KEY` and `PARITOK_API_KEY` for live analysis.
- `LLM_PROVIDER=paritok`.
- A valid `PORT` other than the internal proxy port `8080`.

Secrets are runtime variables only. Never pass them as build arguments or copy
`.env` into the image.

## Build

From the repository root:

```powershell
docker build --progress=plain --tag leanci:latest .
```

The multi-stage build compiles the frontend, installs a CPU-only pinned PyTorch
wheel, and then installs `paritok[proxy]==1.2.7`. A first build can take several
minutes on a slow connection because of the Python ML dependencies.

## Free smoke test

```powershell
$env:LEANCI_DOCKER_CLI = (Get-Command docker).Source
.\backend\.venv\Scripts\python.exe scripts\docker_smoke.py
```

The smoke test uses fixed fake credentials, ignores `.env`, and does not call
DeepSeek. It verifies:

- non-root execution, fixed entrypoint, and one exposed port;
- no credential pattern or `/app/.env` in image configuration or history;
- safe exit code `78` when runtime secrets are missing;
- the static app, configuration status, five samples, and frozen benchmark;
- combined FastAPI, local proxy, and hosted-GPU health behavior;
- internal `/stats` availability without a public proxy port;
- fail-closed analysis before DeepSeek when fake credentials are used;
- linked failure when either managed child process exits.

Success is one JSON line with top-level `"status":"passed"`.

## Live container verification

These commands call Paritok and DeepSeek and may incur DeepSeek charges. Each
command runs one fixed sample, has no orchestration retry, and must finish within
120 seconds.

```powershell
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample python-pytest
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample typescript-build
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample docker-build
```

The script passes `.env` to Docker without reading or printing its values. It
compares the container's before/after `/stats` delta with the API response, verifies
the fixed model, sends SIGTERM to PID 1, checks a clean exit, and removes only the
single container it created.

A fixed sample may be accepted as `skipped_low_yield` only when all of these are
true:

- the API returns `503 PARITOK_COMPRESSION_SKIPPED`;
- the internal delta is exactly one request and zero token counters;
- the model remains `deepseek-v4-flash`;
- the container exits cleanly.

No token value is invented for a skipped request.

## Docker Compose

```powershell
docker compose up --build --detach
docker compose ps
Invoke-WebRequest "http://127.0.0.1:8000/"
Invoke-RestMethod "http://127.0.0.1:8000/api/config-status"
docker compose down
```

Compose binds FastAPI to the host loopback interface, does not publish port 8080,
drops Linux capabilities, and enables `no-new-privileges`. The two HTTP checks
above do not call a model.

For a non-default `PORT`, adjust the example URL. A public deployment also requires
an authenticated TLS gateway, exact CORS origins, distributed rate limiting, a
daily paid-request budget, and an explicit retention policy.

## Verified reference result

The image built and passed the free smoke test on 2026-07-27. The controlled live
container run produced:

| Sample | Outcome | Requests | Original | Compressed | Saved | Exit |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `python-pytest` | `compressed` | 1 | 10,469 | 254 | 10,215 | 0 |
| `typescript-build` | `skipped_low_yield` | 1 | 0 | 0 | 0 | 0 |
| `docker-build` | `compressed` | 1 | 543 | 144 | 399 | 0 |

These are historical observations, not guarantees for new input. See
[Railway deployment](DEPLOY_RAILWAY.md) and
[production deployment](PRODUCTION_DEPLOYMENT.md) for hosted operation.
