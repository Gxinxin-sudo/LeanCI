"""LLM providers with strict validation and bounded retry behavior."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Protocol, cast

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI
from pydantic import SecretStr, ValidationError

from app.config import DEFAULT_DEEPSEEK_MODEL, Settings
from app.llm.debug_records import InvalidAttempt, save_invalid_response_record
from app.llm.prompts import (
    PromptMessage,
    build_analysis_messages,
    build_paritok_analysis_messages,
    build_repair_messages,
)
from app.mock_analysis import build_mock_analysis
from app.models import DiagnosticAnalysis, ProviderResult, ProviderUsage

RESPONSE_FORMAT = {"type": "json_object"}
THINKING_DISABLED = {"thinking": {"type": "disabled"}}


class LLMProviderError(RuntimeError):
    """Safe provider failure suitable for a CLI or public error mapper."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message


class DirectUseCase(StrEnum):
    """The only contexts in which direct DeepSeek access is allowed."""

    CONNECTION_TEST = "connection_test"
    BENCHMARK_BASELINE = "benchmark_baseline"
    TROUBLESHOOTING = "troubleshooting"


class CompletionCreator(Protocol):
    async def create(self, **kwargs: Any) -> Any:
        """Create one OpenAI-compatible chat completion."""


class CompletionClient(Protocol):
    chat: Any


class LLMProvider(ABC):
    """Unified interface implemented by mock, direct, and Paritok providers."""

    @abstractmethod
    async def analyze(self, untrusted_context: str) -> ProviderResult:
        """Analyze untrusted CI evidence and return a validated result."""


class MockProvider(LLMProvider):
    """Deterministic provider for application development and unit tests."""

    async def analyze(self, untrusted_context: str) -> ProviderResult:
        del untrusted_context
        mock = build_mock_analysis()
        analysis = DiagnosticAnalysis.model_validate(
            mock.model_dump(exclude={"compression_stats", "analysis_time_ms"})
        )
        return ProviderResult(
            provider="mock",
            model="mock",
            analysis=analysis,
            usage=None,
            request_attempts=0,
        )


class _OpenAICompatibleDeepSeekProvider(LLMProvider):
    provider_name: Literal["direct_deepseek", "paritok_deepseek"]
    expose_upstream_usage = False
    connection_error_code = "DEEPSEEK_CONNECTION_FAILED"
    connection_error_message = (
        "Could not connect to DeepSeek. Check the base URL, DNS, and firewall."
    )

    def __init__(
        self,
        *,
        api_key: SecretStr,
        base_url: str,
        model: str = DEFAULT_DEEPSEEK_MODEL,
        max_tokens: int = 4096,
        timeout_seconds: float = 60.0,
        max_network_retries: int = 2,
        retry_base_delay_seconds: float = 0.25,
        chunk_target_tokens: int = 40_000,
        debug_response_dir: Path | None = None,
        client: CompletionClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if model != DEFAULT_DEEPSEEK_MODEL:
            raise LLMProviderError(
                code="MODEL_NOT_ALLOWED",
                message="LeanCI only allows the configured deepseek-v4-flash model.",
            )
        if not api_key.get_secret_value().strip():
            raise LLMProviderError(
                code="DEEPSEEK_API_KEY_MISSING",
                message=("DEEPSEEK_API_KEY is not configured. Add it only to the local .env file."),
            )

        self.model = model
        self.max_tokens = max_tokens
        self.max_network_retries = max_network_retries
        self.retry_base_delay_seconds = retry_base_delay_seconds
        self.chunk_target_tokens = chunk_target_tokens
        self.debug_response_dir = debug_response_dir
        self._sleep = sleep
        self._client = client or cast(
            CompletionClient,
            AsyncOpenAI(
                api_key=api_key.get_secret_value(),
                base_url=base_url,
                timeout=timeout_seconds,
                max_retries=0,
            ),
        )

    async def analyze(self, untrusted_context: str) -> ProviderResult:
        return await self.analyze_messages(self._build_analysis_messages(untrusted_context))

    async def analyze_messages(self, messages: list[PromptMessage]) -> ProviderResult:
        """Analyze an already-built fixed message list.

        This is used only by the isolated benchmark so both routes receive the
        byte-identical initial message payload. Application analysis continues
        to call ``analyze`` and select its own fixed Paritok message builder.
        """

        first_completion, request_attempts = await self._request(messages)
        first_content = self._extract_content(first_completion)
        repair_completion: Any | None = None

        try:
            analysis = self._validate_analysis(first_completion, first_content)
        except ValueError as exc:
            self._save_invalid_response(
                attempt="initial",
                reason=str(exc),
                completion=first_completion,
                content=first_content,
            )
            repair_completion, repair_attempts = await self._request(
                build_repair_messages(first_content)
            )
            request_attempts += repair_attempts
            repair_content = self._extract_content(repair_completion)
            try:
                analysis = self._validate_analysis(repair_completion, repair_content)
            except ValueError as exc:
                self._save_invalid_response(
                    attempt="repair",
                    reason=str(exc),
                    completion=repair_completion,
                    content=repair_content,
                )
                raise LLMProviderError(
                    code="LLM_OUTPUT_INVALID",
                    message=(
                        "DeepSeek returned an invalid structured response after one repair attempt."
                    ),
                ) from exc

        usage = self._extract_usage(first_completion) if self.expose_upstream_usage else None
        if usage is not None and repair_completion is not None:
            usage = self._combine_usage(usage, self._extract_usage(repair_completion))

        return ProviderResult(
            provider=self.provider_name,
            model=self.model,
            analysis=analysis,
            usage=usage,
            request_attempts=request_attempts,
        )

    def _save_invalid_response(
        self,
        *,
        attempt: InvalidAttempt,
        reason: str,
        completion: Any,
        content: str,
    ) -> None:
        if self.debug_response_dir is None:
            return
        save_invalid_response_record(
            self.debug_response_dir,
            provider=self.provider_name,
            model=self.model,
            attempt=attempt,
            reason=reason,
            completion=completion,
            content=content,
        )

    def _build_analysis_messages(self, untrusted_context: str) -> list[PromptMessage]:
        return build_analysis_messages(untrusted_context)

    async def _request(self, messages: list[PromptMessage]) -> tuple[Any, int]:
        creator = cast(CompletionCreator, self._client.chat.completions)

        for attempt in range(self.max_network_retries + 1):
            try:
                return (
                    await creator.create(
                        model=self.model,
                        messages=messages,
                        response_format=RESPONSE_FORMAT,
                        extra_body=THINKING_DISABLED,
                        max_tokens=self.max_tokens,
                        stream=False,
                    ),
                    attempt + 1,
                )
            except APITimeoutError as exc:
                if attempt < self.max_network_retries:
                    await self._wait_before_retry(attempt)
                    continue
                raise LLMProviderError(
                    code="DEEPSEEK_TIMEOUT",
                    message=("The DeepSeek request timed out. Check the network and try again."),
                ) from exc
            except APIConnectionError as exc:
                if attempt < self.max_network_retries:
                    await self._wait_before_retry(attempt)
                    continue
                raise LLMProviderError(
                    code=self.connection_error_code,
                    message=self.connection_error_message,
                ) from exc
            except APIStatusError as exc:
                status_code = exc.status_code
                retryable = status_code == 429 or status_code >= 500
                if retryable and attempt < self.max_network_retries:
                    await self._wait_before_retry(attempt)
                    continue
                raise self._map_status_error(status_code) from exc

        raise AssertionError("bounded retry loop exited unexpectedly")

    async def _wait_before_retry(self, attempt: int) -> None:
        delay = self.retry_base_delay_seconds * (2**attempt)
        await self._sleep(delay)

    @staticmethod
    def _map_status_error(status_code: int) -> LLMProviderError:
        if status_code == 401:
            return LLMProviderError(
                code="DEEPSEEK_AUTHENTICATION_FAILED",
                message=(
                    "DeepSeek authentication failed (401). Check DEEPSEEK_API_KEY in "
                    "the local .env file."
                ),
            )
        if status_code == 402:
            return LLMProviderError(
                code="DEEPSEEK_INSUFFICIENT_BALANCE",
                message=(
                    "The DeepSeek account has insufficient balance (402). Check the "
                    "platform billing page."
                ),
            )
        if status_code == 429:
            return LLMProviderError(
                code="DEEPSEEK_RATE_LIMITED",
                message=("DeepSeek rate-limited the request (429). Wait briefly before retrying."),
            )
        if status_code >= 500:
            return LLMProviderError(
                code="DEEPSEEK_SERVER_ERROR",
                message=("DeepSeek is temporarily unavailable (server error). Try again later."),
            )
        return LLMProviderError(
            code="DEEPSEEK_REQUEST_REJECTED",
            message=(
                "DeepSeek rejected the request. Check the fixed model and endpoint configuration."
            ),
        )

    @staticmethod
    def _extract_content(completion: Any) -> str:
        choices = getattr(completion, "choices", None)
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        return content if isinstance(content, str) else ""

    @staticmethod
    def _validate_analysis(completion: Any, content: str) -> DiagnosticAnalysis:
        choices = getattr(completion, "choices", None)
        finish_reason = getattr(choices[0], "finish_reason", None) if choices else None
        if finish_reason == "length" or not content.strip():
            raise ValueError("empty or truncated model content")
        try:
            return DiagnosticAnalysis.model_validate_json(content)
        except ValidationError as exc:
            raise ValueError("model content failed strict validation") from exc

    @staticmethod
    def _extract_usage(completion: Any) -> ProviderUsage:
        usage = getattr(completion, "usage", None)
        if usage is None:
            raise LLMProviderError(
                code="DEEPSEEK_USAGE_MISSING",
                message="DeepSeek returned no usage data for the connection test.",
            )

        if isinstance(usage, Mapping):
            usage_data = dict(usage)
        elif hasattr(usage, "model_dump"):
            usage_data = usage.model_dump()
        else:
            usage_data = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
                "prompt_cache_hit_tokens": getattr(usage, "prompt_cache_hit_tokens", None),
                "prompt_cache_miss_tokens": getattr(usage, "prompt_cache_miss_tokens", None),
            }

        try:
            return ProviderUsage.model_validate(
                {
                    "prompt_tokens": usage_data.get("prompt_tokens"),
                    "completion_tokens": usage_data.get("completion_tokens"),
                    "total_tokens": usage_data.get("total_tokens"),
                    "prompt_cache_hit_tokens": usage_data.get("prompt_cache_hit_tokens"),
                    "prompt_cache_miss_tokens": usage_data.get("prompt_cache_miss_tokens"),
                }
            )
        except ValidationError as exc:
            raise LLMProviderError(
                code="DEEPSEEK_USAGE_INVALID",
                message="DeepSeek returned invalid usage data for the connection test.",
            ) from exc

    @staticmethod
    def _combine_usage(left: ProviderUsage, right: ProviderUsage) -> ProviderUsage:
        def add_optional(left_value: int | None, right_value: int | None) -> int | None:
            if left_value is None or right_value is None:
                return None
            return left_value + right_value

        return ProviderUsage(
            prompt_tokens=left.prompt_tokens + right.prompt_tokens,
            completion_tokens=left.completion_tokens + right.completion_tokens,
            total_tokens=left.total_tokens + right.total_tokens,
            prompt_cache_hit_tokens=add_optional(
                left.prompt_cache_hit_tokens,
                right.prompt_cache_hit_tokens,
            ),
            prompt_cache_miss_tokens=add_optional(
                left.prompt_cache_miss_tokens,
                right.prompt_cache_miss_tokens,
            ),
        )


class DirectDeepSeekProvider(_OpenAICompatibleDeepSeekProvider):
    """Direct access restricted to explicit non-production uses."""

    provider_name = "direct_deepseek"
    expose_upstream_usage = True

    def __init__(self, *, use_case: DirectUseCase, **kwargs: Any) -> None:
        if not isinstance(use_case, DirectUseCase):
            raise LLMProviderError(
                code="DIRECT_USE_CASE_NOT_ALLOWED",
                message=(
                    "Direct DeepSeek access is limited to connection tests, benchmark "
                    "baseline runs, and troubleshooting."
                ),
            )
        self.use_case = use_case
        super().__init__(**kwargs)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        use_case: DirectUseCase,
    ) -> "DirectDeepSeekProvider":
        return cls(
            use_case=use_case,
            api_key=_require_deepseek_key(settings),
            base_url=str(settings.deepseek_base_url),
            model=settings.deepseek_model,
            max_tokens=settings.deepseek_max_output_tokens,
            timeout_seconds=settings.deepseek_timeout_seconds,
            max_network_retries=settings.deepseek_max_network_retries,
            retry_base_delay_seconds=settings.deepseek_retry_base_delay_seconds,
            debug_response_dir=(
                settings.debug_response_dir if settings.save_invalid_response_debug else None
            ),
        )


class ParitokDeepSeekProvider(_OpenAICompatibleDeepSeekProvider):
    """The only provider allowed for formal application analysis."""

    provider_name = "paritok_deepseek"
    connection_error_code = "PARITOK_PROXY_UNAVAILABLE"
    connection_error_message = (
        "The local Paritok Proxy became unavailable during analysis. "
        "Keep the proxy terminal open and try again."
    )

    def _build_analysis_messages(self, untrusted_context: str) -> list[PromptMessage]:
        return build_paritok_analysis_messages(
            untrusted_context,
            target_tokens=self.chunk_target_tokens,
            model=self.model,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "ParitokDeepSeekProvider":
        return cls(
            api_key=_require_deepseek_key(settings),
            base_url=str(settings.paritok_proxy_base_url),
            model=settings.deepseek_model,
            max_tokens=settings.deepseek_max_output_tokens,
            timeout_seconds=settings.deepseek_timeout_seconds,
            max_network_retries=settings.deepseek_max_network_retries,
            retry_base_delay_seconds=settings.deepseek_retry_base_delay_seconds,
            chunk_target_tokens=settings.paritok_chunk_target_tokens,
            debug_response_dir=(
                settings.debug_response_dir if settings.save_invalid_response_debug else None
            ),
        )


def _require_deepseek_key(settings: Settings) -> SecretStr:
    if not settings.deepseek_api_key_configured or settings.deepseek_api_key is None:
        raise LLMProviderError(
            code="DEEPSEEK_API_KEY_MISSING",
            message="DEEPSEEK_API_KEY is not configured. Add it only to the local .env file.",
        )
    return settings.deepseek_api_key


def build_application_provider(settings: Settings) -> LLMProvider:
    """Build an application provider without any direct-DeepSeek fallback."""

    if settings.llm_provider != "paritok":
        raise LLMProviderError(
            code="FORMAL_ANALYSIS_REQUIRES_PARITOK",
            message=(
                "Formal analysis is disabled until LLM_PROVIDER=paritok. "
                "Mock and direct modes cannot serve /api/analyze."
            ),
        )
    return ParitokDeepSeekProvider.from_settings(settings)
