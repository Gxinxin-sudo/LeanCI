# Contributing to LeanCI

Thanks for helping improve LeanCI. This repository is a security-sensitive
hackathon MVP: changes must preserve the formal analysis chain
`FastAPI → local Paritok Proxy → Paritok hosted GPU → DeepSeek`.

## Before opening a change

- Read `AGENTS.md`, `PROJECT_PLAN.md`, `TASKS.md`, `SECURITY.md`, and the
  relevant architecture or deployment document.
- Create a focused branch and keep unrelated local changes out of the commit.
- Never commit `.env`, API keys, access tokens, private CI logs, provider
  responses, traces, or credentials. Use repository samples or synthetic data.
- Do not add arbitrary shell execution, repository cloning, arbitrary file
  reads, user-provided URL fetching, or automatic execution of model output.
- Do not add a direct-DeepSeek fallback to formal `/api/analyze`.

## Local setup

Use Python 3.11+ and Node.js 20.19+/22.12+ or a compatible newer release.
From the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install --requirement backend\requirements-dev.txt

cd frontend
npm ci
cd ..
```

Copy `.env.example` to the Git-ignored `.env` only when local integration work
needs it. Keep both keys empty for ordinary unit tests.

## Required checks

Run the checks that cover the changed area. Before a pull request, run the full
no-cost gate:

```powershell
.\backend\.venv\Scripts\python.exe -m ruff format --check backend
.\backend\.venv\Scripts\python.exe -m ruff check backend
.\backend\.venv\Scripts\python.exe -m pytest backend\tests
.\backend\.venv\Scripts\python.exe scripts\scan_secrets.py

cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

Docker changes also require the static Docker checks and, once the image builds,
the no-cost `scripts/docker_smoke.py` lifecycle test described in
`docs/DOCKER.md`.

Real Paritok/DeepSeek integrations and live benchmarks are opt-in and may incur
cost. Never run them as part of a default test command or CI job. They require
the script's explicit confirmation flag and the operator's authorization.

## Tests and documentation

- Add regression coverage for normal behavior, failure behavior, and relevant
  security boundaries.
- Keep Python data boundaries strict with Pydantic and TypeScript in strict mode.
- Do not hide, delete, or weaken a failing test to make a change pass.
- Update `README.md`, relevant `docs/` pages, `.env.example`, and `TASKS.md`
  whenever behavior, configuration, pricing snapshots, or manual steps change.
- Token values must come from the current request's verified Paritok `/stats`
  delta. Never estimate or synthesize Token metrics.

## Pull requests

Explain the problem, the chosen boundary-preserving solution, files changed,
checks run, and any skipped or externally blocked verification. Keep generated
artifacts and local runtime files out of the diff.

Report security issues privately using the process in `SECURITY.md`; do not open
a public issue containing exploitable details or secrets.
