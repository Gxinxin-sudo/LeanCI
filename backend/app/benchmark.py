"""Isolated, fixed-case benchmark runner and deterministic report generator."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import PurePosixPath
from time import perf_counter
from typing import Any

from app.benchmark_models import (
    BenchmarkArtifact,
    BenchmarkConfiguration,
    BenchmarkCostEstimate,
    BenchmarkGroundTruth,
    BenchmarkPricing,
    BenchmarkRow,
    BenchmarkSummary,
    DeterministicScore,
    HumanReview,
)
from app.config import PROJECT_ROOT, Settings
from app.llm.prompts import build_paritok_analysis_messages
from app.llm.providers import (
    DirectDeepSeekProvider,
    DirectUseCase,
    LLMProviderError,
    ParitokDeepSeekProvider,
)
from app.models import AnalyzeRequest, DiagnosticAnalysis, ProviderResult, ProviderUsage
from app.paritok import ParitokClient, ParitokClientError, calculate_stats_delta
from app.samples import SAMPLE_DEFINITIONS, load_ground_truth, load_sample

BENCHMARKS_ROOT = PROJECT_ROOT / "benchmarks"
RESULTS_JSON_PATH = BENCHMARKS_ROOT / "results.json"
RESULTS_CSV_PATH = BENCHMARKS_ROOT / "results.csv"
REPORT_PATH = BENCHMARKS_ROOT / "report.md"
CASE_IDS = tuple(definition.id for definition in SAMPLE_DEFINITIONS)
# The official local trace diagnosis on 2026-07-26 proved that both evidence
# tool blocks for these fixed cases were skipped as below_refusal_threshold.
# A future 0->0 window is only classified as an expected low-benefit skip for
# these unchanged case IDs. Other 0->0 windows remain fail-closed.
TRACE_VERIFIED_LOW_BENEFIT_CASE_IDS = frozenset(
    {
        "typescript-build",
        "dependency-resolution",
        "github-actions-environment",
    }
)
_USD_QUANTUM = Decimal("0.00000001")


class BenchmarkParitokProvider(ParitokDeepSeekProvider):
    """Paritok route with upstream usage exposed only for benchmark accounting."""

    expose_upstream_usage = True


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _basename(value: str) -> str:
    return PurePosixPath(value.replace("\\", "/")).name.casefold()


def _matches_groups(text: str, groups: list[list[str]]) -> bool:
    normalized = text.casefold()
    return all(any(term.casefold() in normalized for term in group) for group in groups)


def score_analysis(
    analysis: DiagnosticAnalysis | None,
    ground_truth: BenchmarkGroundTruth,
    *,
    json_valid: bool,
) -> DeterministicScore:
    """Apply the fixed 40/20/15/15/10 rubric without an LLM judge."""

    if analysis is None or not json_valid:
        return DeterministicScore(
            root_cause_correct=False,
            evidence_correct=False,
            relevant_files_correct=False,
            fix_direction_correct=False,
            json_valid=False,
            quality_score=0,
            failed_checks=[
                "root_cause",
                "evidence",
                "relevant_files",
                "fix_direction",
                "json_valid",
            ],
        )

    root_cause_correct = _matches_groups(
        analysis.root_cause,
        ground_truth.root_cause_term_groups,
    )
    evidence_correct = all(
        any(
            _basename(item.source) == _basename(expected.source)
            and _matches_groups(
                f"{item.excerpt}\n{item.explanation}",
                expected.term_groups,
            )
            for item in analysis.evidence
        )
        for expected in ground_truth.expected_evidence
    )
    actual_files = {_basename(value) for value in analysis.relevant_files}
    relevant_files_correct = all(
        _basename(expected) in actual_files for expected in ground_truth.expected_relevant_files
    )
    fix_text = "\n".join([*analysis.recommended_changes, analysis.patch])
    fix_direction_correct = _matches_groups(
        fix_text,
        ground_truth.fix_direction_term_groups,
    )
    checks = {
        "root_cause": root_cause_correct,
        "evidence": evidence_correct,
        "relevant_files": relevant_files_correct,
        "fix_direction": fix_direction_correct,
        "json_valid": True,
    }
    quality_score = (
        (40 if root_cause_correct else 0)
        + (20 if evidence_correct else 0)
        + (15 if relevant_files_correct else 0)
        + (15 if fix_direction_correct else 0)
        + 10
    )
    return DeterministicScore(
        root_cause_correct=root_cause_correct,
        evidence_correct=evidence_correct,
        relevant_files_correct=relevant_files_correct,
        fix_direction_correct=fix_direction_correct,
        json_valid=True,
        quality_score=quality_score,
        failed_checks=[name for name, passed in checks.items() if not passed],
    )


def _money(tokens: int, price: Decimal) -> float:
    value = Decimal(tokens) * price / Decimal(1_000_000)
    return float(value.quantize(_USD_QUANTUM, rounding=ROUND_HALF_UP))


def _cost_estimate(
    settings: Settings,
    usage: ProviderUsage | None,
    *,
    saved_tokens: int | None,
) -> BenchmarkCostEstimate:
    if usage is None:
        return BenchmarkCostEstimate()
    cache_split = None
    if usage.prompt_cache_hit_tokens is not None and usage.prompt_cache_miss_tokens is not None:
        cache_split = _money(
            usage.prompt_cache_hit_tokens,
            settings.deepseek_input_cache_hit_usd_per_m,
        ) + _money(
            usage.prompt_cache_miss_tokens,
            settings.deepseek_input_cache_miss_usd_per_m,
        )
    return BenchmarkCostEstimate(
        input_if_all_cache_hit_usd=_money(
            usage.prompt_tokens,
            settings.deepseek_input_cache_hit_usd_per_m,
        ),
        input_if_all_cache_miss_usd=_money(
            usage.prompt_tokens,
            settings.deepseek_input_cache_miss_usd_per_m,
        ),
        input_from_reported_cache_split_usd=cache_split,
        output_usd=_money(
            usage.completion_tokens,
            settings.deepseek_output_usd_per_m,
        ),
        saved_input_if_cache_hit_usd=(
            _money(saved_tokens, settings.deepseek_input_cache_hit_usd_per_m)
            if saved_tokens is not None
            else None
        ),
        saved_input_if_cache_miss_usd=(
            _money(saved_tokens, settings.deepseek_input_cache_miss_usd_per_m)
            if saved_tokens is not None
            else None
        ),
    )


def _row(
    *,
    case_id: str,
    mode: str,
    settings: Settings,
    messages_hash: str,
    schema_hash: str,
    started_at: float,
    result: ProviderResult | None = None,
    ground_truth: BenchmarkGroundTruth,
    error: str | None = None,
    original_tokens: int | None = None,
    compressed_tokens: int | None = None,
    tokens_saved: int | None = None,
    compression_ratio: float | None = None,
    compression_skip_reason: str | None = None,
) -> BenchmarkRow:
    compression_skipped = compression_skip_reason is not None
    success = None if compression_skipped else result is not None and error is None
    status = "compression_skipped" if compression_skipped else ("success" if success else "failed")
    analysis = result.analysis if success is True else None
    score = (
        None
        if compression_skipped
        else score_analysis(analysis, ground_truth, json_valid=success is True)
    )
    usage = result.usage if result is not None else None
    return BenchmarkRow(
        case_id=case_id,
        mode=mode,
        status=status,
        success=success,
        compression_skip_reason=compression_skip_reason,
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        tokens_saved=tokens_saved,
        compression_ratio=compression_ratio,
        prompt_tokens=usage.prompt_tokens if usage else None,
        completion_tokens=usage.completion_tokens if usage else None,
        prompt_cache_hit_tokens=usage.prompt_cache_hit_tokens if usage else None,
        prompt_cache_miss_tokens=usage.prompt_cache_miss_tokens if usage else None,
        latency_ms=round((perf_counter() - started_at) * 1000),
        root_cause_correct=score.root_cause_correct if score else None,
        evidence_correct=score.evidence_correct if score else None,
        relevant_files_correct=score.relevant_files_correct if score else None,
        fix_direction_correct=score.fix_direction_correct if score else None,
        json_valid=score.json_valid if score else None,
        quality_score=score.quality_score if score else None,
        error=error,
        run_timestamp=datetime.now(UTC),
        model=settings.deepseek_model,
        pricing_snapshot_date=settings.pricing_snapshot_date.isoformat(),
        initial_messages_sha256=messages_hash,
        json_schema_sha256=schema_hash,
        score=score,
        human_review=HumanReview(),
        cost_estimate=_cost_estimate(settings, usage, saved_tokens=tokens_saved),
        analysis=analysis,
    )


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, (LLMProviderError, ParitokClientError)):
        code = exc.code
        message = exc.public_message
        return f"{code}: {message}"
    return "BENCHMARK_INTERNAL_ERROR: The fixed benchmark case could not be completed."


class BenchmarkRunner:
    """Run one fixed case as baseline first, then through verified Paritok."""

    def __init__(self, settings: Settings, paritok_client: ParitokClient) -> None:
        self.settings = settings
        self.paritok_client = paritok_client

    def _providers(self) -> tuple[DirectDeepSeekProvider, BenchmarkParitokProvider]:
        if not self.settings.deepseek_api_key_configured or self.settings.deepseek_api_key is None:
            raise LLMProviderError(
                code="DEEPSEEK_API_KEY_MISSING",
                message="DEEPSEEK_API_KEY is not configured in the local .env file.",
            )
        common: dict[str, Any] = {
            "api_key": self.settings.deepseek_api_key,
            "model": self.settings.deepseek_model,
            "max_tokens": self.settings.deepseek_max_output_tokens,
            "timeout_seconds": self.settings.deepseek_timeout_seconds,
            "max_network_retries": 0,
            "retry_base_delay_seconds": 0,
            "chunk_target_tokens": self.settings.paritok_chunk_target_tokens,
        }
        return (
            DirectDeepSeekProvider(
                use_case=DirectUseCase.BENCHMARK_BASELINE,
                base_url=str(self.settings.deepseek_base_url),
                **common,
            ),
            BenchmarkParitokProvider(
                base_url=str(self.settings.paritok_proxy_base_url),
                **common,
            ),
        )

    async def run_case(self, case_id: str) -> list[BenchmarkRow]:
        if case_id not in CASE_IDS:
            raise ValueError("benchmark accepts only bundled case IDs")
        payload = load_sample(case_id)
        ground_truth = BenchmarkGroundTruth.model_validate(load_ground_truth(case_id))
        context = AnalyzeRequest(
            log_text=payload.log_text,
            files=payload.files,
        ).to_untrusted_context()
        messages = build_paritok_analysis_messages(
            context,
            target_tokens=self.settings.paritok_chunk_target_tokens,
            model=self.settings.deepseek_model,
        )
        messages_hash = _sha256_json(messages)
        schema_hash = _sha256_json(DiagnosticAnalysis.model_json_schema())
        preflight_started = perf_counter()

        try:
            await self.paritok_client.health()
            await self.paritok_client.hosted_gpu()
            baseline_stats_before = await self.paritok_client.stats()
            direct, paritok = self._providers()
        except Exception as exc:
            safe_error = _safe_error(exc)
            return [
                _row(
                    case_id=case_id,
                    mode=mode,
                    settings=self.settings,
                    messages_hash=messages_hash,
                    schema_hash=schema_hash,
                    started_at=preflight_started,
                    ground_truth=ground_truth,
                    error=f"PREFLIGHT_FAILED: {safe_error}",
                )
                for mode in ("baseline_uncompressed", "paritok")
            ]

        baseline_started = perf_counter()
        baseline_result: ProviderResult | None = None
        baseline_error: str | None = None
        try:
            baseline_result = await direct.analyze_messages(messages)
        except Exception as exc:
            baseline_error = _safe_error(exc)
        try:
            baseline_stats_after = await self.paritok_client.stats()
            if baseline_stats_after != baseline_stats_before:
                baseline_result = None
                baseline_error = (
                    "PARITOK_STATS_CHANGED_DURING_BASELINE: Baseline isolation could not "
                    "be proved; the direct result was discarded."
                )
        except Exception as exc:
            baseline_result = None
            baseline_error = f"BASELINE_ISOLATION_CHECK_FAILED: {_safe_error(exc)}"
            baseline_stats_after = baseline_stats_before

        baseline_row = _row(
            case_id=case_id,
            mode="baseline_uncompressed",
            settings=self.settings,
            messages_hash=messages_hash,
            schema_hash=schema_hash,
            started_at=baseline_started,
            result=baseline_result,
            ground_truth=ground_truth,
            error=baseline_error,
        )

        paritok_started = perf_counter()
        paritok_result: ProviderResult | None = None
        paritok_error: str | None = None
        compression_skip_reason: str | None = None
        stats_values: dict[str, int | float | None] = {
            "original_tokens": None,
            "compressed_tokens": None,
            "tokens_saved": None,
            "compression_ratio": None,
        }
        try:
            paritok_result = await paritok.analyze_messages(messages)
        except Exception as exc:
            paritok_error = _safe_error(exc)
        try:
            paritok_stats_after = await self.paritok_client.stats()
            await self.paritok_client.hosted_gpu()
            delta = calculate_stats_delta(baseline_stats_after, paritok_stats_after)
            stats_values = (
                {
                    "original_tokens": delta.original_tokens,
                    "compressed_tokens": delta.compressed_tokens,
                    "tokens_saved": delta.saved_tokens,
                    "compression_ratio": delta.compression_ratio,
                }
                if delta.original_tokens > 0
                else {
                    "original_tokens": None,
                    "compressed_tokens": None,
                    "tokens_saved": None,
                    "compression_ratio": None,
                }
            )
            if (
                paritok_result is not None
                and delta.proxy_requests != paritok_result.request_attempts
            ):
                paritok_result = None
                paritok_error = (
                    "PARITOK_ROUTE_NOT_VERIFIED: The stats request delta did not match "
                    "the benchmark provider attempts."
                )
            if paritok_result is not None and paritok_error is None and delta.original_tokens == 0:
                stats_values = {
                    "original_tokens": None,
                    "compressed_tokens": None,
                    "tokens_saved": None,
                    "compression_ratio": None,
                }
                if case_id in TRACE_VERIFIED_LOW_BENEFIT_CASE_IDS:
                    compression_skip_reason = "below_refusal_threshold"
                else:
                    paritok_result = None
                    paritok_error = (
                        "PARITOK_COMPRESSION_SKIP_UNVERIFIED: /stats recorded 0->0, "
                        "but no fixed trace diagnosis proves a low-benefit skip."
                    )
            elif (
                delta.original_tokens > 0
                and delta.original_tokens < ground_truth.minimum_original_tokens
            ):
                paritok_result = None
                paritok_error = (
                    "ORIGINAL_TOKEN_MINIMUM_NOT_MET: The verified stats delta was below "
                    "the fixed case minimum."
                )
        except Exception as exc:
            paritok_result = None
            paritok_error = f"PARITOK_STATS_VALIDATION_FAILED: {_safe_error(exc)}"

        paritok_row = _row(
            case_id=case_id,
            mode="paritok",
            settings=self.settings,
            messages_hash=messages_hash,
            schema_hash=schema_hash,
            started_at=paritok_started,
            result=paritok_result,
            ground_truth=ground_truth,
            error=paritok_error,
            compression_skip_reason=compression_skip_reason,
            **stats_values,
        )
        return [baseline_row, paritok_row]


def build_artifact(settings: Settings, rows: list[BenchmarkRow]) -> BenchmarkArtifact:
    ordered_rows = sorted(
        rows,
        key=lambda row: (
            CASE_IDS.index(row.case_id),
            0 if row.mode == "baseline_uncompressed" else 1,
        ),
    )
    expected_rows = len(CASE_IDS) * 2
    finalized = len(ordered_rows) == expected_rows
    compressed_paritok = [
        row
        for row in ordered_rows
        if row.mode == "paritok"
        and row.tokens_saved is not None
        and row.compression_ratio is not None
    ]

    def average_quality(mode: str) -> float | None:
        mode_rows = [
            row
            for row in ordered_rows
            if row.mode == mode and row.status == "success" and row.quality_score is not None
        ]
        if not mode_rows:
            return None
        return round(
            sum(row.quality_score for row in mode_rows if row.quality_score is not None)
            / len(mode_rows),
            2,
        )

    baseline_quality = average_quality("baseline_uncompressed")
    paritok_quality = average_quality("paritok")
    average_saved = (
        round(
            sum(row.tokens_saved or 0 for row in compressed_paritok) / len(compressed_paritok),
            2,
        )
        if compressed_paritok
        else None
    )
    average_savings_percent = (
        round(
            sum((1 - (row.compression_ratio or 0)) * 100 for row in compressed_paritok)
            / len(compressed_paritok),
            2,
        )
        if compressed_paritok
        else None
    )
    failures = sum(row.status == "failed" for row in ordered_rows)
    successful_rows = sum(row.status == "success" for row in ordered_rows)
    skipped_rows = sum(row.status == "compression_skipped" for row in ordered_rows)
    upstream_timeouts = sum(
        bool(row.error and row.error.startswith("DEEPSEEK_TIMEOUT")) for row in ordered_rows
    )
    quality_change = (
        round(paritok_quality - baseline_quality, 2)
        if paritok_quality is not None and baseline_quality is not None
        else None
    )
    if not finalized:
        supported_claim = "Benchmark incomplete; no promotional claim is supported."
    else:
        compression_text = (
            f"{average_savings_percent:.2f}% average Token savings across "
            f"{len(compressed_paritok)} rows where compression actually occurred"
            if average_savings_percent is not None
            else "no verified average Token savings"
        )
        quality_text = (
            f"a {quality_change:+.2f}-point deterministic quality change"
            if quality_change is not None
            else "no comparable Paritok quality average"
        )
        supported_claim = (
            f"On these five fixed cases, the run observed {compression_text} and "
            f"{quality_text}; {skipped_rows} low-benefit compression skips and "
            f"{failures} failed rows remain included. This does not establish universal "
            "quality preservation, production reliability, or actual billing savings."
        )

    return BenchmarkArtifact(
        schema_version=2,
        generated_at=datetime.now(UTC),
        finalized=finalized,
        case_ids=list(CASE_IDS),
        configuration=BenchmarkConfiguration(
            model=settings.deepseek_model,
            max_tokens=settings.deepseek_max_output_tokens,
            thinking="disabled",
            response_format="json_object",
            network_retries=0,
            execution_order="baseline_uncompressed_then_paritok",
            scoring_rule="40+20+15+15+10",
            token_metric_policy=(
                "Paritok Token metrics only for actual compression from per-request /stats "
                "deltas; baseline and compression_skipped values are null."
            ),
        ),
        pricing=BenchmarkPricing(
            snapshot_date=settings.pricing_snapshot_date.isoformat(),
            input_cache_hit_usd_per_m_tokens=float(settings.deepseek_input_cache_hit_usd_per_m),
            input_cache_miss_usd_per_m_tokens=float(settings.deepseek_input_cache_miss_usd_per_m),
            output_usd_per_m_tokens=float(settings.deepseek_output_usd_per_m),
        ),
        summary=BenchmarkSummary(
            expected_cases=len(CASE_IDS),
            expected_rows=expected_rows,
            completed_rows=len(ordered_rows),
            successful_rows=successful_rows,
            compression_skipped_rows=skipped_rows,
            failed_rows=failures,
            actual_compression_rows=len(compressed_paritok),
            upstream_timeout_rows=upstream_timeouts,
            average_tokens_saved=average_saved,
            average_token_savings_percent=average_savings_percent,
            baseline_average_quality=baseline_quality,
            paritok_average_quality=paritok_quality,
            quality_change_points=quality_change,
            supported_claim=supported_claim,
        ),
        rows=ordered_rows,
    )


def load_results() -> BenchmarkArtifact:
    source = RESULTS_JSON_PATH.read_text(encoding="utf-8")
    payload = json.loads(source)
    if payload.get("schema_version") == 1:
        return migrate_v1_artifact(payload)
    return BenchmarkArtifact.model_validate_json(source)


def migrate_v1_artifact(payload: dict[str, Any]) -> BenchmarkArtifact:
    """Reclassify the saved acceptance run without issuing any model request."""

    if payload.get("schema_version") != 1:
        raise ValueError("only schema_version=1 benchmark artifacts can be migrated")
    migrated_rows: list[BenchmarkRow] = []
    for source_row in payload.get("rows", []):
        row = dict(source_row)
        row["run_timestamp"] = datetime.fromisoformat(row["run_timestamp"])
        is_verified_skip = (
            row.get("mode") == "paritok"
            and row.get("case_id") in TRACE_VERIFIED_LOW_BENEFIT_CASE_IDS
            and row.get("original_tokens") == 0
            and row.get("compressed_tokens") == 0
        )
        if is_verified_skip:
            row.update(
                {
                    "status": "compression_skipped",
                    "success": None,
                    "compression_skip_reason": "below_refusal_threshold",
                    "original_tokens": None,
                    "compressed_tokens": None,
                    "tokens_saved": None,
                    "compression_ratio": None,
                    "root_cause_correct": None,
                    "evidence_correct": None,
                    "relevant_files_correct": None,
                    "fix_direction_correct": None,
                    "json_valid": None,
                    "quality_score": None,
                    "error": None,
                    "score": None,
                    "analysis": None,
                }
            )
            cost_estimate = dict(row["cost_estimate"])
            cost_estimate["saved_input_if_cache_hit_usd"] = None
            cost_estimate["saved_input_if_cache_miss_usd"] = None
            row["cost_estimate"] = cost_estimate
        else:
            row["status"] = "success" if row.get("success") is True else "failed"
            row["compression_skip_reason"] = None
        migrated_rows.append(BenchmarkRow.model_validate(row))

    configuration = payload["configuration"]
    pricing = payload["pricing"]
    settings = Settings(
        _env_file=None,
        deepseek_model=configuration["model"],
        deepseek_max_output_tokens=configuration["max_tokens"],
        pricing_snapshot_date=date.fromisoformat(pricing["snapshot_date"]),
        deepseek_input_cache_hit_usd_per_m=Decimal(
            str(pricing["input_cache_hit_usd_per_m_tokens"])
        ),
        deepseek_input_cache_miss_usd_per_m=Decimal(
            str(pricing["input_cache_miss_usd_per_m_tokens"])
        ),
        deepseek_output_usd_per_m=Decimal(str(pricing["output_usd_per_m_tokens"])),
    )
    artifact = build_artifact(settings, migrated_rows)
    return artifact.model_copy(
        update={"generated_at": datetime.fromisoformat(payload["generated_at"])}
    )


def merge_case_rows(
    existing: BenchmarkArtifact | None,
    case_rows: list[BenchmarkRow],
) -> list[BenchmarkRow]:
    replacement_case_ids = {row.case_id for row in case_rows}
    retained = (
        [row for row in existing.rows if row.case_id not in replacement_case_ids]
        if existing is not None
        else []
    )
    return [*retained, *case_rows]


def build_preflight_failure_rows(
    settings: Settings,
    *,
    error: str,
) -> list[BenchmarkRow]:
    """Build all planned failure rows after one bounded external preflight.

    This never calls a provider and deliberately leaves every Token field null.
    It exists so an unavailable hosted GPU is visible in the committed artifact
    rather than causing cases to disappear.
    """

    rows: list[BenchmarkRow] = []
    schema_hash = _sha256_json(DiagnosticAnalysis.model_json_schema())
    for case_id in CASE_IDS:
        payload = load_sample(case_id)
        ground_truth = BenchmarkGroundTruth.model_validate(load_ground_truth(case_id))
        context = AnalyzeRequest(
            log_text=payload.log_text,
            files=payload.files,
        ).to_untrusted_context()
        messages = build_paritok_analysis_messages(
            context,
            target_tokens=settings.paritok_chunk_target_tokens,
            model=settings.deepseek_model,
        )
        messages_hash = _sha256_json(messages)
        for mode in ("baseline_uncompressed", "paritok"):
            rows.append(
                _row(
                    case_id=case_id,
                    mode=mode,
                    settings=settings,
                    messages_hash=messages_hash,
                    schema_hash=schema_hash,
                    started_at=perf_counter(),
                    ground_truth=ground_truth,
                    error=error,
                )
            )
    return rows


def _csv_text(artifact: BenchmarkArtifact) -> str:
    fieldnames = [
        "case_id",
        "mode",
        "status",
        "success",
        "compression_skip_reason",
        "original_tokens",
        "compressed_tokens",
        "tokens_saved",
        "compression_ratio",
        "prompt_tokens",
        "completion_tokens",
        "prompt_cache_hit_tokens",
        "prompt_cache_miss_tokens",
        "latency_ms",
        "root_cause_correct",
        "evidence_correct",
        "relevant_files_correct",
        "fix_direction_correct",
        "json_valid",
        "quality_score",
        "error",
        "run_timestamp",
        "model",
        "pricing_snapshot_date",
        "manual_review_status",
        "manual_review_notes",
    ]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in artifact.rows:
        value = row.model_dump(mode="json")
        writer.writerow(
            {
                **{name: value.get(name) for name in fieldnames},
                "manual_review_status": row.human_review.status,
                "manual_review_notes": row.human_review.notes,
            }
        )
    return stream.getvalue()


def _markdown_report(artifact: BenchmarkArtifact) -> str:
    summary = artifact.summary
    lines = [
        "# LeanCI Benchmark Report",
        "",
        f"- Generated: `{artifact.generated_at.isoformat()}`",
        f"- Model: `{artifact.configuration.model}`",
        f"- Finalized: `{str(artifact.finalized).lower()}`",
        f"- Pricing snapshot: `{artifact.pricing.snapshot_date}`",
        (
            "- Fixed request configuration: "
            f"`max_tokens={artifact.configuration.max_tokens}`, thinking disabled, "
            "JSON object, zero network retries"
        ),
        (
            "- Token metric policy: baseline and `compression_skipped` fields are null; "
            "Paritok Token fields exist only when isolated `/stats` proves compression."
        ),
        "",
        "## Summary",
        "",
        f"- Successful rows: **{summary.successful_rows}/{summary.expected_rows}**",
        f"- Normal low-benefit compression skips: **{summary.compression_skipped_rows}**",
        f"- Failed rows retained: **{summary.failed_rows}**",
        f"- Rows with actual compression proof: **{summary.actual_compression_rows}**",
        f"- Upstream DeepSeek timeouts: **{summary.upstream_timeout_rows}**",
        (
            f"- Average Token savings across actual compression rows only: "
            f"**{summary.average_token_savings_percent:.2f}%**"
            if summary.average_token_savings_percent is not None
            else "- Average Token savings across actual compression rows only: **unavailable**"
        ),
        (
            f"- Baseline average quality: **{summary.baseline_average_quality:.2f}/100**"
            if summary.baseline_average_quality is not None
            else "- Baseline average quality: **not applicable**"
        ),
        (
            f"- Paritok average quality: **{summary.paritok_average_quality:.2f}/100**"
            if summary.paritok_average_quality is not None
            else "- Paritok average quality: **not applicable**"
        ),
        (
            f"- Quality change: **{summary.quality_change_points:+.2f} points**"
            if summary.quality_change_points is not None
            else "- Quality change: **not applicable**"
        ),
        "",
        summary.supported_claim,
        "",
        "## Fixed quality rubric",
        "",
        "| Check | Points | Method |",
        "| --- | ---: | --- |",
        "| Root cause | 40 | Required ground-truth term groups in `root_cause` |",
        "| Evidence | 20 | Expected source plus supplied-evidence anchors |",
        "| Relevant files | 15 | Required filenames all present |",
        "| Fix direction | 15 | Required direction term groups in changes/patch |",
        "| JSON completeness | 10 | Strict `DiagnosticAnalysis` validation |",
        "",
        "The model never scores itself. Every row keeps `human_review.status=pending` so "
        "a reviewer can confirm or override the deterministic result without rewriting it.",
        "",
        "## Results",
        "",
        (
            "| Case | Mode | Status | Original | Compressed | Saved | Saved % | "
            "Prompt | Completion | Quality | Latency | Error |"
        ),
        ("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"),
    ]
    for row in artifact.rows:
        saved_percent = (
            f"{(1 - row.compression_ratio) * 100:.2f}%"
            if row.compression_ratio is not None
            else "—"
        )
        error = (row.error or "—").replace("|", "\\|")
        lines.append(
            f"| {row.case_id} | {row.mode} | {row.status} | "
            f"{row.original_tokens if row.original_tokens is not None else '—'} | "
            f"{row.compressed_tokens if row.compressed_tokens is not None else '—'} | "
            f"{row.tokens_saved if row.tokens_saved is not None else '—'} | "
            f"{saved_percent} | "
            f"{row.prompt_tokens if row.prompt_tokens is not None else '—'} | "
            f"{row.completion_tokens if row.completion_tokens is not None else '—'} | "
            f"{row.quality_score if row.quality_score is not None else 'N/A'} | "
            f"{row.latency_ms} ms | {error} |"
        )
    lines.extend(
        [
            "",
            "## Failures and review",
            "",
        ]
    )
    skipped = [row for row in artifact.rows if row.status == "compression_skipped"]
    if skipped:
        lines.append(
            "- Expected low-benefit skips (normal Paritok behavior, not an outage, "
            "cache hit, or stats defect):"
        )
        for row in skipped:
            lines.append(
                f"  - `{row.case_id}` / `{row.mode}`: "
                f"`compression_skipped` (`{row.compression_skip_reason}`); Token savings, "
                "compression ratio, and quality are not applicable."
            )
    failed = [row for row in artifact.rows if row.status == "failed"]
    if failed:
        for row in failed:
            lines.append(f"- `{row.case_id}` / `{row.mode}`: {row.error}")
            if row.error and row.error.startswith("DEEPSEEK_TIMEOUT"):
                lines.append(
                    "  - The isolated `/stats` delta was retained, but the upstream "
                    "completion exceeded the fixed provider timeout. No response usage "
                    "or analysis was invented."
                )
            elif row.error and row.error.startswith("ORIGINAL_TOKEN_MINIMUM_NOT_MET"):
                lines.append(
                    "  - The verified `/stats` window recorded "
                    f"`{row.original_tokens}→{row.compressed_tokens}` tokens, below the "
                    "fixed 5,000 original-Token acceptance gate. The returned analysis "
                    "was discarded and scored zero."
                )
    else:
        lines.append("- No API or schema failures occurred in this fixed run.")
    lines.extend(
        [
            "",
            "A quality score below 100 is not hidden and should be reviewed against the "
            "stored `analysis` object and the case's `ground_truth.json`.",
            "",
            "## Cost interpretation",
            "",
            (
                f"- Cache-hit input scenario: "
                f"`${artifact.pricing.input_cache_hit_usd_per_m_tokens}/1M` tokens."
            ),
            (
                f"- Cache-miss input scenario: "
                f"`${artifact.pricing.input_cache_miss_usd_per_m_tokens}/1M` tokens."
            ),
            (f"- Output estimate: `${artifact.pricing.output_usd_per_m_tokens}/1M` tokens."),
            "- These are configured estimates, not an actual bill.",
            "- No Paritok `estimated_cost_saved_usd` value is used.",
            "",
            "## Reproduce",
            "",
            "Start the local Paritok Proxy, then run each fixed case with explicit cost consent:",
            "",
            "```powershell",
            ".\\backend\\.venv\\Scripts\\python.exe scripts\\run_benchmark.py "
            "--confirm-cost --case python-pytest",
            ".\\backend\\.venv\\Scripts\\python.exe scripts\\run_benchmark.py "
            "--confirm-cost --case typescript-build",
            ".\\backend\\.venv\\Scripts\\python.exe scripts\\run_benchmark.py "
            "--confirm-cost --case docker-build",
            ".\\backend\\.venv\\Scripts\\python.exe scripts\\run_benchmark.py "
            "--confirm-cost --case dependency-resolution",
            ".\\backend\\.venv\\Scripts\\python.exe scripts\\run_benchmark.py "
            "--confirm-cost --case github-actions-environment",
            "```",
            "",
            "Each command makes two expected model calls (baseline then Paritok), allows at "
            "most one JSON repair per mode, performs no network retry, and keeps failed rows.",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(artifact: BenchmarkArtifact) -> None:
    BENCHMARKS_ROOT.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON_PATH.write_text(
        artifact.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    RESULTS_CSV_PATH.write_text(
        _csv_text(artifact),
        encoding="utf-8",
        newline="\n",
    )
    REPORT_PATH.write_text(
        _markdown_report(artifact),
        encoding="utf-8",
        newline="\n",
    )
