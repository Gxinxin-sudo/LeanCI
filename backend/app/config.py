"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Validated application configuration.

    Secrets remain wrapped as ``SecretStr`` and are never returned from public
    endpoints. Phase one has no outbound AI or Paritok clients.
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
    deepseek_api_key: SecretStr | None = None
    paritok_api_key: SecretStr | None = None

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
