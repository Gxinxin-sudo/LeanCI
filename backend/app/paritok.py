"""Strict Paritok health, hosted-GPU, and cumulative-stats client."""

from __future__ import annotations

from typing import Any, Literal, Protocol

import httpx
from pydantic import Field, ValidationError

from app.config import Settings
from app.models import CumulativeParitokStats, StrictModel


class ParitokClientError(RuntimeError):
    """A safe, stable Paritok failure that never includes upstream response text."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message


class AsyncHttpClient(Protocol):
    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Issue one GET request."""

    async def aclose(self) -> None:
        """Close owned resources."""


class ProxyHealthSnapshot(StrictModel):
    status: Literal["ok"]
    version: str = Field(min_length=1, max_length=80)


class HostedGpuSnapshot(StrictModel):
    gpu_available: bool
    message: str = Field(default="", max_length=500)


class ParitokStatsSnapshot(StrictModel):
    """Exact Paritok 1.2.7 payload, including one excluded dollar field."""

    total_requests: int = Field(ge=0)
    input_tokens_original: int = Field(ge=0)
    input_tokens_compressed: int = Field(ge=0)
    compression_ratio: float = Field(ge=0)
    tokens_saved: int = Field(ge=0)
    tools_filtered: int = Field(ge=0)
    estimated_cost_saved_usd: str | float = Field(exclude=True)

    def to_public(self) -> CumulativeParitokStats:
        """Drop Paritok's model-price estimate before returning cumulative data."""

        return CumulativeParitokStats(
            total_requests=self.total_requests,
            input_tokens_original=self.input_tokens_original,
            input_tokens_compressed=self.input_tokens_compressed,
            compression_ratio=self.compression_ratio,
            tokens_saved=self.tokens_saved,
            tools_filtered=self.tools_filtered,
        )


class ParitokStatsDelta(StrictModel):
    proxy_requests: int = Field(ge=0)
    original_tokens: int = Field(ge=0)
    compressed_tokens: int = Field(ge=0)
    saved_tokens: int = Field(ge=0)
    tools_filtered: int = Field(ge=0)
    compression_ratio: float = Field(ge=0)


def calculate_stats_delta(
    before: ParitokStatsSnapshot,
    after: ParitokStatsSnapshot,
) -> ParitokStatsDelta:
    """Validate monotonic counters and derive one request-window delta."""

    proxy_requests = after.total_requests - before.total_requests
    original_tokens = after.input_tokens_original - before.input_tokens_original
    compressed_tokens = after.input_tokens_compressed - before.input_tokens_compressed
    saved_tokens = after.tokens_saved - before.tokens_saved
    tools_filtered = after.tools_filtered - before.tools_filtered
    values = (
        proxy_requests,
        original_tokens,
        compressed_tokens,
        saved_tokens,
        tools_filtered,
    )
    if any(value < 0 for value in values):
        raise ParitokClientError(
            code="PARITOK_STATS_INVALID",
            message="Paritok stats counters moved backwards; no Token metrics were returned.",
        )
    if compressed_tokens > original_tokens or saved_tokens != original_tokens - compressed_tokens:
        raise ParitokClientError(
            code="PARITOK_STATS_INVALID",
            message="Paritok stats were internally inconsistent; no Token metrics were returned.",
        )

    compression_ratio = compressed_tokens / original_tokens if original_tokens else 0.0
    return ParitokStatsDelta(
        proxy_requests=proxy_requests,
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        saved_tokens=saved_tokens,
        tools_filtered=tools_filtered,
        compression_ratio=round(compression_ratio, 6),
    )


class ParitokClient:
    """Read only the fixed Paritok endpoints from validated application settings."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: AsyncHttpClient | None = None,
    ) -> None:
        self.settings = settings
        self._client = http_client or httpx.AsyncClient(follow_redirects=False)
        self._owns_client = http_client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def health(self) -> ProxyHealthSnapshot:
        data = await self._get_json(
            self.settings.paritok_health_url,
            timeout=self.settings.paritok_health_timeout_seconds,
            code="PARITOK_UNAVAILABLE",
            message=(
                "The local Paritok Proxy is unavailable. Start it and keep its terminal open."
            ),
        )
        try:
            return ProxyHealthSnapshot.model_validate(data)
        except ValidationError as exc:
            raise ParitokClientError(
                code="PARITOK_HEALTH_INVALID",
                message="Paritok returned an invalid health response.",
            ) from exc

    async def hosted_gpu(self) -> HostedGpuSnapshot:
        if not self.settings.paritok_api_key_configured:
            raise ParitokClientError(
                code="PARITOK_API_KEY_MISSING",
                message="PARITOK_API_KEY is not configured in the local environment.",
            )
        assert self.settings.paritok_api_key is not None
        headers = {"Authorization": f"Bearer {self.settings.paritok_api_key.get_secret_value()}"}
        data = await self._get_json(
            self.settings.paritok_gpu_status_url,
            timeout=self.settings.paritok_gpu_status_timeout_seconds,
            code="PARITOK_GPU_UNAVAILABLE",
            message="The Paritok hosted GPU is unavailable; formal analysis was not sent.",
            headers=headers,
            auth_failure_code="PARITOK_AUTHENTICATION_FAILED",
            auth_failure_message="The Paritok hosted service rejected PARITOK_API_KEY.",
        )
        try:
            snapshot = HostedGpuSnapshot.model_validate(data)
        except ValidationError as exc:
            raise ParitokClientError(
                code="PARITOK_GPU_STATUS_INVALID",
                message="Paritok returned an invalid hosted GPU status response.",
            ) from exc
        if not snapshot.gpu_available:
            raise ParitokClientError(
                code="PARITOK_GPU_UNAVAILABLE",
                message="The Paritok hosted GPU is unavailable; formal analysis was not sent.",
            )
        return snapshot

    async def stats(self) -> ParitokStatsSnapshot:
        data = await self._get_json(
            self.settings.paritok_stats_url,
            timeout=self.settings.paritok_stats_timeout_seconds,
            code="PARITOK_STATS_UNAVAILABLE",
            message="Paritok stats are unavailable; no Token metrics were fabricated.",
        )
        try:
            return ParitokStatsSnapshot.model_validate(data)
        except ValidationError as exc:
            raise ParitokClientError(
                code="PARITOK_STATS_INVALID",
                message="Paritok returned invalid stats; no Token metrics were fabricated.",
            ) from exc

    async def _get_json(
        self,
        url: str,
        *,
        timeout: float,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
        auth_failure_code: str | None = None,
        auth_failure_message: str | None = None,
    ) -> Any:
        try:
            response = await self._client.get(url, headers=headers, timeout=timeout)
        except httpx.RequestError as exc:
            raise ParitokClientError(code=code, message=message) from exc

        if response.status_code in (401, 403) and auth_failure_code:
            raise ParitokClientError(
                code=auth_failure_code,
                message=auth_failure_message or message,
            )
        if response.status_code >= 400:
            raise ParitokClientError(code=code, message=message)
        try:
            return response.json()
        except ValueError as exc:
            raise ParitokClientError(code=code, message=message) from exc
