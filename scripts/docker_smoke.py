"""No-cost Docker image and container lifecycle smoke test for LeanCI."""

from __future__ import annotations

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

try:
    from scripts.scan_secrets import detector_names
except ModuleNotFoundError:
    from scan_secrets import detector_names

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE = "leanci:phase7"
APPLICATION_HOST_PORT = 18086
API_EXIT_HOST_PORT = 18087
NO_KEYS_CONTAINER = "leanci-phase7-no-keys"
PROXY_EXIT_CONTAINER = "leanci-phase7-proxy-exit"
API_EXIT_CONTAINER = "leanci-phase7-api-exit"
CONTAINER_NAMES = (NO_KEYS_CONTAINER, PROXY_EXIT_CONTAINER, API_EXIT_CONTAINER)
COMMAND_TIMEOUT_SECONDS = 30
CONTAINER_READY_TIMEOUT_SECONDS = 25


class DockerSmokeError(RuntimeError):
    """A safe smoke-test failure without container log contents."""


def _docker_cli() -> str:
    configured = os.environ.get("LEANCI_DOCKER_CLI", "").strip()
    executable = configured or shutil.which("docker")
    if not executable:
        raise DockerSmokeError("Docker CLI is unavailable.")
    path = Path(executable)
    if path.name.casefold() not in {"docker", "docker.exe"} or not path.is_file():
        raise DockerSmokeError("LEANCI_DOCKER_CLI must point to docker or docker.exe.")
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
        raise DockerSmokeError(
            f"Docker command {arguments[0]!r} failed with status {completed.returncode}."
        )
    return completed


def _container_exists(docker: str, name: str) -> bool:
    return _run(docker, ["container", "inspect", name], check=False).returncode == 0


def _assert_port_available(port: int) -> None:
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", port))
        except OSError as exc:
            raise DockerSmokeError(f"Host port {port} is already in use.") from exc


def _request(
    path: str,
    *,
    host_port: int = APPLICATION_HOST_PORT,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 5,
) -> tuple[int, dict[str, str], bytes]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{host_port}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            headers = {
                name.casefold(): value for name, value in response.headers.items()
            }
            return response.status, headers, response.read()
    except urllib.error.HTTPError as exc:
        headers = {name.casefold(): value for name, value in exc.headers.items()}
        return exc.code, headers, exc.read()


def _wait_for_ready(host_port: int = APPLICATION_HOST_PORT) -> None:
    deadline = time.monotonic() + CONTAINER_READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            status, _headers, _body = _request(
                "/api/config-status",
                host_port=host_port,
                timeout=1,
            )
            if status == 200:
                return
        except OSError:
            time.sleep(0.25)
    raise DockerSmokeError("Container API did not become ready within 25 seconds.")


def _wait_for_healthy(docker: str, name: str) -> None:
    deadline = time.monotonic() + CONTAINER_READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        inspected = _run(
            docker,
            ["container", "inspect", "--format", "{{.State.Health.Status}}", name],
        )
        if inspected.stdout.strip() == "healthy":
            return
        time.sleep(0.5)
    raise DockerSmokeError(
        "Docker healthcheck did not report healthy within 25 seconds."
    )


def _start_container(docker: str, name: str, host_port: int) -> str:
    completed = _run(
        docker,
        [
            "run",
            "--detach",
            "--name",
            name,
            "--publish",
            f"127.0.0.1:{host_port}:8000",
            "--env",
            "DEEPSEEK_API_KEY=container-test-only",
            "--env",
            "PARITOK_API_KEY=container-test-only",
            "--env",
            "LLM_PROVIDER=paritok",
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
    return completed.stdout.strip()


def _read_internal_json(docker: str, name: str, url: str) -> dict[str, Any]:
    code = (
        "import json,urllib.request;"
        f"data=json.load(urllib.request.urlopen({url!r},timeout=5));"
        "print(json.dumps(data,separators=(',',':')))"
    )
    completed = _run(docker, ["exec", name, "python", "-c", code])
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise DockerSmokeError("Internal container endpoint returned a non-object.")
    return payload


def _read_child_pid(docker: str, name: str, child: str) -> int:
    completed = _run(docker, ["exec", name, "cat", f"/tmp/leanci-{child}.pid"])
    try:
        pid = int(completed.stdout.strip())
    except ValueError as exc:
        raise DockerSmokeError(f"Container {child} PID file was invalid.") from exc
    if pid <= 1:
        raise DockerSmokeError(f"Container {child} PID must be greater than 1.")
    return pid


def _kill_child_and_wait(docker: str, name: str, child: str) -> int:
    pid = _read_child_pid(docker, name, child)
    signal_code = f"import os,signal;os.kill({pid},signal.SIGTERM)"
    _run(docker, ["exec", name, "python", "-c", signal_code])
    waited = _run(docker, ["wait", name], timeout=20)
    try:
        exit_code = int(waited.stdout.strip())
    except ValueError as exc:
        raise DockerSmokeError(
            "Docker wait did not return a container exit code."
        ) from exc
    if exit_code == 0:
        raise DockerSmokeError(
            f"Killing {child} did not fail the supervised container."
        )
    return exit_code


def _inspect_image(docker: str) -> dict[str, Any]:
    inspected = _run(docker, ["image", "inspect", IMAGE])
    payload = json.loads(inspected.stdout)
    config = payload[0]["Config"]
    environment_names = {
        item.partition("=")[0]
        for item in config.get("Env") or []
        if isinstance(item, str)
    }
    if {"DEEPSEEK_API_KEY", "PARITOK_API_KEY"} & environment_names:
        raise DockerSmokeError(
            "The image config contains a secret environment variable."
        )
    if config.get("User") != "10001:10001":
        raise DockerSmokeError("The image does not run as the fixed non-root user.")
    if config.get("Entrypoint") != ["python", "/app/scripts/container_entrypoint.py"]:
        raise DockerSmokeError("The image entrypoint is not the fixed Python PID 1.")
    exposed = set((config.get("ExposedPorts") or {}).keys())
    if exposed != {"8000/tcp"}:
        raise DockerSmokeError("The image must expose only FastAPI port 8000.")

    history = _run(
        docker, ["history", "--no-trunc", "--format", "{{json .CreatedBy}}", IMAGE]
    )
    if any(detector_names(line) for line in history.stdout.splitlines()):
        raise DockerSmokeError(
            "Image history contains a high-confidence secret pattern."
        )
    _run(
        docker,
        [
            "run",
            "--rm",
            "--entrypoint",
            "/usr/bin/test",
            IMAGE,
            "!",
            "-e",
            "/app/.env",
        ],
    )
    return {
        "user": config["User"],
        "entrypoint": config["Entrypoint"],
        "exposed_ports": sorted(exposed),
        "env_secret_names": [],
        "env_file_present": False,
    }


def _application_smoke(docker: str, name: str) -> dict[str, Any]:
    home_status, home_headers, home = _request("/")
    health_status, _health_headers, health_body = _request("/api/health", timeout=15)
    config_status, config_headers, config_body = _request("/api/config-status")
    samples_status, _sample_headers, samples_body = _request("/api/samples")
    benchmark_status, _benchmark_headers, benchmark_body = _request(
        "/api/benchmark/results"
    )
    analysis_status, _analysis_headers, analysis_body = _request(
        "/api/analyze",
        method="POST",
        payload={"log_text": "synthetic container smoke failure", "files": []},
        timeout=15,
    )

    config = json.loads(config_body)
    health = json.loads(health_body)
    samples = json.loads(samples_body)
    benchmark = json.loads(benchmark_body)
    analysis = json.loads(analysis_body)
    if home_status != 200 or b"LeanCI" not in home:
        raise DockerSmokeError("The built frontend was not served.")
    if (
        health_status != 200
        or health.get("service") != "leanci-api"
        or health.get("paritok_connected") is not True
        or health.get("deepseek_called") is not False
    ):
        raise DockerSmokeError(
            "The combined API and local Paritok health contract failed."
        )
    if "default-src 'self'" not in home_headers.get("content-security-policy", ""):
        raise DockerSmokeError("The built frontend is missing its document CSP.")
    if config_status != 200 or config_headers.get("cache-control") != "no-store":
        raise DockerSmokeError(
            "The public config endpoint failed its safe response contract."
        )
    if (
        config.get("llm_provider") != "paritok"
        or config.get("model") != "deepseek-v4-flash"
    ):
        raise DockerSmokeError(
            "The container changed the fixed formal provider or model."
        )
    if not config.get("deepseek_api_key_configured") or not config.get(
        "paritok_api_key_configured"
    ):
        raise DockerSmokeError("Runtime secret presence was not detected safely.")
    if samples_status != 200 or len(samples) != 5:
        raise DockerSmokeError("The five fixed samples were not available.")
    if benchmark_status != 200 or len(benchmark.get("rows", [])) != 10:
        raise DockerSmokeError("The fixed benchmark artifact was not available.")
    if analysis_status != 503 or analysis.get("error", {}).get("code") not in {
        "PARITOK_AUTHENTICATION_FAILED",
        "PARITOK_HOSTED_UNAVAILABLE",
        "PARITOK_GPU_UNAVAILABLE",
    }:
        raise DockerSmokeError(
            "Dummy credentials did not fail closed before a model request."
        )
    if "compression_stats" in analysis or "tokens" in json.dumps(analysis).casefold():
        raise DockerSmokeError("The failed analysis returned unverified Token data.")
    stats = _read_internal_json(
        docker,
        name,
        "http://127.0.0.1:8080/stats",
    )
    if not isinstance(stats.get("total_requests"), int):
        raise DockerSmokeError("The internal Paritok stats endpoint was invalid.")
    return {
        "frontend_status": home_status,
        "health_status": health_status,
        "paritok_connected": health["paritok_connected"],
        "hosted_gpu_available": health["hosted_gpu_available"],
        "config_status": config_status,
        "sample_count": len(samples),
        "benchmark_rows": len(benchmark["rows"]),
        "stats_total_requests": stats["total_requests"],
        "analysis_status": analysis_status,
        "analysis_error_code": analysis["error"]["code"],
        "deepseek_called": False,
    }


def main() -> int:
    docker = _docker_cli()
    for name in CONTAINER_NAMES:
        if _container_exists(docker, name):
            raise DockerSmokeError(
                f"Refusing to replace pre-existing container {name}."
            )

    created: list[str] = []
    result: dict[str, Any] = {}
    try:
        result["image"] = _inspect_image(docker)

        no_keys = _run(docker, ["run", "--name", NO_KEYS_CONTAINER, IMAGE], check=False)
        created.append(NO_KEYS_CONTAINER)
        if no_keys.returncode != 78:
            raise DockerSmokeError(
                "The no-key container did not fail with configuration status 78."
            )
        no_key_output = no_keys.stdout + no_keys.stderr
        if (
            "DEEPSEEK_API_KEY" not in no_key_output
            or "PARITOK_API_KEY" not in no_key_output
            or detector_names(no_key_output)
        ):
            raise DockerSmokeError(
                "The no-key failure was missing names or exposed secret-like data."
            )
        result["no_keys_exit_code"] = no_keys.returncode

        _assert_port_available(APPLICATION_HOST_PORT)
        result["proxy_exit_container_id"] = _start_container(
            docker,
            PROXY_EXIT_CONTAINER,
            APPLICATION_HOST_PORT,
        )[:12]
        created.append(PROXY_EXIT_CONTAINER)
        _wait_for_ready()
        _wait_for_healthy(docker, PROXY_EXIT_CONTAINER)
        result["application"] = _application_smoke(docker, PROXY_EXIT_CONTAINER)
        result["proxy_exit_code"] = _kill_child_and_wait(
            docker, PROXY_EXIT_CONTAINER, "proxy"
        )

        _assert_port_available(API_EXIT_HOST_PORT)
        result["api_exit_container_id"] = _start_container(
            docker,
            API_EXIT_CONTAINER,
            API_EXIT_HOST_PORT,
        )[:12]
        created.append(API_EXIT_CONTAINER)
        _wait_for_ready(API_EXIT_HOST_PORT)
        _wait_for_healthy(docker, API_EXIT_CONTAINER)
        result["api_exit_code"] = _kill_child_and_wait(
            docker, API_EXIT_CONTAINER, "api"
        )
    finally:
        for name in reversed(created):
            _run(docker, ["rm", "--force", name], check=False)

    print(json.dumps({"status": "passed", **result}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        DockerSmokeError,
        OSError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
    ) as exc:
        print(
            json.dumps(
                {"status": "failed", "reason": str(exc)},
                separators=(",", ":"),
            )
        )
        raise SystemExit(1) from exc
