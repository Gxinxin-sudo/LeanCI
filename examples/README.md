# Deterministic CI failure samples

LeanCI ships five local, repeatable CI failure cases with known answers. No sample
clones a repository, fetches a user URL, or executes code.

| ID | Failure type | Log size | Related files | Root cause |
| --- | --- | ---: | ---: | --- |
| `python-pytest` | Python pytest | 69.5 KiB | 3 | Operator precedence makes the fourth backoff value 15 instead of the cap of 16 |
| `typescript-build` | TypeScript build | 73.9 KiB | 3 | A `string \| undefined` value is assigned to a required `string` setting |
| `docker-build` | Docker BuildKit | 40.1 KiB | 3 | `*.json` in `.dockerignore` removes `package-lock.json` from the build context |
| `dependency-resolution` | npm dependency resolution | 63.6 KiB | 2 | React 19 conflicts with a peer dependency that accepts React 18 only |
| `github-actions-environment` | GitHub Actions environment | 56.2 KiB | 2 | An unset repository variable leaves `DEPLOY_ENV` empty |

Each directory contains:

- `ci.log`: a long, secret-free CI log that is treated as untrusted text.
- A small set of relevant source or configuration files.
- `ground_truth.json`: the expected root cause, files, fix direction, and minimum
  source-token requirement used by deterministic scoring.
- For the first three samples, `demo_result.json`: a saved result and sanitized
  Paritok `/stats` snapshots from a real hosted-GPU run.

The application sends only `ci.log` and the related text files to the model.
`ground_truth.json` is never included in model context. Sample APIs accept a fixed
ID, not a filesystem path.

## Rebuild the deterministic logs

This command writes fixed text fixtures and does not run the sample projects:

```powershell
.\backend\.venv\Scripts\python.exe scripts\generate_demo_samples.py
```

## Refresh saved hosted-GPU results

The commands below call Paritok and DeepSeek and may incur DeepSeek charges. Each
command accepts one fixed sample and waits up to about 110 seconds.

```powershell
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample python-pytest
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample typescript-build
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample docker-build
```

Without `--confirm-cost`, the command returns
`skipped:COST_CONFIRMATION_REQUIRED` and sends no model request.

## Saved results

The saved 2026-07-26 runs produced these request-scoped Paritok `/stats` deltas:

| ID | Original tokens | Compressed tokens | Tokens saved | Savings |
| --- | ---: | ---: | ---: | ---: |
| `python-pytest` | 23,906 | 332 | 23,574 | 98.61% |
| `typescript-build` | 20,542 | 847 | 19,695 | 95.88% |
| `docker-build` | 8,325 | 117 | 8,208 | 98.59% |

These are historical observations for the saved requests, not guarantees for new
input or future service behavior.
