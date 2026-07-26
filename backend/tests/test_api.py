from typing import Any

from fastapi.testclient import TestClient

from app.config import Settings
from app.errors import AppError
from app.main import create_app
from app.models import (
    MAX_LOG_CHARACTERS,
    MAX_REQUEST_BYTES,
    AnalysisResult,
    CumulativeParitokStats,
    DeepSeekCostEstimate,
    EvidenceItem,
    HealthResponse,
    VerifiedCompressionStats,
)


def build_result() -> AnalysisResult:
    return AnalysisResult(
        summary="Type checking failed.",
        root_cause="A required string received an undefined value.",
        confidence=0.95,
        evidence=[
            EvidenceItem(
                source="ci.log",
                line_start=8,
                line_end=8,
                excerpt="error TS2345",
                explanation="The compiler identifies the type mismatch.",
            )
        ],
        relevant_files=["src/config.ts"],
        recommended_changes=["Validate the environment value."],
        patch="",
        verification_commands=["npm run typecheck"],
        risks=["Deployment configuration may be incomplete."],
        missing_information=["The deployment environment was not supplied."],
        analysis_time_ms=1324,
        compression_stats=VerifiedCompressionStats(
            proxy_version="1.0.0",
            model="deepseek-v4-flash",
            proxy_requests=1,
            original_tokens=8000,
            compressed_tokens=2000,
            saved_tokens=6000,
            compression_ratio=0.25,
            cumulative=CumulativeParitokStats(
                total_requests=12,
                input_tokens_original=80_000,
                input_tokens_compressed=20_000,
                compression_ratio=0.25,
                tokens_saved=60_000,
                tools_filtered=0,
            ),
            cost_estimate=DeepSeekCostEstimate(
                estimated_input_cost_saved_usd=0.00084,
                input_cache_miss_usd_per_m_tokens=0.14,
                pricing_snapshot_date="2026-07-26",
            ),
        ),
    )


class FakeAnalysisService:
    def __init__(self, *, failure: AppError | None = None) -> None:
        self.failure = failure
        self.inputs: list[str] = []

    async def health(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="leanci-api",
            mode="paritok",
            paritok_connected=True,
            hosted_gpu_available=True,
            proxy_version="1.0.0",
            model="deepseek-v4-flash",
            deepseek_called=False,
            message="Local Paritok Proxy and hosted GPU are available.",
        )

    async def analyze(self, untrusted_context: str) -> AnalysisResult:
        self.inputs.append(untrusted_context)
        if self.failure:
            raise self.failure
        return build_result()


def make_client(
    settings: Settings | None = None,
    *,
    service: Any | None = None,
) -> TestClient:
    active_settings = settings or Settings(_env_file=None)
    return TestClient(
        create_app(
            active_settings,
            analysis_service=service or FakeAnalysisService(),
        )
    )


def test_health_reports_paritok_and_hosted_gpu() -> None:
    response = make_client().get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "leanci-api",
        "mode": "paritok",
        "paritok_connected": True,
        "hosted_gpu_available": True,
        "proxy_version": "1.0.0",
        "model": "deepseek-v4-flash",
        "deepseek_called": False,
        "message": "Local Paritok Proxy and hosted GPU are available.",
    }
    assert len(response.headers["X-Request-ID"]) == 32


def test_config_status_only_exposes_secret_presence_and_safe_metadata() -> None:
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
        "llm_provider": "paritok",
        "model": "deepseek-v4-flash",
    }
    assert "test-only" not in response.text


def test_formal_analysis_returns_verified_request_and_cumulative_stats() -> None:
    service = FakeAnalysisService()
    response = make_client(service=service).post(
        "/api/analyze",
        json={"log_text": "src/services/report.ts:42: type error"},
    )

    assert response.status_code == 200
    result = response.json()
    assert len(service.inputs) == 1
    assert '<CI_LOG source="ci.log">' in service.inputs[0]
    assert "src/services/report.ts:42: type error" in service.inputs[0]
    assert result["compression_stats"]["available"] is True
    assert result["compression_stats"]["verification"] == (
        "local_health+hosted_gpu_preflight+stats_delta"
    )
    assert result["compression_stats"]["original_tokens"] == 8000
    assert result["compression_stats"]["compressed_tokens"] == 2000
    assert result["compression_stats"]["saved_tokens"] == 6000
    assert result["compression_stats"]["cumulative"]["total_requests"] == 12
    assert "estimated_cost_saved_usd" not in result["compression_stats"]["cumulative"]
    assert result["compression_stats"]["cost_estimate"]["pricing_snapshot_date"] == "2026-07-26"
    assert result["analysis_time_ms"] == 1324


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


def test_request_body_hard_limit_is_enforced_before_json_parsing() -> None:
    response = make_client().post(
        "/api/analyze",
        content=b"x" * (MAX_REQUEST_BYTES + 1),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
    assert response.json()["error"]["message"] == "The request body exceeds the 4 MiB limit."


def test_uploaded_files_are_wrapped_as_untrusted_context() -> None:
    service = FakeAnalysisService()
    response = make_client(service=service).post(
        "/api/analyze",
        json={
            "log_text": "pytest failed",
            "files": [{"name": " retry config.py ", "content": "MAX_RETRIES = 3\n"}],
        },
    )

    assert response.status_code == 200
    assert 'name="retry_config.py"' in service.inputs[0]
    assert "MAX_RETRIES = 3" in service.inputs[0]


def test_bundled_sample_api_uses_fixed_ids() -> None:
    client = make_client()
    listing = client.get("/api/samples")
    sample = client.get("/api/samples/python-pytest")
    traversal = client.get("/api/samples/..%2F.env")

    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [
        "python-pytest",
        "typescript-build",
        "docker-build",
        "dependency-resolution",
        "github-actions-environment",
    ]
    assert sample.status_code == 200
    assert sample.json()["log_bytes"] > 30_000
    assert len(sample.json()["files"]) == 3
    assert traversal.status_code in {404, 422}


def test_benchmark_api_returns_every_fixed_case_and_both_modes() -> None:
    client = make_client()

    response = client.get("/api/benchmark/results")

    assert response.status_code == 200
    payload = response.json()
    assert payload["finalized"] is True
    assert len(payload["rows"]) == 10
    assert {(row["case_id"], row["mode"]) for row in payload["rows"]} == {
        (case_id, mode)
        for case_id in payload["case_ids"]
        for mode in ("baseline_uncompressed", "paritok")
    }


def test_paritok_failure_is_returned_as_503_without_internal_details() -> None:
    failure = AppError(
        status_code=503,
        code="PARITOK_UNAVAILABLE",
        message="The local Paritok Proxy is unavailable.",
    )
    response = make_client(service=FakeAnalysisService(failure=failure)).post(
        "/api/analyze",
        json={"log_text": "failure"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PARITOK_UNAVAILABLE"
    assert "C:\\" not in response.text


def test_unknown_route_uses_unified_error_response() -> None:
    response = make_client().get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
