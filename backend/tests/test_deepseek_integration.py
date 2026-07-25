import pytest

from app.config import Settings
from app.llm import DirectDeepSeekProvider, DirectUseCase


@pytest.mark.integration
@pytest.mark.anyio
async def test_real_deepseek_connection_when_local_key_exists() -> None:
    settings = Settings()
    if not settings.deepseek_api_key_configured:
        pytest.skip("DEEPSEEK_API_KEY is not configured in the local environment")

    provider = DirectDeepSeekProvider.from_settings(
        settings,
        use_case=DirectUseCase.CONNECTION_TEST,
    )
    result = await provider.analyze(
        "Source: integration-test.log\nUNTRUSTED DATA: type checking stopped with exit code 1."
    )

    assert result.model == "deepseek-v4-flash"
    assert result.usage is not None
    assert result.usage.total_tokens > 0
