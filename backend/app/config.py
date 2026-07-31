"""Application configuration loaded from environment variables."""

import re
from datetime import date
from decimal import Decimal
from functools import lru_cache
from ipaddress import ip_network
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models import MAX_LOG_CHARACTERS

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
        hide_input_in_errors=True,
    )

    app_name: str = "LeanCI API"
    environment: Literal["development", "production"] = "development"
    max_log_characters: int = Field(
        default=MAX_LOG_CHARACTERS,
        ge=1,
        le=MAX_LOG_CHARACTERS,
    )
    llm_provider: ApplicationProviderName = "paritok"
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: Literal["https://api.deepseek.com"] = DEEPSEEK_BASE_URL
    deepseek_model: Literal["deepseek-v4-flash"] = DEFAULT_DEEPSEEK_MODEL
    deepseek_max_output_tokens: int = Field(default=4096, ge=256, le=16_384)
    deepseek_timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    deepseek_max_network_retries: int = Field(default=2, ge=0, le=5)
    deepseek_retry_base_delay_seconds: float = Field(default=0.25, ge=0, le=5)
    analysis_timeout_seconds: float = Field(default=110.0, gt=0, le=115)
    save_invalid_response_debug: bool = False
    debug_response_dir: Path = Path("runtime/debug_responses")
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
    paritok_chunk_target_tokens: int = Field(default=12_000, ge=512, le=49_000)
    analysis_concurrency: int = Field(default=1, ge=1, le=1)
    api_rate_limit_requests: int = Field(default=120, ge=10, le=10_000)
    analyze_rate_limit_requests: int = Field(default=5, ge=1, le=100)
    rate_limit_window_seconds: int = Field(default=60, ge=10, le=3_600)
    rate_limit_max_buckets: int = Field(default=4_096, ge=128, le=100_000)
    cors_allowed_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    # Production analysis authentication is delegated to a TLS/OIDC gateway.  The
    # gateway must remove client-supplied copies of these headers and add its own.
    trusted_proxy_cidrs: str = ""
    proxy_auth_shared_secret: SecretStr | None = None
    proxy_auth_header: str = "x-leanci-proxy-auth"
    proxy_principal_header: str = "x-leanci-principal"
    data_retention_hours: int = Field(default=24, ge=1, le=720)
    distributed_rate_limit_required: bool = False
    daily_analysis_request_budget: int = Field(default=0, ge=0, le=1_000_000)
    deepseek_input_cache_miss_usd_per_m: Decimal = Field(
        default=Decimal("0.14"),
        ge=0,
    )
    deepseek_input_cache_hit_usd_per_m: Decimal = Field(
        default=Decimal("0.0028"),
        ge=0,
    )
    deepseek_output_usd_per_m: Decimal = Field(default=Decimal("0.28"), ge=0)
    pricing_snapshot_date: date = date(2026, 7, 31)

    @staticmethod
    def _secret_is_present(secret: SecretStr | None) -> bool:
        return bool(secret and secret.get_secret_value().strip())

    @property
    def deepseek_api_key_configured(self) -> bool:
        return self._secret_is_present(self.deepseek_api_key)

    @property
    def paritok_api_key_configured(self) -> bool:
        return self._secret_is_present(self.paritok_api_key)

    @property
    def proxy_auth_configured(self) -> bool:
        return self._secret_is_present(self.proxy_auth_shared_secret)

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_allowed_origins(cls, value: str) -> str:
        origins: list[str] = []
        for raw_origin in value.split(","):
            origin = raw_origin.strip().rstrip("/")
            if not origin or origin == "*":
                raise ValueError("CORS origins must be explicit http(s) origins")
            parsed = urlsplit(origin)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError("CORS origin contains an invalid port") from exc
            if (
                parsed.scheme not in {"http", "https"}
                or parsed.hostname is None
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or (port is not None and not 1 <= port <= 65_535)
            ):
                raise ValueError("CORS origins must not contain credentials, paths, or wildcards")
            if origin not in origins:
                origins.append(origin)
        return ",".join(origins)

    @field_validator("proxy_auth_header", "proxy_principal_header")
    @classmethod
    def validate_internal_header_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9-]{1,64}", normalized):
            raise ValueError("internal authentication header names must be ASCII HTTP token names")
        return normalized

    @field_validator("debug_response_dir")
    @classmethod
    def validate_debug_response_dir(cls, value: Path) -> Path:
        runtime_root = (PROJECT_ROOT / "runtime").resolve()
        candidate = value.resolve() if value.is_absolute() else (PROJECT_ROOT / value).resolve()
        if not candidate.is_relative_to(runtime_root):
            raise ValueError("debug response directory must stay inside runtime")
        return candidate

    @property
    def cors_origins(self) -> list[str]:
        return self.cors_allowed_origins.split(",")

    @property
    def trusted_proxy_networks(self) -> tuple[object, ...]:
        return tuple(
            ip_network(value.strip(), strict=False)
            for value in self.trusted_proxy_cidrs.split(",")
            if value.strip()
        )

    @model_validator(mode="after")
    def validate_production_boundary(self) -> "Settings":
        if self.environment != "production":
            return self
        if self.save_invalid_response_debug:
            raise ValueError("production cannot save invalid response diagnostics")
        if any(urlsplit(origin).scheme != "https" for origin in self.cors_origins):
            raise ValueError("production CORS origins must use HTTPS")
        if not self.trusted_proxy_networks:
            raise ValueError("production requires TRUSTED_PROXY_CIDRS")
        if not self.proxy_auth_configured:
            raise ValueError("production requires PROXY_AUTH_SHARED_SECRET")
        if not self.distributed_rate_limit_required:
            raise ValueError("production requires DISTRIBUTED_RATE_LIMIT_REQUIRED=true")
        if self.daily_analysis_request_budget < 1:
            raise ValueError("production requires DAILY_ANALYSIS_REQUEST_BUDGET >= 1")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""

    return Settings()
