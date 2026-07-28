import subprocess
from email.message import Message
from pathlib import Path

import pytest
from scripts.container_entrypoint import (
    ContainerConfigurationError,
    RuntimeConfig,
    api_command,
    load_runtime_config,
    proxy_command,
    supervise,
)
from scripts.docker_live_verify import (
    LOW_YIELD_STATS_DELTA,
    LiveVerificationError,
    _stats_delta,
    _stop_and_verify,
)
from scripts.docker_live_verify import (
    _docker_cli as _live_docker_cli,
)
from scripts.docker_smoke import (
    API_EXIT_HOST_PORT,
    APPLICATION_HOST_PORT,
    _kill_child_and_wait,
    _request,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_container_runtime_requires_both_secret_names_without_exposing_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("scripts.container_entrypoint.shutil.which", lambda _name: "/bin/paritok")

    with pytest.raises(ContainerConfigurationError) as raised:
        load_runtime_config(
            {
                "DEEPSEEK_API_KEY": "container-test-only",
                "PARITOK_API_KEY": "",
            }
        )

    message = str(raised.value)
    assert "PARITOK_API_KEY" in message
    assert "container-test-only" not in message


@pytest.mark.parametrize("port", ["0", "65536", "8080", "not-a-port"])
def test_container_runtime_rejects_invalid_or_conflicting_ports(
    monkeypatch: pytest.MonkeyPatch,
    port: str,
) -> None:
    monkeypatch.setattr("scripts.container_entrypoint.shutil.which", lambda _name: "/bin/paritok")

    with pytest.raises(ContainerConfigurationError):
        load_runtime_config(
            {
                "DEEPSEEK_API_KEY": "container-test-only",
                "PARITOK_API_KEY": "container-test-only",
                "PORT": port,
            }
        )


def test_container_commands_fix_proxy_loopback_and_single_api_worker() -> None:
    config = RuntimeConfig(
        port=9000,
        paritok_executable=Path("/usr/local/bin/paritok"),
        project_root=Path("/app"),
    )

    proxy = proxy_command(config)
    api = api_command(config)

    assert proxy[0].replace("\\", "/") == "/usr/local/bin/paritok"
    assert proxy[1:7] == [
        "proxy",
        "--host",
        "127.0.0.1",
        "--port",
        "8080",
        "--config-file",
    ]
    assert proxy[7].replace("\\", "/") == "/app/paritok.yaml"
    assert proxy[8:] == [
        "--openai-url",
        "https://api.deepseek.com/chat/completions",
        "--log-level",
        "warning",
    ]
    assert "--host" in api
    assert api[api.index("--host") + 1] == "0.0.0.0"
    assert api[api.index("--port") + 1] == "9000"
    assert api[api.index("--workers") + 1] == "1"
    assert "--no-access-log" in api


def test_supervisor_waits_for_proxy_health_before_starting_api(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    events: list[str] = []

    class FakeProcess:
        def __init__(self, name: str, pid: int) -> None:
            self.name = name
            self.pid = pid

        def poll(self) -> int | None:
            return 9 if self.name == "api" else None

    processes = [FakeProcess("proxy", 21), FakeProcess("api", 22)]

    def fake_popen(command: list[str], **_kwargs: object) -> FakeProcess:
        name = "proxy" if "proxy" in command else "api"
        events.append(f"start:{name}")
        return processes.pop(0)

    def fake_wait(_process: FakeProcess, url: str) -> bool:
        events.append(f"wait:{url}")
        return True

    monkeypatch.setattr("scripts.container_entrypoint.subprocess.Popen", fake_popen)
    monkeypatch.setattr("scripts.container_entrypoint._wait_for_http", fake_wait)
    monkeypatch.setattr("scripts.container_entrypoint._write_pid", lambda *_args: None)
    monkeypatch.setattr("scripts.container_entrypoint._stop_processes", lambda *_args: None)

    result = supervise(
        RuntimeConfig(
            port=8000,
            paritok_executable=Path("/usr/local/bin/paritok"),
            project_root=Path("/app"),
        )
    )

    assert result == 1
    assert events == [
        "start:proxy",
        "wait:http://127.0.0.1:8080/health",
        "start:api",
        "wait:http://127.0.0.1:8000/api/config-status",
    ]
    assert "FastAPI exited unexpectedly with status 9" in capsys.readouterr().err


def test_docker_assets_exclude_secrets_and_do_not_publish_proxy_port() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "FROM node:" in dockerfile
    assert "FROM python:" in dockerfile
    assert "COPY . " not in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert 'ENTRYPOINT ["python", "/app/scripts/container_entrypoint.py"]' in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert "EXPOSE 8080" not in dockerfile
    assert "ARG DEEPSEEK_API_KEY" not in dockerfile
    assert "ARG PARITOK_API_KEY" not in dockerfile
    assert "ENV DEEPSEEK_API_KEY" not in dockerfile
    assert "ENV PARITOK_API_KEY" not in dockerfile
    assert "/api/health" in dockerfile
    assert "paritok_connected" in dockerfile
    assert "os.environ.get('PORT','8000')" in dockerfile
    assert "--mount=type=cache" not in dockerfile
    assert "--index-url https://download.pytorch.org/whl/cpu" in dockerfile
    assert '"torch==2.13.0+cpu"' in dockerfile

    for required_pattern in (
        ".git",
        ".env",
        ".env.*",
        "backend/.venv",
        "frontend/node_modules",
        "artifacts/runtime",
        "**/.pytest_cache",
        "**/.ruff_cache",
        "**/.mypy_cache",
    ):
        assert required_pattern in dockerignore

    assert "env_file:" in compose
    assert "127.0.0.1:" in compose
    assert "8080:" not in compose
    assert "no-new-privileges:true" in compose
    assert "cap_drop:" in compose


def test_container_dependency_versions_match_runtime_with_proxy_extra() -> None:
    runtime_lines = {
        line.strip()
        for line in (PROJECT_ROOT / "backend" / "requirements.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    container_lines = {
        line.strip()
        for line in (PROJECT_ROOT / "backend" / "requirements-container.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    paritok_config = (PROJECT_ROOT / "paritok.yaml").read_text(encoding="utf-8")

    assert container_lines == runtime_lines
    assert "paritok[proxy]==1.2.7" in container_lines
    assert "strategy: passthrough" in paritok_config


def test_docker_smoke_normalizes_response_header_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = Message()
    headers["Content-security-policy"] = "default-src 'self'"

    class FakeResponse:
        status = 200

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"LeanCI"

        @property
        def headers(self) -> Message:
            return headers

    monkeypatch.setattr(
        "scripts.docker_smoke.urllib.request.urlopen",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    status, normalized, body = _request("/")

    assert status == 200
    assert normalized["content-security-policy"] == "default-src 'self'"
    assert body == b"LeanCI"


def test_docker_smoke_signals_child_without_shell_or_kill_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    class Completed:
        stdout = "17"

    def fake_run(
        _docker: str,
        arguments: list[str],
        **_kwargs: object,
    ) -> Completed:
        calls.append(arguments)
        return Completed()

    monkeypatch.setattr("scripts.docker_smoke._read_child_pid", lambda *_args: 23)
    monkeypatch.setattr("scripts.docker_smoke._run", fake_run)

    assert _kill_child_and_wait("docker.exe", "fixed-container", "proxy") == 17
    assert calls[0][:4] == ["exec", "fixed-container", "python", "-c"]
    assert "os.kill(23,signal.SIGTERM)" in calls[0][4]
    assert calls[1] == ["wait", "fixed-container"]


def test_docker_smoke_uses_distinct_fixed_host_ports() -> None:
    assert APPLICATION_HOST_PORT == 18086
    assert API_EXIT_HOST_PORT == 18087
    assert APPLICATION_HOST_PORT != API_EXIT_HOST_PORT


def test_live_verifier_accepts_only_an_explicit_docker_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    docker = tmp_path / "docker.exe"
    docker.write_bytes(b"test-only")
    monkeypatch.setenv("LEANCI_DOCKER_CLI", str(docker))

    assert _live_docker_cli() == str(docker.resolve())

    invalid = tmp_path / "not-docker.exe"
    invalid.write_bytes(b"test-only")
    monkeypatch.setenv("LEANCI_DOCKER_CLI", str(invalid))
    with pytest.raises(LiveVerificationError):
        _live_docker_cli()


def test_live_verifier_rejects_stats_counter_reset() -> None:
    before = {
        "total_requests": 2,
        "input_tokens_original": 10,
        "input_tokens_compressed": 4,
        "tokens_saved": 6,
    }
    after = dict(before)
    after["total_requests"] = 1

    with pytest.raises(LiveVerificationError):
        _stats_delta(before, after)


def test_low_yield_stats_delta_is_explicit_and_does_not_fabricate_tokens() -> None:
    assert LOW_YIELD_STATS_DELTA == {
        "total_requests": 1,
        "input_tokens_original": 0,
        "input_tokens_compressed": 0,
        "tokens_saved": 0,
    }


def test_live_verifier_uses_inspected_state_not_stop_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        _docker: str,
        arguments: list[str],
        *,
        check: bool = True,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        del check, timeout
        if arguments[0] == "stop":
            return subprocess.CompletedProcess(arguments, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(
            arguments,
            0,
            stdout='{"Running":false,"ExitCode":0}',
            stderr="",
        )

    monkeypatch.setattr("scripts.docker_live_verify._run", fake_run)

    assert _stop_and_verify("docker.exe") == 0
