import os

import pytest

from app.analysis import AnalysisService
from app.config import Settings
from app.paritok import ParitokClient, ParitokClientError


@pytest.mark.integration
@pytest.mark.anyio
async def test_real_formal_route_when_local_proxy_and_keys_exist() -> None:
    settings = Settings()
    if os.getenv("RUN_PARITOK_INTEGRATION") != "1":
        pytest.skip("Set RUN_PARITOK_INTEGRATION=1 to allow a real paid formal request")
    if (
        settings.llm_provider != "paritok"
        or not settings.deepseek_api_key_configured
        or not settings.paritok_api_key_configured
    ):
        pytest.skip("Formal Paritok mode and both local API keys are required")

    client = ParitokClient(settings)
    try:
        try:
            await client.health()
            await client.hosted_gpu()
        except ParitokClientError as exc:
            pytest.skip(f"Local Paritok integration is unavailable: {exc.code}")

        service = AnalysisService(settings, client)
        result = await service.analyze(
            "Source: integration-test.log\n"
            + "\n".join(
                f"step {index}: repeated compiler context before error TS2345"
                for index in range(800)
            )
        )
    finally:
        await client.aclose()

    assert result.compression_stats.available is True
    assert result.compression_stats.proxy_requests >= 1
    assert result.compression_stats.cumulative.total_requests >= 1
    assert result.compression_stats.model == "deepseek-v4-flash"
