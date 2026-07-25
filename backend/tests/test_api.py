from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import DEMO_NOTICE, MAX_LOG_CHARACTERS


def make_client(settings: Settings | None = None) -> TestClient:
    return TestClient(create_app(settings))


def test_health_is_explicitly_demo_only() -> None:
    response = make_client().get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "leanci-api",
        "mode": "demo",
        "paritok_connected": False,
        "deepseek_called": False,
        "message": DEMO_NOTICE,
    }
    assert len(response.headers["X-Request-ID"]) == 32


def test_config_status_only_exposes_secret_presence() -> None:
    settings = Settings(
        _env_file=None,
        deepseek_api_key="test-only",
        paritok_api_key="test-only",
    )
    response = make_client(settings).get("/api/config-status")

    assert response.status_code == 200
    assert response.json() == {
        "deepseek_api_key_configured": True,
        "paritok_api_key_configured": True,
    }
    assert "test-only" not in response.text


def test_mock_analysis_returns_complete_contract_without_token_numbers() -> None:
    response = make_client().post(
        "/api/analyze",
        json={"log_text": "src/services/report.ts:42: type error"},
    )

    assert response.status_code == 200
    result = response.json()
    assert set(result) == {
        "summary",
        "root_cause",
        "confidence",
        "evidence",
        "relevant_files",
        "recommended_changes",
        "patch",
        "verification_commands",
        "risks",
        "missing_information",
        "compression_stats",
    }
    assert result["compression_stats"] == {
        "available": False,
        "paritok_connected": False,
        "original_tokens": None,
        "compressed_tokens": None,
        "saved_tokens": None,
        "compression_ratio": None,
        "message": DEMO_NOTICE,
    }


def test_whitespace_log_uses_unified_error_response() -> None:
    response = make_client().post("/api/analyze", json={"log_text": "   \n"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_LOG"
    assert response.json()["error"]["message"] == "Paste a CI log before starting analysis."
    assert len(response.json()["error"]["request_id"]) == 32


def test_oversized_log_does_not_echo_input() -> None:
    oversized_log = "x" * (MAX_LOG_CHARACTERS + 1)
    response = make_client().post("/api/analyze", json={"log_text": oversized_log})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert oversized_log[:100] not in response.text


def test_configured_log_limit_is_enforced_server_side() -> None:
    settings = Settings(_env_file=None, max_log_characters=4)
    response = make_client(settings).post("/api/analyze", json={"log_text": "12345"})

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "LOG_TOO_LARGE"


def test_unknown_route_uses_unified_error_response() -> None:
    response = make_client().get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
