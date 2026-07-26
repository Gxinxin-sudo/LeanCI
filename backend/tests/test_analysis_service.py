import asyncio
import json
import os
import subprocess
from typing import Any

import pytest

from app.analysis import AnalysisService
from app.config import Settings
from app.errors import AppError
from app.llm import LLMProvider, LLMProviderError
from app.models import DiagnosticAnalysis, ProviderResult
from app.paritok import (
    HostedGpuSnapshot,
    ParitokClientError,
    ParitokStatsSnapshot,
    ProxyHealthSnapshot,
)

VALID_ANALYSIS = DiagnosticAnalysis.model_validate(
    {
        "summary": "Type checking failed.",
        "root_cause": "A required string received an undefined value.",
        "confidence": 0.95,
        "evidence": [
            {
                "source": "ci.log",
                "line_start": 8,
                "line_end": 8,
                "excerpt": "error TS2345",
                "explanation": "The compiler identifies the type mismatch.",
            }
        ],
        "relevant_files": ["src/config.ts"],
        "recommended_changes": ["Validate the environment value."],
        "patch": "",
        "verification_commands": ["npm run typecheck"],
        "risks": ["Deployment configuration may be incomplete."],
        "missing_information": ["The deployment environment was not supplied."],
    }
)


def snapshot(
    *,
    requests: int,
    original: int,
    compressed: int,
    saved: int,
) -> ParitokStatsSnapshot:
    return ParitokStatsSnapshot(
        total_requests=requests,
        input_tokens_original=original,
        input_tokens_compressed=compressed,
        compression_ratio=compressed / original if original else 0.0,
        tokens_saved=saved,
        tools_filtered=0,
        estimated_cost_saved_usd="$9000.00",
    )


class FakeParitokClient:
    def __init__(
        self,
        stats: list[ParitokStatsSnapshot | Exception],
        *,
        health_error: ParitokClientError | None = None,
        gpu_error: ParitokClientError | None = None,
    ) -> None:
        self.stats_items = stats
        self.health_error = health_error
        self.gpu_error = gpu_error
        self.gpu_checks = 0

    async def health(self) -> ProxyHealthSnapshot:
        if self.health_error:
            raise self.health_error
        return ProxyHealthSnapshot(status="ok", version="1.0.0")

    async def hosted_gpu(self) -> HostedGpuSnapshot:
        self.gpu_checks += 1
        if self.gpu_error:
            raise self.gpu_error
        return HostedGpuSnapshot(gpu_available=True, message="ready")

    async def stats(self) -> ParitokStatsSnapshot:
        item = self.stats_items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeProvider(LLMProvider):
    def __init__(
        self,
        *,
        request_attempts: int = 1,
        failure: LLMProviderError | None = None,
        pause: float = 0,
        analysis: DiagnosticAnalysis = VALID_ANALYSIS,
    ) -> None:
        self.request_attempts = request_attempts
        self.failure = failure
        self.pause = pause
        self.analysis = analysis
        self.active = 0
        self.max_active = 0

    async def analyze(self, untrusted_context: str) -> ProviderResult:
        del untrusted_context
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.pause:
                await asyncio.sleep(self.pause)
            if self.failure:
                raise self.failure
            return ProviderResult(
                provider="paritok_deepseek",
                model="deepseek-v4-flash",
                analysis=self.analysis,
                usage=None,
                request_attempts=self.request_attempts,
            )
        finally:
            self.active -= 1


def settings(**overrides: Any) -> Settings:
    values = {
        "deepseek_api_key": "unit-test-only",
        "paritok_api_key": "unit-test-only",
        **overrides,
    }
    return Settings(_env_file=None, **values)


@pytest.mark.anyio
async def test_formal_analysis_returns_verified_delta_and_lean_cost_estimate() -> None:
    paritok = FakeParitokClient(
        [
            snapshot(requests=10, original=1000, compressed=400, saved=600),
            snapshot(requests=11, original=9000, compressed=2400, saved=6600),
        ]
    )
    service = AnalysisService(settings(), paritok, provider=FakeProvider())  # type: ignore[arg-type]

    result = await service.analyze("untrusted")

    stats = result.compression_stats
    assert stats.available is True
    assert stats.original_tokens == 8000
    assert stats.compressed_tokens == 2000
    assert stats.saved_tokens == 6000
    assert stats.compression_ratio == 0.25
    assert stats.cumulative.total_requests == 11
    assert stats.cost_estimate.estimated_input_cost_saved_usd == 0.00084
    assert stats.cost_estimate.input_cache_miss_usd_per_m_tokens == 0.14
    assert "$9000.00" not in stats.model_dump_json()
    assert "estimated_cost_saved_usd" not in stats.model_dump_json()
    assert paritok.gpu_checks == 2


@pytest.mark.anyio
async def test_proxy_request_count_must_match_provider_attempts() -> None:
    paritok = FakeParitokClient(
        [
            snapshot(requests=10, original=1000, compressed=400, saved=600),
            snapshot(requests=12, original=9000, compressed=2400, saved=6600),
        ]
    )
    service = AnalysisService(settings(), paritok, provider=FakeProvider())  # type: ignore[arg-type]

    with pytest.raises(AppError) as captured:
        await service.analyze("untrusted")

    assert captured.value.status_code == 503
    assert captured.value.code == "PARITOK_ROUTE_NOT_VERIFIED"


@pytest.mark.anyio
async def test_formal_analysis_fails_closed_when_paritok_skips_all_evidence() -> None:
    paritok = FakeParitokClient(
        [
            snapshot(requests=10, original=1000, compressed=400, saved=600),
            snapshot(requests=11, original=1000, compressed=400, saved=600),
        ]
    )
    service = AnalysisService(settings(), paritok, provider=FakeProvider())  # type: ignore[arg-type]

    with pytest.raises(AppError) as captured:
        await service.analyze("untrusted")

    assert captured.value.status_code == 503
    assert captured.value.code == "PARITOK_COMPRESSION_SKIPPED"
    assert "discarded" in captured.value.message


@pytest.mark.anyio
async def test_stats_failure_discards_analysis_and_returns_503() -> None:
    error = ParitokClientError(
        code="PARITOK_STATS_UNAVAILABLE",
        message="Paritok stats are unavailable; no Token metrics were fabricated.",
    )
    paritok = FakeParitokClient([error])
    service = AnalysisService(settings(), paritok, provider=FakeProvider())  # type: ignore[arg-type]

    with pytest.raises(AppError) as captured:
        await service.analyze("untrusted")

    assert captured.value.status_code == 503
    assert captured.value.code == "PARITOK_STATS_UNAVAILABLE"


@pytest.mark.anyio
async def test_deepseek_failure_is_clear_and_safe() -> None:
    paritok = FakeParitokClient([snapshot(requests=10, original=1000, compressed=400, saved=600)])
    provider = FakeProvider(
        failure=LLMProviderError(
            code="DEEPSEEK_SERVER_ERROR",
            message="DeepSeek is temporarily unavailable (server error). Try again later.",
        )
    )
    service = AnalysisService(settings(), paritok, provider=provider)  # type: ignore[arg-type]

    with pytest.raises(AppError) as captured:
        await service.analyze("untrusted")

    assert captured.value.status_code == 502
    assert captured.value.code == "DEEPSEEK_SERVER_ERROR"
    assert "temporarily unavailable" in captured.value.message


@pytest.mark.anyio
async def test_analysis_lock_prevents_stats_window_overlap() -> None:
    paritok = FakeParitokClient(
        [
            snapshot(requests=0, original=0, compressed=0, saved=0),
            snapshot(requests=1, original=1000, compressed=500, saved=500),
            snapshot(requests=1, original=1000, compressed=500, saved=500),
            snapshot(requests=2, original=2000, compressed=1000, saved=1000),
        ]
    )
    provider = FakeProvider(pause=0.01)
    service = AnalysisService(settings(), paritok, provider=provider)  # type: ignore[arg-type]

    results = await asyncio.gather(
        service.analyze("first"),
        service.analyze("second"),
    )

    assert len(results) == 2
    assert provider.max_active == 1


@pytest.mark.anyio
async def test_health_does_not_call_deepseek_and_reports_gpu_failure() -> None:
    error = ParitokClientError(
        code="PARITOK_GPU_UNAVAILABLE",
        message="The Paritok hosted GPU is unavailable; formal analysis was not sent.",
    )
    paritok = FakeParitokClient([], gpu_error=error)
    provider = FakeProvider()
    service = AnalysisService(settings(), paritok, provider=provider)  # type: ignore[arg-type]

    result = await service.health()

    assert result.status == "degraded"
    assert result.paritok_connected is True
    assert result.hosted_gpu_available is False
    assert result.deepseek_called is False
    assert provider.max_active == 0


@pytest.mark.anyio
async def test_health_is_degraded_when_deepseek_key_is_missing() -> None:
    paritok = FakeParitokClient([])
    service = AnalysisService(
        settings(deepseek_api_key=None),
        paritok,  # type: ignore[arg-type]
        provider=FakeProvider(),
    )

    result = await service.health()

    assert result.status == "degraded"
    assert result.paritok_connected is True
    assert result.hosted_gpu_available is True
    assert result.deepseek_called is False
    assert result.message.startswith("DEEPSEEK_API_KEY is not configured")


@pytest.mark.anyio
async def test_missing_deepseek_key_fails_before_any_paritok_request() -> None:
    paritok = FakeParitokClient([])
    service = AnalysisService(
        settings(deepseek_api_key=None),
        paritok,  # type: ignore[arg-type]
        provider=FakeProvider(),
    )

    with pytest.raises(AppError) as captured:
        await service.analyze("untrusted")

    assert captured.value.status_code == 503
    assert captured.value.code == "DEEPSEEK_API_KEY_MISSING"
    assert paritok.gpu_checks == 0


def test_response_serialization_never_contains_paritok_cost_field_name() -> None:
    public = snapshot(
        requests=1,
        original=1000,
        compressed=500,
        saved=500,
    ).to_public()

    assert "estimated_cost_saved_usd" not in json.dumps(public.model_dump())


@pytest.mark.anyio
async def test_model_patch_and_commands_are_returned_as_text_and_never_executed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dangerous_command = "python -c \"raise SystemExit('must not run')\""
    dangerous_patch = "*** Begin Patch\n*** Delete File: important.txt\n*** End Patch"
    analysis = VALID_ANALYSIS.model_copy(
        update={
            "patch": dangerous_patch,
            "verification_commands": [dangerous_command],
        }
    )
    paritok = FakeParitokClient(
        [
            snapshot(requests=0, original=0, compressed=0, saved=0),
            snapshot(requests=1, original=8000, compressed=2000, saved=6000),
        ]
    )

    def fail_execution(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("model-controlled execution was attempted")

    monkeypatch.setattr(os, "system", fail_execution)
    monkeypatch.setattr(subprocess, "run", fail_execution)
    service = AnalysisService(
        settings(),
        paritok,  # type: ignore[arg-type]
        provider=FakeProvider(analysis=analysis),
    )

    result = await service.analyze("untrusted log with fake system instructions")

    assert result.patch == dangerous_patch
    assert result.verification_commands == [dangerous_command]
