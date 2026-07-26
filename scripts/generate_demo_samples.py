"""Generate deterministic, inert demo assets without running any sample code."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"


def write_text(relative_path: str, content: str) -> None:
    path = EXAMPLES_ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(relative_path: str, value: dict[str, object]) -> None:
    write_text(relative_path, json.dumps(value, indent=2, ensure_ascii=False))


def pytest_log() -> str:
    lines = [
        "Run python -m pytest -vv --maxfail=1",
        "============================= test session starts =============================",
        "platform win32 -- Python 3.12.13, pytest-8.4.2, pluggy-1.6.0",
        "cachedir: .pytest_cache",
        "rootdir: D:\\a\\retry-service\\retry-service",
        "configfile: pyproject.toml",
        "plugins: anyio-4.10.0, asyncio-1.2.0, cov-7.0.0",
        "asyncio: mode=Mode.STRICT, debug=False",
        "collecting ... collected 864 items",
        "",
    ]
    for index in range(1, 821):
        percentage = min(94, index * 100 // 864)
        lines.append(
            "tests/test_retry_matrix.py::test_retry_schedule"
            f"[base-0.5-attempt-{index:04d}] PASSED [{percentage:3d}%]"
        )
    lines.extend(
        [
            "tests/test_retry.py::test_zero_attempt_uses_base_delay PASSED             [ 95%]",
            "tests/test_retry.py::test_backoff_grows_exponentially PASSED              [ 95%]",
            "tests/test_retry.py::test_retry_backoff_caps_at_maximum FAILED            [ 95%]",
            "",
            "=================================== FAILURES ===================================",
            "___________________ test_retry_backoff_caps_at_maximum ____________________",
            "",
            "    def test_retry_backoff_caps_at_maximum() -> None:",
            "        policy = RetryPolicy(base_delay=2, max_delay=16)",
            "",
            ">       assert policy.delay_for(attempt=4) == 16",
            "E       assert 15 == 16",
            "E        +  where 15 = delay_for(attempt=4)",
            "E        +    where delay_for = RetryPolicy(base_delay=2, max_delay=16).delay_for",
            "",
            "tests\\test_retry.py:18: AssertionError",
            "=========================== short test summary info ===========================",
            "FAILED tests/test_retry.py::test_retry_backoff_caps_at_maximum - assert 15 == 16",
            "!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!",
            "======================== 1 failed, 823 passed in 9.84s ========================",
            "Error: Process completed with exit code 1.",
        ]
    )
    return "\n".join(lines)


def typescript_log() -> str:
    lines = [
        "Run npm ci --no-audit --no-fund",
        "npm info using npm@11.13.0",
        "npm info using node@v24.16.0",
        "added 412 packages in 4s",
        "",
        "Run npm run build:workspaces",
        "",
        "> release-dashboard@2.4.0 build:workspaces",
        "> turbo run build --output-logs=full",
        "",
        "turbo 2.5.6",
        "• Packages in scope: 320",
        "• Running build in 320 packages",
    ]
    for index in range(1, 321):
        package = f"@release-dashboard/package-{index:03d}"
        lines.extend(
            [
                f"{package}:build: cache hit, replaying logs {index:08x}",
                f"{package}:build: > tsc -b tsconfig.json --pretty false",
                f"{package}:build: Found 0 errors. Incremental state is current.",
            ]
        )
    lines.extend(
        [
            "",
            "@release-dashboard/deploy-config:build: cache miss, executing 00c1f41e",
            "@release-dashboard/deploy-config:build: > tsc -b tsconfig.json --pretty false",
            "",
            "src/config.ts(14,5): error TS2322: Type 'string | undefined' is not assignable to type 'string'.",
            "  Type 'undefined' is not assignable to type 'string'.",
            "",
            "14     region: process.env.DEPLOY_REGION,",
            "       ~~~~~~",
            "",
            "  src/config.ts(3,3)",
            "    3   region: string",
            "        ~~~~~~",
            "    The expected type comes from property 'region' which is declared here on type 'AppConfig'",
            "",
            "Found 1 error.",
            "npm error Lifecycle script `build` failed with error:",
            "npm error code 2",
            "npm error path D:\\a\\release-dashboard\\release-dashboard",
            "npm error command failed",
            "npm error command C:\\Windows\\system32\\cmd.exe /d /s /c tsc -b && vite build",
            "Error: Process completed with exit code 2.",
        ]
    )
    return "\n".join(lines)


def docker_log() -> str:
    lines = [
        "Run docker buildx build --progress=plain --tag demo-api:ci .",
        '#0 building with "default" instance using docker driver',
        "",
        "#1 [internal] load build definition from Dockerfile",
        "#1 transferring dockerfile: 612B done",
        "#1 DONE 0.0s",
        "",
        "#2 [internal] load metadata for docker.io/library/node:22.18.0-alpine",
        "#2 DONE 0.7s",
        "",
        "#3 [auth] library/node:pull token for registry-1.docker.io",
        "#3 DONE 0.0s",
        "",
        "#4 [internal] load .dockerignore",
        "#4 transferring context: 178B done",
        "#4 DONE 0.0s",
        "",
        "#5 [1/6] FROM docker.io/library/node:22.18.0-alpine@sha256:44d3b2f6f4e7c13a",
    ]
    for _ in range(1, 751):
        lines.append("BuildKit progress: downloading the base image layer.")
    lines.extend(
        [
            "#5 extracting sha256:8c2f1d4a7b09",
            "#5 extracting sha256:8c2f1d4a7b09 1.4s done",
            "#5 DONE 39.1s",
            "",
            "#6 [internal] load build context",
            "#6 transferring context: 3.14kB done",
            "#6 DONE 0.0s",
            "",
            "#7 [2/6] WORKDIR /app",
            "#7 DONE 0.1s",
            "",
            "#8 [3/6] COPY package.json package-lock.json ./",
            (
                "#8 ERROR: failed to calculate checksum of ref "
                'moby::m9g4j5h6k7l8: "/package-lock.json": not found'
            ),
            "------",
            " > [3/6] COPY package.json package-lock.json ./:",
            "------",
            "Dockerfile:5",
            "--------------------",
            "   3 |     WORKDIR /app",
            "   4 |",
            "   5 | >>> COPY package.json package-lock.json ./",
            "   6 |     RUN npm ci --omit=dev",
            "   7 |",
            "--------------------",
            (
                "ERROR: failed to solve: failed to compute cache key: "
                'failed to calculate checksum: "/package-lock.json": not found'
            ),
            "Error: buildx failed with: ERROR: failed to solve",
            "Error: Process completed with exit code 1.",
        ]
    )
    return "\n".join(lines)


def dependency_resolution_log() -> str:
    lines = [
        "Run npm ci --no-audit --no-fund",
        "npm info using npm@11.13.0",
        "npm info using node@v24.16.0",
        "npm http fetch GET 200 https://registry.npmjs.org/react 41ms (cache revalidated)",
        "npm http fetch GET 200 https://registry.npmjs.org/react-dom 38ms (cache revalidated)",
        "npm http fetch GET 200 https://registry.npmjs.org/@legacy-grid%2freact 52ms (cache revalidated)",
    ]
    for index in range(1, 701):
        lines.append(
            "npm sill idealTree buildDeps: resolved transitive package "
            f"@workspace/dependency-{index:04d}@1.0.{index % 17}"
        )
    lines.extend(
        [
            "npm error code ERESOLVE",
            "npm error ERESOLVE unable to resolve dependency tree",
            "npm error",
            "npm error While resolving: analytics-console@3.2.0",
            "npm error Found: react@19.2.0",
            "npm error node_modules/react",
            'npm error   react@"19.2.0" from the root project',
            "npm error",
            "npm error Could not resolve dependency:",
            'npm error peer react@"^18.2.0" from @legacy-grid/react@4.6.0',
            "npm error node_modules/@legacy-grid/react",
            'npm error   @legacy-grid/react@"4.6.0" from the root project',
            "npm error",
            "npm error Fix the upstream dependency conflict, or retry",
            "npm error this command with --force or --legacy-peer-deps",
            "npm error to accept an incorrect (and potentially broken) dependency resolution.",
            "npm error",
            "npm error A complete log can be found in: C:\\npm\\_logs\\eresolve-report.txt",
            "Error: Process completed with exit code 1.",
        ]
    )
    return "\n".join(lines)


def github_actions_environment_log() -> str:
    lines = [
        "2026-07-26T02:10:01.001Z Requested labels: ubuntu-latest",
        "2026-07-26T02:10:02.114Z Job is waiting for a hosted runner to come online.",
        "2026-07-26T02:10:04.219Z Job is about to start running on the hosted runner.",
        "2026-07-26T02:10:04.500Z Current runner version: '2.332.0'",
        "2026-07-26T02:10:04.501Z Operating System: Ubuntu 24.04.2 LTS",
        "2026-07-26T02:10:04.502Z Runner Image: ubuntu-24.04",
    ]
    for index in range(1, 651):
        lines.append(
            "2026-07-26T02:10:"
            f"{5 + index // 100:02d}.{index % 1000:03d}Z "
            f"Downloading action dependency layer {index:04d}/0650 from tool cache"
        )
    lines.extend(
        [
            "2026-07-26T02:10:15.010Z ##[group]Run python scripts/validate_env.py",
            "2026-07-26T02:10:15.011Z python scripts/validate_env.py",
            "2026-07-26T02:10:15.012Z shell: /usr/bin/bash -e {0}",
            "2026-07-26T02:10:15.013Z env:",
            "2026-07-26T02:10:15.014Z   DEPLOY_ENV:",
            "2026-07-26T02:10:15.015Z ##[endgroup]",
            "2026-07-26T02:10:15.101Z Traceback (most recent call last):",
            '2026-07-26T02:10:15.102Z   File "scripts/validate_env.py", line 8, in <module>',
            '2026-07-26T02:10:15.103Z     raise RuntimeError("DEPLOY_ENV is required")',
            "2026-07-26T02:10:15.104Z RuntimeError: DEPLOY_ENV is required",
            "2026-07-26T02:10:15.110Z ##[error]Process completed with exit code 1.",
        ]
    )
    return "\n".join(lines)


def generate_python_sample() -> None:
    root = "python-pytest"
    write_text(f"{root}/ci.log", pytest_log())
    write_text(
        f"{root}/src/retry.py",
        """
from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    base_delay: int
    max_delay: int

    def delay_for(self, attempt: int) -> int:
        return min(self.base_delay * 2**attempt - 1, self.max_delay)
""",
    )
    write_text(
        f"{root}/tests/test_retry.py",
        """
from src.retry import RetryPolicy


def test_zero_attempt_uses_base_delay() -> None:
    assert RetryPolicy(base_delay=2, max_delay=16).delay_for(attempt=0) == 1


def test_retry_backoff_caps_at_maximum() -> None:
    policy = RetryPolicy(base_delay=2, max_delay=16)
    assert policy.delay_for(attempt=4) == 16
""",
    )
    write_text(
        f"{root}/pyproject.toml",
        """
[tool.pytest.ini_options]
addopts = "-vv --maxfail=1"
testpaths = ["tests"]
""",
    )
    write_json(
        f"{root}/ground_truth.json",
        {
            "schema_version": 2,
            "case_id": root,
            "expected_root_cause": (
                "Operator precedence subtracts one after exponentiation, so attempt 4 "
                "returns 15 instead of the configured 16-second cap."
            ),
            "root_cause_term_groups": [
                ["15"],
                ["16"],
                ["- 1", "-1", "subtract", "precedence"],
            ],
            "expected_evidence": [
                {
                    "source": "ci.log",
                    "term_groups": [["assert 15 == 16", "15 == 16"]],
                },
                {
                    "source": "test_retry.py",
                    "term_groups": [["attempt=4"], ["== 16"]],
                },
            ],
            "expected_relevant_files": ["retry.py", "test_retry.py"],
            "expected_fix_direction": [
                "Make the intended backoff formula explicit with parentheses.",
                "Keep the cap test and add boundary cases around the maximum delay.",
            ],
            "fix_direction_term_groups": [
                ["parenthes", "formula", "remove - 1", "remove -1"],
                ["cap", "maximum", "boundary"],
            ],
            "minimum_original_tokens": 5000,
        },
    )


def generate_typescript_sample() -> None:
    root = "typescript-build"
    write_text(f"{root}/ci.log", typescript_log())
    write_text(
        f"{root}/src/config.ts",
        """
export interface AppConfig {
  apiBaseUrl: string
  region: string
}

export function loadConfig(): AppConfig {
  return {
    apiBaseUrl: process.env.API_BASE_URL ?? 'http://127.0.0.1:3000',
    region: process.env.DEPLOY_REGION,
  }
}
""",
    )
    write_text(
        f"{root}/src/deploy.ts",
        """
import { loadConfig } from './config'

const config = loadConfig()
console.log(`Preparing deployment for ${config.region}`)
""",
    )
    write_text(
        f"{root}/tsconfig.json",
        """
{
  "compilerOptions": {
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noEmit": true
  },
  "include": ["src"]
}
""",
    )
    write_json(
        f"{root}/ground_truth.json",
        {
            "schema_version": 2,
            "case_id": root,
            "expected_root_cause": (
                "DEPLOY_REGION is string | undefined, but loadConfig promises AppConfig "
                "with a required string region."
            ),
            "root_cause_term_groups": [
                ["deploy_region"],
                ["undefined"],
                ["string"],
            ],
            "expected_evidence": [
                {
                    "source": "ci.log",
                    "term_groups": [["ts2322"], ["string | undefined"]],
                },
                {
                    "source": "config.ts",
                    "term_groups": [["process.env.deploy_region"]],
                },
            ],
            "expected_relevant_files": ["config.ts", "deploy.ts", "tsconfig.json"],
            "expected_fix_direction": [
                "Validate DEPLOY_REGION once at configuration startup.",
                "Throw a clear configuration error or provide an intentional default.",
            ],
            "fix_direction_term_groups": [
                ["validate", "check", "guard"],
                ["throw", "error", "default"],
            ],
            "minimum_original_tokens": 5000,
        },
    )


def generate_docker_sample() -> None:
    root = "docker-build"
    write_text(f"{root}/ci.log", docker_log())
    write_text(
        f"{root}/Dockerfile",
        """
FROM node:22.18.0-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY src ./src

CMD ["node", "src/server.js"]
""",
    )
    write_text(
        f"{root}/.dockerignore",
        """
node_modules
dist
coverage
*.log
*.json
.git
""",
    )
    write_text(
        f"{root}/package.json",
        """
{
  "name": "demo-api",
  "private": true,
  "version": "1.0.0",
  "scripts": {
    "start": "node src/server.js"
  }
}
""",
    )
    write_json(
        f"{root}/ground_truth.json",
        {
            "schema_version": 2,
            "case_id": root,
            "expected_root_cause": (
                "The *.json rule in .dockerignore removes package.json and "
                "package-lock.json from the build context before COPY runs."
            ),
            "root_cause_term_groups": [
                [".dockerignore"],
                ["*.json"],
                ["package-lock.json"],
            ],
            "expected_evidence": [
                {
                    "source": "ci.log",
                    "term_groups": [["package-lock.json"], ["not found"]],
                },
                {
                    "source": ".dockerignore",
                    "term_groups": [["*.json"]],
                },
            ],
            "expected_relevant_files": ["Dockerfile", ".dockerignore"],
            "expected_fix_direction": [
                "Replace the broad *.json ignore rule with targeted generated-file rules.",
                "Alternatively add explicit !package.json and !package-lock.json exceptions.",
            ],
            "fix_direction_term_groups": [
                ["remove", "replace", "narrow", "exception", "!package"],
                ["*.json", "package.json", "package-lock.json"],
            ],
            "minimum_original_tokens": 5000,
        },
    )


def generate_dependency_resolution_sample() -> None:
    root = "dependency-resolution"
    write_text(f"{root}/ci.log", dependency_resolution_log())
    write_text(
        f"{root}/package.json",
        """
{
  "name": "analytics-console",
  "private": true,
  "version": "3.2.0",
  "dependencies": {
    "@legacy-grid/react": "4.6.0",
    "react": "19.2.0",
    "react-dom": "19.2.0"
  }
}
""",
    )
    write_text(
        f"{root}/package-lock.json",
        """
{
  "name": "analytics-console",
  "version": "3.2.0",
  "lockfileVersion": 3,
  "packages": {
    "": {
      "dependencies": {
        "@legacy-grid/react": "4.6.0",
        "react": "19.2.0",
        "react-dom": "19.2.0"
      }
    },
    "node_modules/@legacy-grid/react": {
      "version": "4.6.0",
      "peerDependencies": {
        "react": "^18.2.0"
      }
    }
  }
}
""",
    )
    write_json(
        f"{root}/ground_truth.json",
        {
            "schema_version": 2,
            "case_id": root,
            "expected_root_cause": (
                "@legacy-grid/react 4.6.0 requires React ^18.2.0, while the root "
                "project pins React 19.2.0, so npm correctly rejects the peer tree."
            ),
            "root_cause_term_groups": [
                ["@legacy-grid/react"],
                ["^18.2.0", "react 18"],
                ["19.2.0", "react 19"],
                ["peer"],
            ],
            "expected_evidence": [
                {
                    "source": "ci.log",
                    "term_groups": [["eresolve"], ["peer react"], ["^18.2.0"]],
                },
                {
                    "source": "package.json",
                    "term_groups": [["@legacy-grid/react"], ["19.2.0"]],
                },
            ],
            "expected_relevant_files": ["package.json", "package-lock.json"],
            "expected_fix_direction": [
                (
                    "Upgrade @legacy-grid/react to a release that supports React 19, "
                    "or intentionally align React and React DOM to 18."
                ),
                "Regenerate and review the lockfile; do not hide the conflict with --force.",
            ],
            "fix_direction_term_groups": [
                ["upgrade", "align", "downgrade"],
                ["react 19", "react 18", "peer"],
                ["lockfile", "package-lock"],
            ],
            "minimum_original_tokens": 5000,
        },
    )


def generate_github_actions_environment_sample() -> None:
    root = "github-actions-environment"
    write_text(f"{root}/ci.log", github_actions_environment_log())
    write_text(
        f"{root}/deploy.yml",
        """
name: deploy

on:
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Validate deployment environment
        env:
          DEPLOY_ENV: ${{ vars.DEPLOY_ENVIRONMENT }}
        run: python scripts/validate_env.py
""",
    )
    write_text(
        f"{root}/validate_env.py",
        """
import os


deploy_env = os.environ.get("DEPLOY_ENV", "").strip()
if not deploy_env:
    raise RuntimeError("DEPLOY_ENV is required")
if deploy_env not in {"staging", "production"}:
    raise RuntimeError("DEPLOY_ENV must be staging or production")
""",
    )
    write_json(
        f"{root}/ground_truth.json",
        {
            "schema_version": 2,
            "case_id": root,
            "expected_root_cause": (
                "The workflow maps DEPLOY_ENV from the repository variable "
                "DEPLOY_ENVIRONMENT, but that variable is unset in this Actions context, "
                "so the validation script receives an empty value."
            ),
            "root_cause_term_groups": [
                ["deploy_environment"],
                ["unset", "missing", "empty", "not defined"],
                ["deploy_env"],
            ],
            "expected_evidence": [
                {
                    "source": "ci.log",
                    "term_groups": [["deploy_env:"], ["deploy_env is required"]],
                },
                {
                    "source": "deploy.yml",
                    "term_groups": [["vars.deploy_environment"]],
                },
            ],
            "expected_relevant_files": ["deploy.yml", "validate_env.py"],
            "expected_fix_direction": [
                (
                    "Define DEPLOY_ENVIRONMENT at the repository or selected GitHub "
                    "Environment scope before dispatching the workflow."
                ),
                "Keep the fail-fast validation and document the allowed values.",
            ],
            "fix_direction_term_groups": [
                ["define", "configure", "set"],
                [
                    "repository variable",
                    "environment variable",
                    "github environment",
                    "vars",
                ],
                ["staging", "production", "allowed"],
            ],
            "minimum_original_tokens": 5000,
        },
    )


def main() -> None:
    generate_python_sample()
    generate_typescript_sample()
    generate_docker_sample()
    generate_dependency_resolution_sample()
    generate_github_actions_environment_sample()
    for sample_id in (
        "python-pytest",
        "typescript-build",
        "docker-build",
        "dependency-resolution",
        "github-actions-environment",
    ):
        log_path = EXAMPLES_ROOT / sample_id / "ci.log"
        print(f"{sample_id}: {log_path.stat().st_size} UTF-8 bytes")


if __name__ == "__main__":
    main()
