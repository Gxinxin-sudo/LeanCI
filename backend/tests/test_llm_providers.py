import json
from collections.abc import Awaitable, Callable
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError
from pydantic import SecretStr

from app.config import Settings
from app.llm.providers import (
    RESPONSE_FORMAT,
    THINKING_DISABLED,
    DirectDeepSeekProvider,
    DirectUseCase,
    LLMProviderError,
    MockProvider,
    ParitokDeepSeekProvider,
    build_application_provider,
)

VALID_ANALYSIS = {
    "summary": "Type checking failed.",
    "root_cause": "A required string received an undefined value.",
    "confidence": 0.95,
    "evidence": [
        {
            "source": "ci.log",
            "line_start": 8,
            "line_end": 8,
            "excerpt": "error TS2345",
            "explanation": "The compiler identifies the type mismatch.",
        }
    ],
    "relevant_files": ["src/config.ts"],
    "recommended_changes": ["Validate the environment value."],
    "patch": "",
    "verification_commands": ["npm run typecheck"],
    "risks": ["Deployment configuration may be incomplete."],
    "missing_information": ["The deployment environment was not supplied."],
}


def make_completion(
    content: str,
    *,
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    finish_reason: str = "stop",
) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ],
        usage={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "prompt_cache_hit_tokens": 2,
            "prompt_cache_miss_tokens": prompt_tokens - 2,
        },
    )


class FakeCompletions:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses: list[Any]) -> None:
        self.completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


async def no_sleep(_delay: float) -> None:
    return None


def make_direct_provider(
    responses: list[Any],
    *,
    max_network_retries: int = 2,
    sleep: Callable[[float], Awaitable[None]] = no_sleep,
    debug_response_dir: Path | None = None,
) -> tuple[DirectDeepSeekProvider, FakeClient]:
    client = FakeClient(responses)
    provider = DirectDeepSeekProvider(
        use_case=DirectUseCase.CONNECTION_TEST,
        api_key=SecretStr("unit-test-only"),
        base_url="https://api.deepseek.com",
        max_network_retries=max_network_retries,
        retry_base_delay_seconds=0,
        debug_response_dir=debug_response_dir,
        client=client,
        sleep=sleep,
    )
    return provider, client


@pytest.mark.anyio
async def test_mock_provider_returns_strict_result_without_fabricated_usage() -> None:
    result = await MockProvider().analyze("untrusted log")

    assert result.provider == "mock"
    assert result.usage is None
    assert result.analysis.root_cause


@pytest.mark.anyio
async def test_direct_provider_sends_fixed_deepseek_parameters() -> None:
    provider, client = make_direct_provider([make_completion(json.dumps(VALID_ANALYSIS))])

    result = await provider.analyze("UNTRUSTED DATA")

    assert result.provider == "direct_deepseek"
    assert result.model == "deepseek-v4-flash"
    assert result.usage is not None
    assert result.usage.total_tokens == 30
    assert result.request_attempts == 1
    assert len(client.completions.calls) == 1
    call = client.completions.calls[0]
    assert call["model"] == "deepseek-v4-flash"
    assert call["response_format"] == RESPONSE_FORMAT
    assert call["extra_body"] == THINKING_DISABLED
    assert call["max_tokens"] == 4096
    assert call["stream"] is False
    assert "json" in call["messages"][0]["content"].lower()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_content",
    [
        "",
        "{not-json",
        json.dumps({key: value for key, value in VALID_ANALYSIS.items() if key != "summary"}),
    ],
    ids=["empty", "invalid-json", "missing-field"],
)
async def test_invalid_output_gets_exactly_one_repair_attempt(
    invalid_content: str,
) -> None:
    provider, client = make_direct_provider(
        [
            make_completion(invalid_content, prompt_tokens=5, completion_tokens=1),
            make_completion(
                json.dumps(VALID_ANALYSIS),
                prompt_tokens=7,
                completion_tokens=10,
            ),
        ]
    )

    result = await provider.analyze("untrusted")

    assert len(client.completions.calls) == 2
    assert result.usage is not None
    assert result.usage.prompt_tokens == 12
    assert result.usage.completion_tokens == 11
    assert result.usage.total_tokens == 23
    assert result.request_attempts == 2
    repair_prompt = client.completions.calls[1]["messages"][1]["content"]
    assert "<UNTRUSTED_PREVIOUS_OUTPUT>" in repair_prompt


@pytest.mark.anyio
async def test_invalid_output_debug_record_never_saves_model_content(
    tmp_path: Path,
) -> None:
    invalid_content = "private-token-value {not-json"
    provider, _client = make_direct_provider(
        [
            make_completion(invalid_content),
            make_completion(json.dumps(VALID_ANALYSIS)),
        ],
        debug_response_dir=tmp_path,
    )

    await provider.analyze("private uploaded evidence")

    records = list(tmp_path.glob("invalid-*.json"))
    assert len(records) == 1
    serialized = records[0].read_text(encoding="utf-8")
    payload = json.loads(serialized)
    assert invalid_content not in serialized
    assert "private uploaded evidence" not in serialized
    assert payload["content_saved"] is False
    assert payload["attempt"] == "initial"
    assert payload["reason"] == "model content failed strict validation"
    assert payload["content_sha256"] == sha256(invalid_content.encode()).hexdigest()
    assert payload["content_characters"] == len(invalid_content)


@pytest.mark.anyio
async def test_second_invalid_output_stops_without_a_third_attempt() -> None:
    provider, client = make_direct_provider(
        [make_completion(""), make_completion("{still-invalid")]
    )

    with pytest.raises(LLMProviderError) as captured:
        await provider.analyze("untrusted")

    assert captured.value.code == "LLM_OUTPUT_INVALID"
    assert len(client.completions.calls) == 2


def make_status_error(status_code: int) -> APIStatusError:
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    response = httpx.Response(status_code, request=request)
    if status_code == 401:
        return AuthenticationError("test-only", response=response, body=None)
    return APIStatusError("test-only", response=response, body=None)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status_code", "expected_code", "expected_calls"),
    [
        (401, "DEEPSEEK_AUTHENTICATION_FAILED", 1),
        (402, "DEEPSEEK_INSUFFICIENT_BALANCE", 1),
        (429, "DEEPSEEK_RATE_LIMITED", 3),
        (500, "DEEPSEEK_SERVER_ERROR", 3),
    ],
)
async def test_status_errors_have_friendly_messages_and_bounded_retries(
    status_code: int,
    expected_code: str,
    expected_calls: int,
) -> None:
    errors = [make_status_error(status_code) for _ in range(expected_calls)]
    provider, client = make_direct_provider(errors)

    with pytest.raises(LLMProviderError) as captured:
        await provider.analyze("untrusted")

    assert captured.value.code == expected_code
    assert str(status_code) in captured.value.public_message or status_code >= 500
    assert len(client.completions.calls) == expected_calls


@pytest.mark.anyio
async def test_timeout_retries_are_bounded_and_use_safe_error() -> None:
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    provider, client = make_direct_provider([APITimeoutError(request) for _ in range(3)])

    with pytest.raises(LLMProviderError) as captured:
        await provider.analyze("untrusted")

    assert captured.value.code == "DEEPSEEK_TIMEOUT"
    assert "timed out" in captured.value.public_message
    assert len(client.completions.calls) == 3


@pytest.mark.anyio
async def test_retryable_failure_can_recover_within_the_limit() -> None:
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    provider, client = make_direct_provider(
        [
            APITimeoutError(request),
            make_completion(json.dumps(VALID_ANALYSIS)),
        ]
    )

    result = await provider.analyze("untrusted")

    assert result.analysis.summary == VALID_ANALYSIS["summary"]
    assert result.request_attempts == 2
    assert len(client.completions.calls) == 2


@pytest.mark.anyio
async def test_paritok_provider_does_not_expose_upstream_usage_as_formal_metrics() -> None:
    client = FakeClient([make_completion(json.dumps(VALID_ANALYSIS))])
    provider = ParitokDeepSeekProvider(
        api_key=SecretStr("unit-test-only"),
        base_url="http://127.0.0.1:8080/v1",
        client=client,
    )

    result = await provider.analyze("untrusted")

    assert result.provider == "paritok_deepseek"
    assert result.usage is None
    assert result.request_attempts == 1
    messages = client.completions.calls[0]["messages"]
    assert any(message["role"] == "tool" for message in messages)
    assert "UNTRUSTED DATA" in next(
        message["content"] for message in messages if message["role"] == "tool"
    )


def test_application_provider_factory_never_selects_direct_deepseek() -> None:
    with pytest.raises(LLMProviderError) as captured:
        build_application_provider(Settings(_env_file=None, llm_provider="mock"))
    assert captured.value.code == "FORMAL_ANALYSIS_REQUIRES_PARITOK"

    settings = Settings(
        _env_file=None,
        llm_provider="paritok",
        deepseek_api_key="unit-test-only",
    )
    paritok_provider = build_application_provider(settings)
    assert isinstance(paritok_provider, ParitokDeepSeekProvider)


def test_application_provider_does_not_fallback_when_paritok_lacks_key() -> None:
    settings = Settings(_env_file=None, llm_provider="paritok")

    with pytest.raises(LLMProviderError) as captured:
        build_application_provider(settings)

    assert captured.value.code == "DEEPSEEK_API_KEY_MISSING"


@pytest.mark.anyio
async def test_paritok_connection_failure_is_not_mislabeled_as_direct_deepseek() -> None:
    request = httpx.Request("POST", "http://127.0.0.1:8080/v1/chat/completions")
    client = FakeClient([APIConnectionError(request=request)])
    provider = ParitokDeepSeekProvider(
        api_key=SecretStr("unit-test-only"),
        base_url="http://127.0.0.1:8080/v1",
        max_network_retries=0,
        client=client,
    )

    with pytest.raises(LLMProviderError) as captured:
        await provider.analyze("untrusted")

    assert captured.value.code == "PARITOK_PROXY_UNAVAILABLE"


def test_direct_provider_rejects_an_unapproved_runtime_use_case() -> None:
    with pytest.raises(LLMProviderError) as captured:
        DirectDeepSeekProvider(
            use_case="production",  # type: ignore[arg-type]
            api_key=SecretStr("unit-test-only"),
            base_url="https://api.deepseek.com",
        )

    assert captured.value.code == "DIRECT_USE_CASE_NOT_ALLOWED"
