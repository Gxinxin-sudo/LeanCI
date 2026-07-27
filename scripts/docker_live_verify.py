"""Run one fixed paid sample through the real single-container route.

This script deliberately accepts one sample per invocation so an operator can
bound every external verification to the repository's 120-second command limit.
It passes the ignored local .env to Docker without reading or printing values.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE = "leanci:phase7"
CONTAINER = "leanci-phase7-live-verify"
HOST_PORT = 18088
SAMPLES = ("python-pytest", "typescript-build", "docker-build")
EXPECTED_MODEL = "deepseek-v4-flash"
LOW_YIELD_ERROR_CODE = "PARITOK_COMPRESSION_SKIPPED"
LOW_YIELD_STATS_DELTA = {
    "total_requests": 1,
    "input_tokens_original": 0,
    "input_tokens_compressed": 0,
    "tokens_saved": 0,
}
COMMAND_TIMEOUT_SECONDS = 30
READY_TIMEOUT_SECONDS = 25
ANALYSIS_TIMEOUT_SECONDS = 110


class LiveVerificationError(RuntimeError):
    """A safe verification failure that never includes credentials."""


def _docker_cli() -> str:
    configured = os.environ.get("LEANCI_DOCKER_CLI", "").strip()
    executable = configured or shutil.which("docker")
    if not executable:
        raise LiveVerificationError("Docker CLI is unavailable.")
    path = Path(executable)
    if path.name.casefold() not in {"docker", "docker.exe"} or not path.is_file():
        raise LiveVerificationError(
            "LEANCI_DOCKER_CLI must point to docker or docker.exe."
        )
    return str(path.resolve())


def _run(
    docker: str,
    arguments: list[str],
    *,
    check: bool = True,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [docker, *arguments],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and completed.returncode != 0:
        raise LiveVerificationError(
            f"Docker command {arguments[0]!r} failed with status "
            f"{completed.returncode}."
        )
    return completed


def _request(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 5,
) -> tuple[int, dict[str, Any]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{HOST_PORT}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            parsed = json.load(response)
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        try:
            parsed = json.load(exc)
        except (json.JSONDecodeError, UnicodeDecodeError):
            parsed = {"error": {"code": "NON_JSON_ERROR"}}
        return exc.code, parsed


def _wait_for_health() -> dict[str, Any]:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    last_payload: dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            status, payload = _request("/api/health", timeout=12)
            last_payload = payload
            if (
                status == 200
                and payload.get("status") == "ok"
                and payload.get("paritok_connected") is True
                and payload.get("hosted_gpu_available") is True
                and payload.get("deepseek_called") is False
                and payload.get("model") == EXPECTED_MODEL
            ):
                return payload
        except OSError:
            pass
        time.sleep(0.25)
    component = {
        "status": last_payload.get("status"),
        "paritok_connected": last_payload.get("paritok_connected"),
        "hosted_gpu_available": last_payload.get("hosted_gpu_available"),
    }
    raise LiveVerificationError(
        "Container did not report a fully healthy formal route within 25 seconds: "
        + json.dumps(component, separators=(",", ":"))
    )


def _internal_stats(docker: str) -> dict[str, int]:
    code = (
        "import json,urllib.request;"
        "d=json.load(urllib.request.urlopen("
        "'http://127.0.0.1:8080/stats',timeout=5));"
        "print(json.dumps(d,separators=(',',':')))"
    )
    completed = _run(docker, ["exec", CONTAINER, "python", "-c", code])
    payload = json.loads(completed.stdout)
    required = (
        "total_requests",
        "input_tokens_original",
        "input_tokens_compressed",
        "tokens_saved",
    )
    if not isinstance(payload, dict) or any(
        not isinstance(payload.get(name), int) for name in required
    ):
        raise LiveVerificationError("Paritok /stats returned an invalid payload.")
    return {name: payload[name] for name in required}


def _stats_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    delta = {name: after[name] - before[name] for name in before}
    if any(value < 0 for value in delta.values()):
        raise LiveVerificationError("Paritok /stats counters moved backwards.")
    return delta


def _assert_port_available() -> None:
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", HOST_PORT))
        except OSError as exc:
            raise LiveVerificationError(
                f"Host port {HOST_PORT} is already in use."
            ) from exc


def _container_exists(docker: str) -> bool:
    return (
        _run(
            docker,
            ["container", "inspect", CONTAINER],
            check=False,
        ).returncode
        == 0
    )


def _stop_and_verify(docker: str) -> int:
    _run(docker, ["stop", "--time", "15", CONTAINER], timeout=20)
    inspected = _run(
        docker,
        ["container", "inspect", "--format", "{{json .State}}", CONTAINER],
    )
    state = json.loads(inspected.stdout)
    if state.get("Running") is not False or state.get("ExitCode") != 0:
        raise LiveVerificationError(
            "Container did not exit cleanly after SIGTERM "
            f"(exit={state.get('ExitCode')})."
        )
    return int(state["ExitCode"])


def verify(sample_id: str) -> dict[str, Any]:
    docker = _docker_cli()
    env_file = PROJECT_ROOT / ".env"
    if not env_file.is_file():
        raise LiveVerificationError(
            "The ignored local .env file is required for live verification."
        )
    if _container_exists(docker):
        raise LiveVerificationError(
            f"Refusing to replace pre-existing container {CONTAINER}."
        )
    _assert_port_available()

    created = False
    clean_exit_code: int | None = None
    try:
        _run(
            docker,
            [
                "run",
                "--detach",
                "--name",
                CONTAINER,
                "--publish",
                f"127.0.0.1:{HOST_PORT}:8000",
                "--env-file",
                str(env_file),
                "--env",
                "ENVIRONMENT=development",
                "--env",
                "PORT=8000",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                IMAGE,
            ],
        )
        created = True
        health = _wait_for_health()
        before = _internal_stats(docker)

        sample_status, sample = _request(f"/api/samples/{sample_id}")
        if sample_status != 200:
            raise LiveVerificationError("The fixed sample could not be loaded.")
        analysis_status, analysis = _request(
            "/api/analyze",
            method="POST",
            payload={"log_text": sample["log_text"], "files": sample["files"]},
            timeout=ANALYSIS_TIMEOUT_SECONDS,
        )
        after = _internal_stats(docker)
        delta = _stats_delta(before, after)
        error_code: str | None = None
        if analysis_status == 200:
            proof = analysis.get("compression_stats")
            if not isinstance(proof, dict):
                raise LiveVerificationError(
                    "Analysis did not return verified compression stats."
                )
            if proof.get("model") != EXPECTED_MODEL:
                raise LiveVerificationError(
                    "Analysis did not use the fixed deepseek-v4-flash model."
                )
            expected = {
                "total_requests": proof.get("proxy_requests"),
                "input_tokens_original": proof.get("original_tokens"),
                "input_tokens_compressed": proof.get("compressed_tokens"),
                "tokens_saved": proof.get("saved_tokens"),
            }
            if delta != expected:
                raise LiveVerificationError(
                    "The API compression proof did not match container /stats delta."
                )
            analysis_outcome = "compressed"
            model = proof.get("model")
        else:
            error_code = analysis.get("error", {}).get("code", "UNKNOWN")
            if (
                analysis_status != 503
                or error_code != LOW_YIELD_ERROR_CODE
                or delta != LOW_YIELD_STATS_DELTA
            ):
                raise LiveVerificationError(
                    f"Formal analysis failed with HTTP {analysis_status} ({error_code}); "
                    "safe_stats_delta=" + json.dumps(delta, separators=(",", ":")) + "."
                )
            analysis_outcome = "skipped_low_yield"
            model = health["model"]

        clean_exit_code = _stop_and_verify(docker)
        return {
            "status": "passed",
            "sample": sample_id,
            "analysis_outcome": analysis_outcome,
            "analysis_error_code": error_code,
            "health": {
                "status": health["status"],
                "paritok_connected": health["paritok_connected"],
                "hosted_gpu_available": health["hosted_gpu_available"],
                "deepseek_called": health["deepseek_called"],
            },
            "stats_delta": delta,
            "model": model,
            "container_exit_code": clean_exit_code,
            "orchestration_retries": 0,
        }
    finally:
        if created:
            if clean_exit_code is None:
                _run(
                    docker,
                    ["stop", "--time", "15", CONTAINER],
                    check=False,
                    timeout=20,
                )
            _run(docker, ["rm", CONTAINER], check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True, choices=SAMPLES)
    parser.add_argument(
        "--confirm-cost",
        action="store_true",
        help="Required acknowledgement that one real Paritok/DeepSeek analysis may incur cost.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.confirm_cost:
        print(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "Pass --confirm-cost to authorize one real model analysis.",
                },
                separators=(",", ":"),
            )
        )
        return 2
    result = verify(args.sample)
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        LiveVerificationError,
        OSError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ) as exc:
        print(
            json.dumps(
                {"status": "failed", "reason": str(exc)},
                separators=(",", ":"),
            )
        )
        raise SystemExit(1) from exc
