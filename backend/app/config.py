"""Application configuration loaded from environment variables."""

from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
ApplicationProviderName = Literal["mock", "paritok"]
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
PARITOK_PROXY_BASE_URL = "http://127.0.0.1:8080/v1"
PARITOK_HEALTH_URL = "http://127.0.0.1:8080/health"
PARITOK_STATS_URL = "http://127.0.0.1:8080/stats"
PARITOK_GPU_STATUS_URL = "https://www.paritok.com/api/test"
PARITOK_UPSTREAM_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/chat/completions"


class Settings(BaseSettings):
    """Validated application configuration.

    Secrets remain wrapped as ``SecretStr`` and are never returned from public
    endpoints. Direct DeepSeek access is intentionally not an application mode.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    app_name: str = "LeanCI API"
    environment: str = "development"
    max_log_characters: int = Field(default=120_000, ge=1, le=120_000)
    llm_provider: ApplicationProviderName = "paritok"
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: Literal["https://api.deepseek.com"] = DEEPSEEK_BASE_URL
    deepseek_model: Literal["deepseek-v4-flash"] = DEFAULT_DEEPSEEK_MODEL
    deepseek_max_output_tokens: int = Field(default=4096, ge=256, le=16_384)
    deepseek_timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    deepseek_max_network_retries: int = Field(default=2, ge=0, le=5)
    deepseek_retry_base_delay_seconds: float = Field(default=0.25, ge=0, le=5)
    paritok_api_key: SecretStr | None = None
    paritok_proxy_base_url: Literal["http://127.0.0.1:8080/v1"] = PARITOK_PROXY_BASE_URL
    paritok_health_url: Literal["http://127.0.0.1:8080/health"] = PARITOK_HEALTH_URL
    paritok_stats_url: Literal["http://127.0.0.1:8080/stats"] = PARITOK_STATS_URL
    paritok_gpu_status_url: Literal["https://www.paritok.com/api/test"] = PARITOK_GPU_STATUS_URL
    paritok_upstream_chat_completions_url: Literal["https://api.deepseek.com/chat/completions"] = (
        PARITOK_UPSTREAM_CHAT_COMPLETIONS_URL
    )
    paritok_health_timeout_seconds: float = Field(default=3.0, gt=0, le=30)
    paritok_stats_timeout_seconds: float = Field(default=3.0, gt=0, le=30)
    paritok_gpu_status_timeout_seconds: float = Field(default=10.0, gt=0, le=30)
    paritok_chunk_target_tokens: int = Field(default=40_000, ge=512, le=49_000)
    analysis_concurrency: int = Field(default=1, ge=1, le=1)
    deepseek_input_cache_miss_usd_per_m: Decimal = Field(
        default=Decimal("0.14"),
        ge=0,
    )
    deepseek_input_cache_hit_usd_per_m: Decimal = Field(
        default=Decimal("0.0028"),
        ge=0,
    )
    deepseek_output_usd_per_m: Decimal = Field(default=Decimal("0.28"), ge=0)
    pricing_snapshot_date: date = date(2026, 7, 25)

    @staticmethod
    def _secret_is_present(secret: SecretStr | None) -> bool:
        return bool(secret and secret.get_secret_value().strip())

    @property
    def deepseek_api_key_configured(self) -> bool:
        return self._secret_is_present(self.deepseek_api_key)

    @property
    def paritok_api_key_configured(self) -> bool:
        return self._secret_is_present(self.paritok_api_key)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""

    return Settings()
