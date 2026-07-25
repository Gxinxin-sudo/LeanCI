import pytest
from pydantic import ValidationError

from app.config import DEFAULT_DEEPSEEK_MODEL, Settings


def test_llm_defaults_are_paritok_and_v4_flash() -> None:
    settings = Settings(_env_file=None)

    assert settings.llm_provider == "paritok"
    assert settings.deepseek_model == DEFAULT_DEEPSEEK_MODEL
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.paritok_proxy_base_url == "http://127.0.0.1:8080/v1"
    assert settings.paritok_health_url == "http://127.0.0.1:8080/health"
    assert settings.paritok_stats_url == "http://127.0.0.1:8080/stats"
    assert settings.paritok_gpu_status_url == "https://www.paritok.com/api/test"
    assert settings.deepseek_max_output_tokens == 4096
    assert settings.deepseek_max_network_retries == 2
    assert settings.paritok_health_timeout_seconds == 3
    assert settings.paritok_stats_timeout_seconds == 3


@pytest.mark.parametrize("legacy_model", ["deepseek-chat", "deepseek-reasoner"])
def test_legacy_deepseek_models_are_rejected(legacy_model: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, deepseek_model=legacy_model)


def test_direct_provider_is_not_an_application_setting() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_provider="direct")


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("deepseek_base_url", "https://example.com"),
        ("paritok_proxy_base_url", "http://127.0.0.1:9999/v1"),
        ("paritok_health_url", "http://example.com/health"),
        ("paritok_stats_url", "http://example.com/stats"),
        ("paritok_gpu_status_url", "https://example.com/test"),
        (
            "paritok_upstream_chat_completions_url",
            "https://api.deepseek.com/v1/chat/completions",
        ),
    ],
)
def test_formal_urls_are_fixed(field: str, invalid_value: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: invalid_value})
