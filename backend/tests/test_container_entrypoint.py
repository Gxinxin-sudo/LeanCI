from email.message import Message
from pathlib import Path

import pytest
from scripts.container_entrypoint import (
    ContainerConfigurationError,
    RuntimeConfig,
    api_command,
    load_runtime_config,
    proxy_command,
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

    for required_pattern in (
        ".git",
        ".env",
        ".env.*",
        "backend/.venv",
        "frontend/node_modules",
        "artifacts/runtime",
    ):
        assert required_pattern in dockerignore

    assert "env_file:" in compose
    assert "127.0.0.1:" in compose
    assert "8080:" not in compose
    assert "no-new-privileges:true" in compose
    assert "cap_drop:" in compose


def test_container_dependency_versions_match_runtime_with_passthrough_only() -> None:
    runtime_lines = {
        line.strip().replace("paritok[proxy]", "paritok")
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
    assert "strategy: passthrough" in paritok_config
    assert "sentence-transformers" not in "\n".join(container_lines)
    assert "numpy" not in "\n".join(container_lines)


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
