"""Container PID 1 for the fixed Paritok + Uvicorn process topology."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from threading import Event

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARITOK_PORT = 8080
STARTUP_TIMEOUT_SECONDS = 20.0
CHILD_STOP_TIMEOUT_SECONDS = 8.0


class ContainerConfigurationError(ValueError):
    """A safe startup configuration error that never contains secret values."""


@dataclass(frozen=True)
class RuntimeConfig:
    port: int
    paritok_executable: Path
    project_root: Path = PROJECT_ROOT


def load_runtime_config(environment: Mapping[str, str]) -> RuntimeConfig:
    """Validate the fixed runtime boundary without returning secret values."""

    missing = [
        name
        for name in ("DEEPSEEK_API_KEY", "PARITOK_API_KEY")
        if not environment.get(name, "").strip()
    ]
    if missing:
        raise ContainerConfigurationError(
            "Missing required runtime secret variables: " + ", ".join(missing)
        )
    if environment.get("LLM_PROVIDER", "paritok").strip().casefold() != "paritok":
        raise ContainerConfigurationError(
            "LLM_PROVIDER must be paritok in the container."
        )

    raw_port = environment.get("PORT", "8000").strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ContainerConfigurationError(
            "PORT must be an integer from 1 to 65535."
        ) from exc
    if not 1 <= port <= 65_535 or port == PARITOK_PORT:
        raise ContainerConfigurationError(
            "PORT must be from 1 to 65535 and must not conflict with internal port 8080."
        )

    executable = shutil.which("paritok")
    if executable is None:
        raise ContainerConfigurationError(
            "The fixed Paritok executable is unavailable."
        )
    return RuntimeConfig(port=port, paritok_executable=Path(executable).resolve())


def proxy_command(config: RuntimeConfig) -> list[str]:
    """Return the fixed localhost-only Paritok command."""

    return [
        str(config.paritok_executable),
        "proxy",
        "--host",
        "127.0.0.1",
        "--port",
        str(PARITOK_PORT),
        "--config-file",
        str(config.project_root / "paritok.yaml"),
        "--openai-url",
        "https://api.deepseek.com/chat/completions",
        "--log-level",
        "warning",
    ]


def api_command(config: RuntimeConfig) -> list[str]:
    """Return the fixed single-worker Uvicorn command."""

    return [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--app-dir",
        str(config.project_root / "backend"),
        "--host",
        "0.0.0.0",
        "--port",
        str(config.port),
        "--workers",
        "1",
        "--no-access-log",
    ]


def _wait_for_http(process: subprocess.Popen[bytes], url: str) -> bool:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except (OSError, urllib.error.URLError):
            time.sleep(0.2)
    return False


def _stop_processes(processes: tuple[subprocess.Popen[bytes], ...]) -> None:
    """Stop children together so the total grace period remains bounded."""

    running = [process for process in processes if process.poll() is None]
    for process in running:
        process.terminate()

    deadline = time.monotonic() + CHILD_STOP_TIMEOUT_SECONDS
    for process in running:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            continue

    for process in running:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)


def _write_pid(name: str, process: subprocess.Popen[bytes]) -> None:
    Path(f"/tmp/leanci-{name}.pid").write_text(str(process.pid), encoding="ascii")


def supervise(config: RuntimeConfig) -> int:
    """Start both fixed services and fail the container when either exits."""

    stop_requested = Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_requested.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    print(
        f"LeanCI container starting Paritok on 127.0.0.1:{PARITOK_PORT} "
        f"and FastAPI on 0.0.0.0:{config.port}.",
        flush=True,
    )
    processes: dict[str, subprocess.Popen[bytes]] = {}

    try:
        try:
            proxy = subprocess.Popen(proxy_command(config), cwd=config.project_root)
        except OSError:
            print(
                "Paritok process could not be started.",
                file=sys.stderr,
                flush=True,
            )
            return 1
        processes["Paritok"] = proxy
        _write_pid("proxy", proxy)
        print(f"Paritok process started with PID {proxy.pid}.", flush=True)

        if not _wait_for_http(proxy, f"http://127.0.0.1:{PARITOK_PORT}/health"):
            return_code = proxy.poll()
            if return_code is None:
                message = "Paritok did not become healthy within 20 seconds."
            else:
                message = (
                    "Paritok exited during startup with status "
                    f"{return_code} before /health became ready."
                )
            print(message, file=sys.stderr, flush=True)
            return 1

        print("Paritok /health is ready; starting FastAPI.", flush=True)
        try:
            api = subprocess.Popen(api_command(config), cwd=config.project_root)
        except OSError:
            print(
                "FastAPI process could not be started.",
                file=sys.stderr,
                flush=True,
            )
            return 1
        processes["FastAPI"] = api
        _write_pid("api", api)
        print(f"FastAPI process started with PID {api.pid}.", flush=True)
        if not _wait_for_http(api, f"http://127.0.0.1:{config.port}/api/config-status"):
            return_code = api.poll()
            if return_code is None:
                message = "FastAPI did not become ready within 20 seconds."
            else:
                message = (
                    "FastAPI exited during startup with status "
                    f"{return_code} before its readiness probe succeeded."
                )
            print(message, file=sys.stderr, flush=True)
            return 1

        print("LeanCI container services are ready.", flush=True)
        while not stop_requested.wait(0.2):
            for name, process in processes.items():
                return_code = process.poll()
                if return_code is not None:
                    print(
                        f"{name} exited unexpectedly with status {return_code}; "
                        "stopping the sibling process.",
                        file=sys.stderr,
                        flush=True,
                    )
                    return 1
        print("Shutdown signal received; stopping both services.", flush=True)
        return 0
    finally:
        _stop_processes(tuple(reversed(processes.values())))


def main() -> int:
    try:
        config = load_runtime_config(os.environ)
    except ContainerConfigurationError as exc:
        print(
            f"LeanCI container configuration error: {exc}", file=sys.stderr, flush=True
        )
        return 78
    try:
        return supervise(config)
    except (OSError, subprocess.SubprocessError):
        print(
            "LeanCI container encountered a local process supervision error.",
            file=sys.stderr,
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
