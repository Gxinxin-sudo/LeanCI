from types import SimpleNamespace
from typing import Any

import pytest

from app.benchmark import BenchmarkRunner, build_artifact, score_analysis
from app.benchmark_models import BenchmarkGroundTruth
from app.config import Settings
from app.models import DiagnosticAnalysis, ProviderResult, ProviderUsage
from app.paritok import ParitokStatsSnapshot
from app.samples import load_ground_truth


def valid_analysis() -> DiagnosticAnalysis:
    return DiagnosticAnalysis(
        summary="The TypeScript build stops at configuration loading.",
        root_cause=("DEPLOY_REGION is undefined while AppConfig requires a string value."),
        confidence=0.97,
        evidence=[
            {
                "source": "ci.log",
                "line_start": 10,
                "line_end": 10,
                "excerpt": "error TS2322: Type 'string | undefined'",
                "explanation": "TS2322 identifies the invalid assignment.",
            },
            {
                "source": "src/config.ts",
                "line_start": 9,
                "line_end": 9,
                "excerpt": "region: process.env.DEPLOY_REGION",
                "explanation": "The optional environment lookup is returned directly.",
            },
        ],
        relevant_files=["src/config.ts", "src/deploy.ts", "tsconfig.json"],
        recommended_changes=[
            "Validate DEPLOY_REGION with a guard and throw a configuration error."
        ],
        patch="const region = process.env.DEPLOY_REGION",
        verification_commands=["npm run typecheck"],
        risks=["Deployment configuration may still be absent."],
        missing_information=[],
    )


def test_deterministic_score_uses_fixed_weights() -> None:
    truth = BenchmarkGroundTruth.model_validate(load_ground_truth("typescript-build"))

    score = score_analysis(valid_analysis(), truth, json_valid=True)

    assert score.quality_score == 100
    assert score.failed_checks == []


def test_failed_json_is_retained_as_a_zero_score() -> None:
    truth = BenchmarkGroundTruth.model_validate(load_ground_truth("typescript-build"))

    score = score_analysis(None, truth, json_valid=False)

    assert score.quality_score == 0
    assert score.json_valid is False
    assert score.failed_checks == [
        "root_cause",
        "evidence",
        "relevant_files",
        "fix_direction",
        "json_valid",
    ]


class FakeProvider:
    def __init__(self, provider: str) -> None:
        self.provider = provider
        self.message_hash_inputs: list[list[dict[str, Any]]] = []

    async def analyze_messages(
        self,
        messages: list[dict[str, Any]],
    ) -> ProviderResult:
        self.message_hash_inputs.append(messages)
        return ProviderResult(
            provider=self.provider,
            model="deepseek-v4-flash",
            analysis=valid_analysis(),
            usage=ProviderUsage(
                prompt_tokens=6_200 if self.provider == "direct_deepseek" else 320,
                completion_tokens=180,
                total_tokens=6_380 if self.provider == "direct_deepseek" else 500,
                prompt_cache_hit_tokens=0,
                prompt_cache_miss_tokens=(6_200 if self.provider == "direct_deepseek" else 320),
            ),
            request_attempts=1,
        )


class FakeParitokClient:
    def __init__(
        self,
        *,
        mutate_during_baseline: bool = False,
        zero_token_window: bool = False,
    ) -> None:
        self.mutate_during_baseline = mutate_during_baseline
        self.zero_token_window = zero_token_window
        self.stats_calls = 0

    async def health(self) -> SimpleNamespace:
        return SimpleNamespace(status="ok", version="1.2.7")

    async def hosted_gpu(self) -> SimpleNamespace:
        return SimpleNamespace(gpu_available=True)

    async def stats(self) -> ParitokStatsSnapshot:
        self.stats_calls += 1
        if self.stats_calls == 1:
            requests, original, compressed = 10, 50_000, 5_000
        elif self.stats_calls == 2 and self.mutate_during_baseline:
            requests, original, compressed = 11, 56_200, 5_320
        elif self.stats_calls == 2:
            requests, original, compressed = 10, 50_000, 5_000
        elif self.zero_token_window:
            requests, original, compressed = 11, 50_000, 5_000
        else:
            requests, original, compressed = 11, 56_200, 5_320
        return ParitokStatsSnapshot(
            total_requests=requests,
            input_tokens_original=original,
            input_tokens_compressed=compressed,
            compression_ratio=compressed / original,
            tokens_saved=original - compressed,
            tools_filtered=requests,
            estimated_cost_saved_usd="999",
        )


class FakeBenchmarkRunner(BenchmarkRunner):
    def __init__(
        self,
        settings: Settings,
        paritok_client: FakeParitokClient,
    ) -> None:
        super().__init__(settings, paritok_client)  # type: ignore[arg-type]
        self.direct = FakeProvider("direct_deepseek")
        self.paritok = FakeProvider("paritok_deepseek")

    def _providers(self) -> tuple[FakeProvider, FakeProvider]:  # type: ignore[override]
        return self.direct, self.paritok


@pytest.mark.anyio
async def test_runner_uses_identical_initial_messages_and_isolated_stats() -> None:
    settings = Settings(
        _env_file=None,
        deepseek_api_key="unit-test-only",
        paritok_api_key="unit-test-only",
    )
    runner = FakeBenchmarkRunner(settings, FakeParitokClient())

    rows = await runner.run_case("typescript-build")

    assert [row.mode for row in rows] == ["baseline_uncompressed", "paritok"]
    assert all(row.success for row in rows)
    assert rows[0].initial_messages_sha256 == rows[1].initial_messages_sha256
    assert runner.direct.message_hash_inputs == runner.paritok.message_hash_inputs
    assert rows[0].original_tokens is None
    assert rows[1].original_tokens == 6_200
    assert rows[1].compressed_tokens == 320
    assert rows[1].tokens_saved == 5_880
    assert rows[1].quality_score == 100


@pytest.mark.anyio
async def test_runner_keeps_both_failed_rows_when_baseline_stats_are_contaminated() -> None:
    settings = Settings(
        _env_file=None,
        deepseek_api_key="unit-test-only",
        paritok_api_key="unit-test-only",
    )
    runner = FakeBenchmarkRunner(
        settings,
        FakeParitokClient(mutate_during_baseline=True),
    )

    rows = await runner.run_case("typescript-build")

    assert rows[0].success is False
    assert "PARITOK_STATS_CHANGED_DURING_BASELINE" in (rows[0].error or "")
    assert rows[0].quality_score == 0
    assert rows[1].success is False
    assert rows[1].quality_score == 0


@pytest.mark.anyio
async def test_zero_token_stats_window_never_claims_one_hundred_percent_savings() -> None:
    settings = Settings(
        _env_file=None,
        deepseek_api_key="unit-test-only",
        paritok_api_key="unit-test-only",
    )
    runner = FakeBenchmarkRunner(
        settings,
        FakeParitokClient(zero_token_window=True),
    )

    rows = await runner.run_case("typescript-build")

    assert rows[1].success is False
    assert rows[1].original_tokens == 0
    assert rows[1].compressed_tokens == 0
    assert rows[1].tokens_saved == 0
    assert rows[1].compression_ratio is None
    assert "ORIGINAL_TOKEN_MINIMUM_NOT_MET" in (rows[1].error or "")


def test_partial_artifact_refuses_to_make_a_promotional_claim() -> None:
    settings = Settings(_env_file=None)
    artifact = build_artifact(settings, [])

    assert artifact.finalized is False
    assert artifact.summary.failed_rows == 0
    assert artifact.summary.supported_claim.startswith("Benchmark incomplete")
