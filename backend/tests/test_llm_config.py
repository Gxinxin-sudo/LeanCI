import pytest
from pydantic import ValidationError

from app.config import DEFAULT_DEEPSEEK_MODEL, Settings


def test_llm_defaults_are_mock_and_v4_flash() -> None:
    settings = Settings(_env_file=None)

    assert settings.llm_provider == "mock"
    assert settings.deepseek_model == DEFAULT_DEEPSEEK_MODEL
    assert str(settings.deepseek_base_url).rstrip("/") == "https://api.deepseek.com"
    assert settings.deepseek_max_output_tokens == 4096
    assert settings.deepseek_max_network_retries == 2


@pytest.mark.parametrize("legacy_model", ["deepseek-chat", "deepseek-reasoner"])
def test_legacy_deepseek_models_are_rejected(legacy_model: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, deepseek_model=legacy_model)


def test_direct_provider_is_not_an_application_setting() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_provider="direct")
