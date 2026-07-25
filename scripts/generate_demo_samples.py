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
            "schema_version": 1,
            "sample_id": root,
            "root_cause": (
                "Operator precedence subtracts one after exponentiation, so attempt 4 "
                "returns 15 instead of the configured 16-second cap."
            ),
            "expected_relevant_files": ["retry.py", "test_retry.py"],
            "required_relevant_files": ["retry.py", "test_retry.py"],
            "required_answer_terms": ["delay_for", "-1"],
            "expected_fix_direction": [
                "Make the intended backoff formula explicit with parentheses.",
                "Keep the cap test and add boundary cases around the maximum delay.",
            ],
            "expected_patch_contains": [
                "min(self.base_delay * (2**attempt), self.max_delay)"
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
            "schema_version": 1,
            "sample_id": root,
            "root_cause": (
                "DEPLOY_REGION is string | undefined, but loadConfig promises AppConfig "
                "with a required string region."
            ),
            "expected_relevant_files": ["config.ts", "deploy.ts", "tsconfig.json"],
            "required_relevant_files": ["config.ts"],
            "required_answer_terms": ["undefined", "string"],
            "expected_fix_direction": [
                "Validate DEPLOY_REGION once at configuration startup.",
                "Throw a clear configuration error or provide an intentional default.",
            ],
            "expected_patch_contains": ["const region = process.env.DEPLOY_REGION"],
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
            "schema_version": 1,
            "sample_id": root,
            "root_cause": (
                "The *.json rule in .dockerignore removes package.json and "
                "package-lock.json from the build context before COPY runs."
            ),
            "expected_relevant_files": ["Dockerfile", ".dockerignore"],
            "required_relevant_files": [".dockerignore"],
            "required_answer_terms": [".dockerignore", "package-lock"],
            "expected_fix_direction": [
                "Replace the broad *.json ignore rule with targeted generated-file rules.",
                "Alternatively add explicit !package.json and !package-lock.json exceptions.",
            ],
            "expected_patch_contains": ["!package.json", "!package-lock.json"],
            "minimum_original_tokens": 5000,
        },
    )


def main() -> None:
    generate_python_sample()
    generate_typescript_sample()
    generate_docker_sample()
    for sample_id in ("python-pytest", "typescript-build", "docker-build"):
        log_path = EXAMPLES_ROOT / sample_id / "ci.log"
        print(f"{sample_id}: {log_path.stat().st_size} UTF-8 bytes")


if __name__ == "__main__":
    main()
