"""Fail-closed formal analysis orchestration."""

from __future__ import annotations

import asyncio
from decimal import ROUND_HALF_UP, Decimal
from time import perf_counter

from app.config import Settings
from app.errors import AppError
from app.llm import LLMProvider, LLMProviderError, build_application_provider
from app.models import (
    AnalysisResult,
    DeepSeekCostEstimate,
    HealthResponse,
    ProviderResult,
    VerifiedCompressionStats,
)
from app.paritok import (
    ParitokClient,
    ParitokClientError,
    calculate_stats_delta,
)

_USD_QUANTUM = Decimal("0.00000001")


def _provider_error_to_app_error(exc: LLMProviderError) -> AppError:
    if exc.code in {
        "FORMAL_ANALYSIS_REQUIRES_PARITOK",
        "PARITOK_PROXY_UNAVAILABLE",
        "DEEPSEEK_API_KEY_MISSING",
    }:
        status_code = 503
    elif exc.code == "DEEPSEEK_TIMEOUT":
        status_code = 504
    else:
        status_code = 502
    return AppError(
        status_code=status_code,
        code=exc.code,
        message=exc.public_message,
    )


def _paritok_error_to_app_error(exc: ParitokClientError) -> AppError:
    return AppError(
        status_code=503,
        code=exc.code,
        message=exc.public_message,
    )


class AnalysisService:
    """Own the only formal path from FastAPI through Paritok to DeepSeek."""

    def __init__(
        self,
        settings: Settings,
        paritok_client: ParitokClient,
        *,
        provider: LLMProvider | None = None,
    ) -> None:
        self.settings = settings
        self.paritok_client = paritok_client
        self._provider = provider
        self._analysis_lock = asyncio.Lock()

    async def health(self) -> HealthResponse:
        """Return a safe aggregate status without calling DeepSeek."""

        if self.settings.llm_provider != "paritok":
            return HealthResponse(
                status="degraded",
                service="leanci-api",
                mode="paritok",
                paritok_connected=False,
                hosted_gpu_available=False,
                proxy_version=None,
                model=self.settings.deepseek_model,
                deepseek_called=False,
                message="Formal analysis requires LLM_PROVIDER=paritok.",
            )

        proxy_version: str | None = None
        paritok_connected = False
        hosted_gpu_available = False
        try:
            health = await self.paritok_client.health()
            proxy_version = health.version
            paritok_connected = True
        except ParitokClientError as exc:
            return HealthResponse(
                status="degraded",
                service="leanci-api",
                mode="paritok",
                paritok_connected=False,
                hosted_gpu_available=False,
                proxy_version=None,
                model=self.settings.deepseek_model,
                deepseek_called=False,
                message=exc.public_message,
            )

        try:
            await self.paritok_client.hosted_gpu()
            hosted_gpu_available = True
        except ParitokClientError as exc:
            return HealthResponse(
                status="degraded",
                service="leanci-api",
                mode="paritok",
                paritok_connected=paritok_connected,
                hosted_gpu_available=False,
                proxy_version=proxy_version,
                model=self.settings.deepseek_model,
                deepseek_called=False,
                message=exc.public_message,
            )

        if not self.settings.deepseek_api_key_configured:
            return HealthResponse(
                status="degraded",
                service="leanci-api",
                mode="paritok",
                paritok_connected=paritok_connected,
                hosted_gpu_available=hosted_gpu_available,
                proxy_version=proxy_version,
                model=self.settings.deepseek_model,
                deepseek_called=False,
                message="DEEPSEEK_API_KEY is not configured; formal analysis is unavailable.",
            )

        return HealthResponse(
            status="ok",
            service="leanci-api",
            mode="paritok",
            paritok_connected=paritok_connected,
            hosted_gpu_available=hosted_gpu_available,
            proxy_version=proxy_version,
            model=self.settings.deepseek_model,
            deepseek_called=False,
            message="Local Paritok Proxy and hosted GPU are available.",
        )

    async def analyze(self, untrusted_context: str) -> AnalysisResult:
        """Run one serialized, stats-verified production analysis."""

        started_at = perf_counter()
        if self.settings.llm_provider != "paritok":
            raise _provider_error_to_app_error(
                LLMProviderError(
                    code="FORMAL_ANALYSIS_REQUIRES_PARITOK",
                    message=(
                        "Formal analysis is disabled until LLM_PROVIDER=paritok. "
                        "Mock and direct modes cannot serve /api/analyze."
                    ),
                )
            )
        if not self.settings.deepseek_api_key_configured:
            raise _provider_error_to_app_error(
                LLMProviderError(
                    code="DEEPSEEK_API_KEY_MISSING",
                    message=(
                        "DEEPSEEK_API_KEY is not configured. Add it only to the local .env file."
                    ),
                )
            )

        async with self._analysis_lock:
            try:
                health = await self.paritok_client.health()
                await self.paritok_client.hosted_gpu()
                before = await self.paritok_client.stats()
            except ParitokClientError as exc:
                raise _paritok_error_to_app_error(exc) from exc

            try:
                provider = self._provider or build_application_provider(self.settings)
                provider_result = await provider.analyze(untrusted_context)
            except LLMProviderError as exc:
                raise _provider_error_to_app_error(exc) from exc

            try:
                after = await self.paritok_client.stats()
                await self.paritok_client.hosted_gpu()
                delta = calculate_stats_delta(before, after)
            except ParitokClientError as exc:
                raise _paritok_error_to_app_error(exc) from exc

            self._validate_proxy_proof(provider_result, delta.proxy_requests)
            estimated_cost = self._estimate_input_cost(delta.saved_tokens)

            return AnalysisResult(
                **provider_result.analysis.model_dump(),
                analysis_time_ms=round((perf_counter() - started_at) * 1000),
                compression_stats=VerifiedCompressionStats(
                    proxy_version=health.version,
                    model=self.settings.deepseek_model,
                    proxy_requests=delta.proxy_requests,
                    original_tokens=delta.original_tokens,
                    compressed_tokens=delta.compressed_tokens,
                    saved_tokens=delta.saved_tokens,
                    compression_ratio=delta.compression_ratio,
                    cumulative=after.to_public(),
                    cost_estimate=DeepSeekCostEstimate(
                        estimated_input_cost_saved_usd=estimated_cost,
                        input_cache_miss_usd_per_m_tokens=float(
                            self.settings.deepseek_input_cache_miss_usd_per_m
                        ),
                        pricing_snapshot_date=self.settings.pricing_snapshot_date.isoformat(),
                    ),
                ),
            )

    @staticmethod
    def _validate_proxy_proof(provider_result: ProviderResult, proxy_requests: int) -> None:
        if (
            provider_result.provider != "paritok_deepseek"
            or provider_result.usage is not None
            or provider_result.request_attempts < 1
            or proxy_requests != provider_result.request_attempts
        ):
            raise AppError(
                status_code=503,
                code="PARITOK_ROUTE_NOT_VERIFIED",
                message=(
                    "The Paritok stats delta did not match this analysis request; "
                    "the result was discarded."
                ),
            )

    def _estimate_input_cost(self, saved_tokens: int) -> float:
        value = (
            Decimal(saved_tokens)
            * self.settings.deepseek_input_cache_miss_usd_per_m
            / Decimal(1_000_000)
        )
        return float(value.quantize(_USD_QUANTUM, rounding=ROUND_HALF_UP))
