import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app
from app.security import AnalysisConcurrencyLimitMiddleware, TrustedProxyAuthenticationMiddleware
from tests.test_api import FakeAnalysisService


def make_client(
    *,
    settings: Settings | None = None,
    service: Any | None = None,
    raise_server_exceptions: bool = True,
) -> TestClient:
    return TestClient(
        create_app(
            settings or Settings(_env_file=None),
            analysis_service=service or FakeAnalysisService(),
        ),
        raise_server_exceptions=raise_server_exceptions,
    )


def test_every_api_response_has_request_id_no_store_and_security_headers() -> None:
    client = make_client()

    for response in (
        client.get("/api/health"),
        client.get("/api/does-not-exist"),
        client.post(
            "/api/analyze",
            content=b"x" * (4 * 1024 * 1024 + 1),
            headers={"Content-Type": "application/json"},
        ),
    ):
        assert len(response.headers["X-Request-ID"]) == 32
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Content-Security-Policy"].startswith("default-src 'none'")
        assert response.headers["Permissions-Policy"] == (
            "camera=(), microphone=(), geolocation=()"
        )
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"


def test_request_id_is_server_owned_and_logs_never_include_headers_or_raw_path(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="leanci.access")
    client = make_client()
    secret = "header-secret-value-123456789"

    response = client.get(
        f"/api/not-a-route/{secret}",
        headers={
            "Authorization": f"Bearer {secret}",
            "X-Request-ID": "caller-controlled-id",
        },
    )

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] != "caller-controlled-id"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert secret not in caplog.text
    assert "Authorization" not in caplog.text
    assert "route=unknown" in caplog.text


@pytest.mark.parametrize(
    ("headers", "expected_code"),
    [
        ({"Content-Type": "text/plain"}, "UNSUPPORTED_MEDIA_TYPE"),
        ({"Content-Type": "application/octet-stream"}, "UNSUPPORTED_MEDIA_TYPE"),
        ({"Content-Type": "application/json; charset=iso-8859-1"}, "UNSUPPORTED_MEDIA_TYPE"),
        (
            {"Content-Type": "application/json", "Content-Encoding": "gzip"},
            "UNSUPPORTED_CONTENT_ENCODING",
        ),
    ],
)
def test_analysis_rejects_content_type_and_encoding_spoofing(
    headers: dict[str, str],
    expected_code: str,
) -> None:
    response = make_client().post(
        "/api/analyze",
        content=b'{"log_text":"failed"}',
        headers=headers,
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == expected_code


def test_utf8_json_content_type_is_accepted() -> None:
    response = make_client().post(
        "/api/analyze",
        content='{"log_text":"编译失败"}'.encode(),
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )

    assert response.status_code == 200


def test_cors_uses_an_explicit_allowlist_without_credentials() -> None:
    client = make_client(
        settings=Settings(
            _env_file=None,
            cors_allowed_origins="https://demo.example.com,http://127.0.0.1:5173",
        )
    )

    allowed = client.options(
        "/api/analyze",
        headers={
            "Origin": "https://demo.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    disallowed = client.get(
        "/api/health",
        headers={"Origin": "https://attacker.example"},
    )

    assert allowed.status_code == 200
    assert allowed.headers["Access-Control-Allow-Origin"] == "https://demo.example.com"
    assert allowed.headers.get("Access-Control-Allow-Credentials") is None
    assert "Access-Control-Allow-Origin" not in disallowed.headers


@pytest.mark.parametrize(
    "origins",
    [
        "*",
        "https://demo.example.com/path",
        "https://user:password@demo.example.com",
        "file:///tmp/demo",
    ],
)
def test_cors_configuration_rejects_wildcards_paths_and_credentials(origins: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_allowed_origins=origins)


def test_production_configuration_requires_a_complete_gateway_boundary() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            cors_allowed_origins="https://app.example.com",
        )

    settings = Settings(
        _env_file=None,
        environment="production",
        cors_allowed_origins="https://app.example.com",
        trusted_proxy_cidrs="10.0.0.0/8",
        proxy_auth_shared_secret="test-only-internal-secret",
        distributed_rate_limit_required=True,
        daily_analysis_request_budget=25,
    )
    assert settings.proxy_auth_configured is True
    assert str(settings.trusted_proxy_networks[0]) == "10.0.0.0/8"


def test_configuration_errors_hide_secret_inputs() -> None:
    secret_marker = "must-not-appear-in-validation-errors"

    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            environment="production",
            deepseek_api_key=secret_marker,
            paritok_api_key=secret_marker,
            cors_allowed_origins="http://localhost:5173",
        )

    assert secret_marker not in str(exc_info.value)
    assert "input_value=" not in str(exc_info.value)


@pytest.mark.anyio
async def test_trusted_proxy_authentication_rejects_direct_or_spoofed_analysis() -> None:
    sent: list[dict[str, Any]] = []

    async def downstream(
        scope: dict[str, Any],
        _receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        assert scope["state"]["principal"] == "user:123"
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    middleware = TrustedProxyAuthenticationMiddleware(
        downstream,
        required=True,
        trusted_proxy_networks=Settings(
            _env_file=None,
            trusted_proxy_cidrs="10.0.0.0/8",
        ).trusted_proxy_networks,
        shared_secret="test-only-internal-secret",
        auth_header="x-leanci-proxy-auth",
        principal_header="x-leanci-principal",
    )
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/analyze",
        "headers": [
            (b"x-leanci-proxy-auth", b"test-only-internal-secret"),
            (b"x-leanci-principal", b"user:123"),
        ],
        "state": {},
        "client": ("203.0.113.10", 443),
    }
    await middleware(scope, receive, send)  # type: ignore[arg-type]
    assert sent[0]["status"] == 401
    assert b"AUTHENTICATION_REQUIRED" in sent[1]["body"]

    sent.clear()
    scope["client"] = ("10.1.2.3", 443)
    await middleware(scope, receive, send)  # type: ignore[arg-type]
    assert sent[0]["status"] == 200


def test_analysis_rate_limit_is_bounded_and_returns_retry_metadata() -> None:
    client = make_client(
        settings=Settings(
            _env_file=None,
            analyze_rate_limit_requests=1,
            rate_limit_window_seconds=60,
        )
    )

    first = client.post("/api/analyze", json={"log_text": "first failure"})
    second = client.post("/api/analyze", json={"log_text": "second failure"})

    assert first.status_code == 200
    assert first.headers["RateLimit-Limit"] == "1"
    assert first.headers["RateLimit-Remaining"] == "0"
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "RATE_LIMITED"
    assert int(second.headers["Retry-After"]) >= 1


def test_analysis_has_a_bounded_end_to_end_timeout() -> None:
    class SlowService(FakeAnalysisService):
        async def analyze(self, untrusted_context: str) -> Any:
            del untrusted_context
            await asyncio.sleep(1)
            raise AssertionError("timeout did not cancel analysis")

    response = make_client(
        settings=Settings(_env_file=None, analysis_timeout_seconds=0.01),
        service=SlowService(),
    ).post("/api/analyze", json={"log_text": "failed"})

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "ANALYSIS_TIMEOUT"
    assert "No result was accepted" in response.json()["error"]["message"]


@pytest.mark.anyio
async def test_excess_concurrent_analysis_is_rejected_without_queueing() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()
    first_sent: list[dict[str, Any]] = []
    second_sent: list[dict[str, Any]] = []

    async def downstream(
        _scope: dict[str, Any],
        _receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        entered.set()
        await release.wait()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send_first(message: dict[str, Any]) -> None:
        first_sent.append(message)

    async def send_second(message: dict[str, Any]) -> None:
        second_sent.append(message)

    def scope() -> dict[str, Any]:
        return {
            "type": "http",
            "method": "POST",
            "path": "/api/analyze",
            "headers": [],
            "state": {},
            "client": ("127.0.0.1", 50000),
        }

    middleware = AnalysisConcurrencyLimitMiddleware(downstream, maximum=1)
    first = asyncio.create_task(middleware(scope(), receive, send_first))  # type: ignore[arg-type]
    await asyncio.wait_for(entered.wait(), timeout=1)

    await middleware(scope(), receive, send_second)  # type: ignore[arg-type]

    assert second_sent[0]["status"] == 429
    assert b"ANALYSIS_BUSY" in second_sent[1]["body"]
    release.set()
    await asyncio.wait_for(first, timeout=1)
    assert first_sent[0]["status"] == 200


def test_unexpected_exception_never_returns_environment_or_internal_path(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_name = "DEEPSEEK_" + "API_KEY"
    secret_value = "real-looking-secret-" + "123456789"
    secret = f"{secret_name}={secret_value}"

    class ExplodingService(FakeAnalysisService):
        async def analyze(self, untrusted_context: str) -> Any:
            del untrusted_context
            raise RuntimeError(f"{secret} at C:\\private\\service.py")

    caplog.set_level(logging.INFO, logger="leanci.access")
    response = make_client(
        service=ExplodingService(),
        raise_server_exceptions=False,
    ).post("/api/analyze", json={"log_text": "failed"})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert secret not in response.text
    assert "C:\\private" not in response.text
    assert secret not in caplog.text


def test_built_frontend_is_served_with_document_security_headers(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        "<!doctype html><html><body>LeanCI container frontend</body></html>",
        encoding="utf-8",
    )
    client = TestClient(
        create_app(
            Settings(_env_file=None),
            analysis_service=FakeAnalysisService(),
            frontend_dist=tmp_path,
        )
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "LeanCI container frontend" in response.text
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
    assert response.headers["X-Frame-Options"] == "DENY"


def test_production_disables_interactive_api_documentation(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<!doctype html><title>LeanCI</title>", encoding="utf-8")
    client = TestClient(
        create_app(
            Settings(
                _env_file=None,
                environment="production",
                cors_allowed_origins="https://app.example.com",
                trusted_proxy_cidrs="10.0.0.0/8",
                proxy_auth_shared_secret="test-only-internal-secret",
                distributed_rate_limit_required=True,
                daily_analysis_request_budget=25,
            ),
            analysis_service=FakeAnalysisService(),
            frontend_dist=tmp_path,
        )
    )

    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
