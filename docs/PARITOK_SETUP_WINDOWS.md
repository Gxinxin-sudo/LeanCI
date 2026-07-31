# Paritok hosted GPU setup on Windows

LeanCI pins `paritok[proxy]==1.2.7`. The configuration below matches that package
version and the current repository implementation.

## Install

From the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install "paritok[proxy]==1.2.7"
.\backend\.venv\Scripts\python.exe -m pip install --requirement backend\requirements-dev.txt
```

Confirm the CLI:

```powershell
.\backend\.venv\Scripts\paritok.exe --version
.\backend\.venv\Scripts\paritok.exe proxy --help
```

## Local secrets

Create `.env` only if it does not already exist:

```powershell
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item ".env.example" ".env"
}
```

Fill the two secret values locally:

```dotenv
PARITOK_API_KEY=
DEEPSEEK_API_KEY=
LLM_PROVIDER=paritok
DEEPSEEK_MODEL=deepseek-v4-flash
PARITOK_PROXY_BASE_URL=http://127.0.0.1:8080/v1
PARITOK_HEALTH_URL=http://127.0.0.1:8080/health
PARITOK_STATS_URL=http://127.0.0.1:8080/stats
```

Do not put credentials in `paritok.yaml`, source code, tests, screenshots, command
output, or Git. Paritok reads `PARITOK_API_KEY` from the process environment.
FastAPI sends `DEEPSEEK_API_KEY` to the loopback proxy, which forwards it only to
the fixed DeepSeek endpoint.

## Configuration

The root [paritok.yaml](../paritok.yaml) uses:

- `use_gpu_server: true`
- hosted server URL, model, timeout, and empty YAML API-key field
- compression thresholds
- history controls
- passthrough tool discovery
- disabled trace by default

Tool discovery is `passthrough` because LeanCI does not accept a user-provided tool
catalog. This avoids the optional local embedding selector without changing hosted
context compression.

## Start locally

Use three PowerShell terminals, all opened at the repository root.

Terminal 1:

```powershell
.\scripts\start_paritok.ps1
```

The script reads the ignored `.env`, performs an authenticated hosted-GPU
preflight, and then starts an equivalent fixed command:

```powershell
.\backend\.venv\Scripts\paritok.exe proxy `
  --host 127.0.0.1 `
  --port 8080 `
  --config-file paritok.yaml `
  --openai-url "https://api.deepseek.com/chat/completions" `
  --log-level info
```

Terminal 2:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app `
  --app-dir backend `
  --host 127.0.0.1 `
  --port 8000 `
  --workers 1
```

Keep one worker. Request attribution depends on one process-local lock around the
before/after `/stats` window.

Terminal 3:

```powershell
Set-Location frontend
npm run dev
```

Open `http://127.0.0.1:5173`.

## Health checks

```powershell
Invoke-RestMethod "http://127.0.0.1:8080/health"
Invoke-RestMethod "http://127.0.0.1:8080/stats"
.\backend\.venv\Scripts\python.exe scripts\test_paritok_connection.py
Invoke-RestMethod "http://127.0.0.1:8000/api/health"
```

Local proxy health proves only that the process is alive. Formal analysis is
enabled only when the authenticated hosted-GPU check succeeds too.

## Linux and Docker

Inject `PARITOK_API_KEY` at runtime, then run:

```sh
./scripts/start_paritok.sh
```

The script binds only `127.0.0.1:8080` and uses the fixed DeepSeek Chat Completions
endpoint. A container process manager must supervise both the proxy and one-worker
FastAPI process. Never publish port 8080.

## Common errors

| Error | Meaning |
| --- | --- |
| `FORMAL_ANALYSIS_REQUIRES_PARITOK` | Set `LLM_PROVIDER=paritok` and restart FastAPI |
| `PARITOK_PROXY_UNAVAILABLE` | The proxy is down, port 8080 is occupied, or a local firewall blocked it |
| `PARITOK_GPU_UNAVAILABLE` | The hosted GPU is unreachable or the Paritok key is invalid |
| `PARITOK_STATS_UNAVAILABLE` | `/stats` timed out or failed strict validation |
| `PARITOK_ROUTE_NOT_VERIFIED` | Another client contaminated the shared stats window |
| `DEEPSEEK_AUTHENTICATION_FAILED` | The DeepSeek key is invalid or revoked |
| `DEEPSEEK_INSUFFICIENT_BALANCE` | The DeepSeek account has insufficient balance |
| `DEEPSEEK_TIMEOUT` | The upstream request exceeded its timeout |
| `DEEPSEEK_SERVER_ERROR` | DeepSeek returned a temporary server failure |

LeanCI discards the diagnosis when route proof fails and never creates replacement
token numbers.
