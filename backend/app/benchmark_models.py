"""Strict contracts for fixed, auditable LeanCI benchmark artifacts."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import DiagnosticAnalysis

BenchmarkMode = Literal["baseline_uncompressed", "paritok"]
BenchmarkStatus = Literal[
    "baseline_completed",
    "compressed",
    "skipped_low_yield",
    "unavailable",
    "upstream_failed",
]
CompressionSkipReason = Literal["below_refusal_threshold"]
GroundTruthText = Annotated[str, Field(min_length=1, max_length=8_000)]
GroundTruthTerm = Annotated[str, Field(min_length=1, max_length=300)]


class BenchmarkStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ExpectedEvidence(BenchmarkStrictModel):
    source: str = Field(min_length=1, max_length=240)
    term_groups: list[list[GroundTruthTerm]] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_groups(self) -> "ExpectedEvidence":
        if any(not group for group in self.term_groups):
            raise ValueError("evidence term groups must not be empty")
        return self


class BenchmarkGroundTruth(BenchmarkStrictModel):
    schema_version: Literal[2]
    case_id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=80)
    expected_root_cause: GroundTruthText
    root_cause_term_groups: list[list[GroundTruthTerm]] = Field(min_length=1, max_length=12)
    expected_evidence: list[ExpectedEvidence] = Field(min_length=1, max_length=20)
    expected_relevant_files: list[str] = Field(min_length=1, max_length=20)
    expected_fix_direction: list[GroundTruthText] = Field(min_length=1, max_length=20)
    fix_direction_term_groups: list[list[GroundTruthTerm]] = Field(min_length=1, max_length=12)
    minimum_original_tokens: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_groups(self) -> "BenchmarkGroundTruth":
        groups = [*self.root_cause_term_groups, *self.fix_direction_term_groups]
        if any(not group for group in groups):
            raise ValueError("ground-truth term groups must not be empty")
        return self


class DeterministicScore(BenchmarkStrictModel):
    root_cause_correct: bool
    evidence_correct: bool
    relevant_files_correct: bool
    fix_direction_correct: bool
    json_valid: bool
    quality_score: int = Field(ge=0, le=100)
    failed_checks: list[
        Literal[
            "root_cause",
            "evidence",
            "relevant_files",
            "fix_direction",
            "json_valid",
        ]
    ] = Field(max_length=5)

    @model_validator(mode="after")
    def validate_total(self) -> "DeterministicScore":
        expected = (
            (40 if self.root_cause_correct else 0)
            + (20 if self.evidence_correct else 0)
            + (15 if self.relevant_files_correct else 0)
            + (15 if self.fix_direction_correct else 0)
            + (10 if self.json_valid else 0)
        )
        if self.quality_score != expected:
            raise ValueError("quality_score does not match the fixed rubric")
        return self


class HumanReview(BenchmarkStrictModel):
    status: Literal["pending", "confirmed", "overridden"] = "pending"
    reviewer: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=4_000)


class BenchmarkCostEstimate(BenchmarkStrictModel):
    input_if_all_cache_hit_usd: float | None = Field(default=None, ge=0)
    input_if_all_cache_miss_usd: float | None = Field(default=None, ge=0)
    input_from_reported_cache_split_usd: float | None = Field(default=None, ge=0)
    output_usd: float | None = Field(default=None, ge=0)
    saved_input_if_cache_hit_usd: float | None = Field(default=None, ge=0)
    saved_input_if_cache_miss_usd: float | None = Field(default=None, ge=0)
    disclaimer: Literal[
        "Configured estimate only; cache behavior varies and this is not an actual bill."
    ] = "Configured estimate only; cache behavior varies and this is not an actual bill."


class BenchmarkRow(BenchmarkStrictModel):
    case_id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=80)
    mode: BenchmarkMode
    status: BenchmarkStatus
    success: bool
    compression_skip_reason: CompressionSkipReason | None = None
    original_tokens: int | None = Field(default=None, ge=0)
    compressed_tokens: int | None = Field(default=None, ge=0)
    tokens_saved: int | None = Field(default=None, ge=0)
    compression_ratio: float | None = Field(default=None, ge=0, le=1)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    prompt_cache_hit_tokens: int | None = Field(default=None, ge=0)
    prompt_cache_miss_tokens: int | None = Field(default=None, ge=0)
    latency_ms: int = Field(ge=0, le=3_600_000)
    root_cause_correct: bool | None
    evidence_correct: bool | None
    relevant_files_correct: bool | None
    fix_direction_correct: bool | None
    json_valid: bool | None
    quality_score: int | None = Field(default=None, ge=0, le=100)
    error: str | None = Field(default=None, max_length=1_000)
    run_timestamp: datetime
    model: Literal["deepseek-v4-flash"]
    pricing_snapshot_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    initial_messages_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    json_schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    score: DeterministicScore | None
    human_review: HumanReview
    cost_estimate: BenchmarkCostEstimate
    analysis: DiagnosticAnalysis | None = None

    @model_validator(mode="after")
    def validate_row(self) -> "BenchmarkRow":
        mirrored = (
            self.root_cause_correct,
            self.evidence_correct,
            self.relevant_files_correct,
            self.fix_direction_correct,
            self.json_valid,
            self.quality_score,
        )
        has_analysis = self.analysis is not None
        if has_analysis:
            if not self.success or self.error is not None or self.score is None:
                raise ValueError("valid analysis rows require success, score, and no error")
            score_values = (
                self.score.root_cause_correct,
                self.score.evidence_correct,
                self.score.relevant_files_correct,
                self.score.fix_direction_correct,
                self.score.json_valid,
                self.score.quality_score,
            )
            if mirrored != score_values:
                raise ValueError("flat score columns must match the score object")
            if self.prompt_tokens is None or self.completion_tokens is None:
                raise ValueError("valid analyses require reported provider usage")
        else:
            if (
                self.success
                or self.score is not None
                or any(value is not None for value in mirrored)
            ):
                raise ValueError("rows without valid analysis must use null quality fields")

        if self.mode == "baseline_uncompressed":
            if self.status not in {
                "baseline_completed",
                "unavailable",
                "upstream_failed",
            }:
                raise ValueError("baseline rows cannot carry a Paritok compression status")
            if self.compression_skip_reason is not None:
                raise ValueError("baseline rows cannot carry a compression skip reason")
        elif self.status == "baseline_completed":
            raise ValueError("Paritok rows cannot be baseline_completed")

        if self.status == "baseline_completed" and not has_analysis:
            raise ValueError("baseline_completed requires a valid analysis")
        if self.status == "compressed" and (self.mode != "paritok" or not has_analysis):
            raise ValueError("compressed requires a valid Paritok analysis")
        if self.status == "skipped_low_yield":
            if self.mode != "paritok":
                raise ValueError("only Paritok rows can be skipped_low_yield")
            if self.compression_skip_reason != "below_refusal_threshold":
                raise ValueError("skipped_low_yield requires the verified reason")
            if self.error is not None:
                raise ValueError("normal low-yield skips are not failures")
        elif self.compression_skip_reason is not None:
            raise ValueError("only skipped_low_yield rows can store a skip reason")
        if self.status in {"unavailable", "upstream_failed"} and (
            has_analysis or self.error is None
        ):
            raise ValueError("unavailable/upstream_failed require a safe error and no analysis")

        if self.mode == "baseline_uncompressed" and any(
            value is not None
            for value in (
                self.original_tokens,
                self.compressed_tokens,
                self.tokens_saved,
                self.compression_ratio,
            )
        ):
            raise ValueError("baseline compression metrics must remain null without Paritok proof")
        token_metrics = (
            self.original_tokens,
            self.compressed_tokens,
            self.tokens_saved,
            self.compression_ratio,
        )
        if self.status in {"skipped_low_yield", "unavailable"} and any(
            value is not None for value in token_metrics
        ):
            raise ValueError("skipped/unavailable Token metrics are not applicable")
        if any(value is not None for value in token_metrics) and any(
            value is None for value in token_metrics
        ):
            raise ValueError("stats-delta Token metrics must be complete or all null")
        if self.status == "compressed" and any(value is None for value in token_metrics):
            raise ValueError("compressed rows require complete stats-delta metrics")
        if all(value is not None for value in token_metrics):
            assert self.original_tokens is not None
            assert self.compressed_tokens is not None
            assert self.tokens_saved is not None
            assert self.compression_ratio is not None
            if self.original_tokens == 0:
                raise ValueError("0->0 is a skip, not a compression Token metric")
            if self.tokens_saved != self.original_tokens - self.compressed_tokens:
                raise ValueError("stored Token metrics are internally inconsistent")
            expected_ratio = self.compressed_tokens / self.original_tokens
            if abs(self.compression_ratio - expected_ratio) > 0.000001:
                raise ValueError("stored compression ratio is inconsistent")
        return self


class BenchmarkPricing(BenchmarkStrictModel):
    snapshot_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    input_cache_hit_usd_per_m_tokens: float = Field(ge=0)
    input_cache_miss_usd_per_m_tokens: float = Field(ge=0)
    output_usd_per_m_tokens: float = Field(ge=0)
    note: Literal["Configured DeepSeek prices; estimates are scenarios, not actual billing."] = (
        "Configured DeepSeek prices; estimates are scenarios, not actual billing."
    )


class BenchmarkConfiguration(BenchmarkStrictModel):
    model: Literal["deepseek-v4-flash"]
    max_tokens: int = Field(ge=1)
    thinking: Literal["disabled"]
    response_format: Literal["json_object"]
    network_retries: Literal[0]
    execution_order: Literal["baseline_uncompressed_then_paritok"]
    scoring_rule: Literal["40+20+15+15+10"]
    token_metric_policy: Literal[
        "Paritok Token metrics only for actual compression from per-request /stats deltas; "
        "baseline, skipped_low_yield, and unavailable values are null."
    ]


class BenchmarkSummary(BenchmarkStrictModel):
    expected_cases: int = Field(ge=1)
    expected_rows: int = Field(ge=2)
    completed_rows: int = Field(ge=0)
    baseline_completed_rows: int = Field(ge=0)
    compressed_rows: int = Field(ge=0)
    skipped_low_yield_rows: int = Field(ge=0)
    unavailable_rows: int = Field(ge=0)
    upstream_failed_rows: int = Field(ge=0)
    upstream_timeout_rows: int = Field(ge=0)
    quality_pair_count: int = Field(ge=0)
    average_tokens_saved: float | None = Field(default=None, ge=0)
    average_token_savings_percent: float | None = Field(default=None, ge=0, le=100)
    baseline_average_quality: float | None = Field(default=None, ge=0, le=100)
    paritok_average_quality: float | None = Field(default=None, ge=0, le=100)
    quality_change_points: float | None = Field(default=None, ge=-100, le=100)
    supported_claim: str = Field(min_length=1, max_length=1_000)


class BenchmarkArtifact(BenchmarkStrictModel):
    schema_version: Literal[3]
    generated_at: datetime
    finalized: bool
    case_ids: list[str] = Field(min_length=1, max_length=50)
    configuration: BenchmarkConfiguration
    pricing: BenchmarkPricing
    summary: BenchmarkSummary
    rows: list[BenchmarkRow] = Field(max_length=100)

    @model_validator(mode="after")
    def validate_artifact(self) -> "BenchmarkArtifact":
        keys = [(row.case_id, row.mode) for row in self.rows]
        if len(keys) != len(set(keys)):
            raise ValueError("benchmark rows must be unique by case and mode")
        if any(row.case_id not in self.case_ids for row in self.rows):
            raise ValueError("benchmark row references an unknown fixed case")
        expected_rows = len(self.case_ids) * 2
        if self.summary.expected_rows != expected_rows:
            raise ValueError("summary expected row count is inconsistent")
        if self.summary.expected_cases != len(self.case_ids):
            raise ValueError("summary expected case count is inconsistent")
        if self.summary.completed_rows != len(self.rows):
            raise ValueError("summary completed row count is inconsistent")
        counted_rows = (
            self.summary.baseline_completed_rows
            + self.summary.compressed_rows
            + self.summary.skipped_low_yield_rows
            + self.summary.unavailable_rows
            + self.summary.upstream_failed_rows
        )
        if counted_rows != len(self.rows):
            raise ValueError("summary status counts are inconsistent")
        if self.summary.compressed_rows != sum(row.status == "compressed" for row in self.rows):
            raise ValueError("summary compressed count is inconsistent")
        if self.summary.upstream_timeout_rows != sum(
            bool(row.error and row.error.startswith("DEEPSEEK_TIMEOUT")) for row in self.rows
        ):
            raise ValueError("summary upstream timeout count is inconsistent")
        pair_count = 0
        for case_id in self.case_ids:
            case_rows = [row for row in self.rows if row.case_id == case_id]
            if len(case_rows) == 2 and all(row.analysis is not None for row in case_rows):
                pair_count += 1
        if self.summary.quality_pair_count != pair_count:
            raise ValueError("summary quality pair count is inconsistent")
        if len(self.case_ids) != len(set(self.case_ids)):
            raise ValueError("benchmark case IDs must be unique")
        if self.finalized and len(self.rows) != expected_rows:
            raise ValueError("a finalized benchmark must retain both modes for every case")
        return self
