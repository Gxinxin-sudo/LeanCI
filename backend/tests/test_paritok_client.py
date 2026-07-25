from pathlib import Path
from typing import Any

import httpx
import pytest
from paritok.config import ParitokConfig

from app.config import Settings
from app.paritok import (
    ParitokClient,
    ParitokClientError,
    ParitokStatsSnapshot,
    calculate_stats_delta,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def response(url: str, payload: dict[str, Any], *, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        request=httpx.Request("GET", url),
    )


class FakeHttpClient:
    def __init__(self, responses: list[httpx.Response | Exception]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append({"url": url, **kwargs})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def aclose(self) -> None:
        return None


def make_settings(**overrides: Any) -> Settings:
    return Settings(
        _env_file=None,
        paritok_api_key="unit-test-only",
        **overrides,
    )


@pytest.mark.anyio
async def test_health_and_stats_use_fixed_urls_and_independent_timeouts() -> None:
    settings = make_settings(
        paritok_health_timeout_seconds=1.5,
        paritok_stats_timeout_seconds=2.5,
    )
    client_impl = FakeHttpClient(
        [
            response(settings.paritok_health_url, {"status": "ok", "version": "1.0.0"}),
            response(
                settings.paritok_stats_url,
                {
                    "total_requests": 3,
                    "input_tokens_original": 9000,
                    "input_tokens_compressed": 3000,
                    "compression_ratio": 0.333,
                    "tokens_saved": 6000,
                    "tools_filtered": 0,
                    "estimated_cost_saved_usd": "$99.99",
                },
            ),
        ]
    )
    client = ParitokClient(settings, http_client=client_impl)

    health = await client.health()
    stats = await client.stats()

    assert health.version == "1.0.0"
    assert client_impl.calls[0]["url"] == "http://127.0.0.1:8080/health"
    assert client_impl.calls[0]["timeout"] == 1.5
    assert client_impl.calls[1]["url"] == "http://127.0.0.1:8080/stats"
    assert client_impl.calls[1]["timeout"] == 2.5
    public_stats = stats.to_public().model_dump()
    assert public_stats["tokens_saved"] == 6000
    assert "estimated_cost_saved_usd" not in public_stats
    assert "99.99" not in str(public_stats)


@pytest.mark.anyio
async def test_hosted_gpu_check_sends_key_without_exposing_it() -> None:
    settings = make_settings(paritok_gpu_status_timeout_seconds=4)
    client_impl = FakeHttpClient(
        [
            response(
                settings.paritok_gpu_status_url,
                {"gpu_available": True, "message": "ready"},
            )
        ]
    )
    client = ParitokClient(settings, http_client=client_impl)

    snapshot = await client.hosted_gpu()

    assert snapshot.gpu_available is True
    assert client_impl.calls[0]["timeout"] == 4
    assert client_impl.calls[0]["headers"]["Authorization"] == "Bearer unit-test-only"
    assert "unit-test-only" not in snapshot.model_dump_json()


@pytest.mark.anyio
async def test_unavailable_stats_fail_without_fabricating_numbers() -> None:
    settings = make_settings()
    request = httpx.Request("GET", settings.paritok_stats_url)
    client_impl = FakeHttpClient([httpx.ReadTimeout("unit-test", request=request)])
    client = ParitokClient(settings, http_client=client_impl)

    with pytest.raises(ParitokClientError) as captured:
        await client.stats()

    assert captured.value.code == "PARITOK_STATS_UNAVAILABLE"
    assert "no Token metrics were fabricated" in captured.value.public_message


@pytest.mark.anyio
async def test_protocol_failure_is_mapped_to_safe_stats_error() -> None:
    settings = make_settings()
    request = httpx.Request("GET", settings.paritok_stats_url)
    client_impl = FakeHttpClient([httpx.RemoteProtocolError("unsafe details", request=request)])
    client = ParitokClient(settings, http_client=client_impl)

    with pytest.raises(ParitokClientError) as captured:
        await client.stats()

    assert captured.value.code == "PARITOK_STATS_UNAVAILABLE"
    assert "unsafe details" not in captured.value.public_message


@pytest.mark.anyio
async def test_gpu_false_fails_closed() -> None:
    settings = make_settings()
    client_impl = FakeHttpClient(
        [
            response(
                settings.paritok_gpu_status_url,
                {"gpu_available": False, "message": "offline"},
            )
        ]
    )
    client = ParitokClient(settings, http_client=client_impl)

    with pytest.raises(ParitokClientError) as captured:
        await client.hosted_gpu()

    assert captured.value.code == "PARITOK_GPU_UNAVAILABLE"


def stats(
    *,
    requests: int,
    original: int,
    compressed: int,
    saved: int,
    tools_filtered: int = 0,
) -> ParitokStatsSnapshot:
    return ParitokStatsSnapshot(
        total_requests=requests,
        input_tokens_original=original,
        input_tokens_compressed=compressed,
        compression_ratio=compressed / original if original else 0.0,
        tokens_saved=saved,
        tools_filtered=tools_filtered,
        estimated_cost_saved_usd="$123.45",
    )


def test_stats_delta_uses_only_monotonic_counters() -> None:
    delta = calculate_stats_delta(
        stats(requests=10, original=1000, compressed=400, saved=600),
        stats(requests=12, original=9000, compressed=2400, saved=6600),
    )

    assert delta.proxy_requests == 2
    assert delta.original_tokens == 8000
    assert delta.compressed_tokens == 2000
    assert delta.saved_tokens == 6000
    assert delta.compression_ratio == 0.25


def test_stats_delta_rejects_counter_reset_and_inconsistent_savings() -> None:
    before = stats(requests=10, original=1000, compressed=400, saved=600)

    with pytest.raises(ParitokClientError):
        calculate_stats_delta(
            before,
            stats(requests=9, original=1000, compressed=400, saved=600),
        )
    with pytest.raises(ParitokClientError):
        calculate_stats_delta(
            before,
            stats(requests=11, original=2000, compressed=900, saved=999),
        )


def test_repository_yaml_matches_the_installed_paritok_1_2_7_schema() -> None:
    config = ParitokConfig.from_yaml(PROJECT_ROOT / "paritok.yaml")

    assert config.use_gpu_server is True
    assert config.gpu_server.base_url == "https://www.paritok.com/api"
    assert config.gpu_server.model == "paritok-4b-v1"
    assert config.gpu_server.api_key == ""
    assert config.compression.min_tokens == 512
    assert config.compression.max_tokens == 50_000
    assert config.tool_discovery.strategy == "passthrough"
    assert config.trace.enabled is False
