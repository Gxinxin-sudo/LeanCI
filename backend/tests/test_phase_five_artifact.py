import json
from pathlib import Path

import pytest

from app.benchmark_models import BenchmarkArtifact
from app.samples import load_ground_truth

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = PROJECT_ROOT / "benchmarks" / "results.json"
FIXED_CASE_IDS = (
    "python-pytest",
    "typescript-build",
    "docker-build",
    "dependency-resolution",
    "github-actions-environment",
)
REQUIRED_FLAT_FIELDS = {
    "case_id",
    "mode",
    "success",
    "original_tokens",
    "compressed_tokens",
    "tokens_saved",
    "compression_ratio",
    "prompt_tokens",
    "completion_tokens",
    "latency_ms",
    "root_cause_correct",
    "evidence_correct",
    "relevant_files_correct",
    "fix_direction_correct",
    "json_valid",
    "error",
    "run_timestamp",
    "model",
    "pricing_snapshot_date",
}


def load_published_artifact() -> tuple[dict[str, object], BenchmarkArtifact]:
    raw_json = RESULTS_PATH.read_text(encoding="utf-8")
    payload = json.loads(raw_json)
    return payload, BenchmarkArtifact.model_validate_json(raw_json)


def test_published_phase_five_artifact_preserves_fair_complete_pairs() -> None:
    payload, artifact = load_published_artifact()

    assert artifact.finalized is True
    assert tuple(artifact.case_ids) == FIXED_CASE_IDS
    assert len(artifact.rows) == 10
    assert artifact.configuration.model == "deepseek-v4-flash"
    assert artifact.configuration.max_tokens == 4096
    assert artifact.configuration.thinking == "disabled"
    assert artifact.configuration.response_format == "json_object"
    assert artifact.configuration.network_retries == 0
    assert artifact.configuration.execution_order == ("baseline_uncompressed_then_paritok")
    assert artifact.configuration.scoring_rule == "40+20+15+15+10"

    raw_rows = payload["rows"]
    assert isinstance(raw_rows, list)
    assert all(set(row) >= REQUIRED_FLAT_FIELDS for row in raw_rows)

    for case_id in FIXED_CASE_IDS:
        case_rows = [row for row in artifact.rows if row.case_id == case_id]
        assert [row.mode for row in case_rows] == [
            "baseline_uncompressed",
            "paritok",
        ]
        assert len({row.initial_messages_sha256 for row in case_rows}) == 1
        assert len({row.json_schema_sha256 for row in case_rows}) == 1
        assert len({row.model for row in case_rows}) == 1
        assert len({row.pricing_snapshot_date for row in case_rows}) == 1

        baseline = case_rows[0]
        minimum_input_tokens = load_ground_truth(case_id)["minimum_original_tokens"]
        assert baseline.prompt_tokens is not None
        assert baseline.prompt_tokens > minimum_input_tokens
        assert baseline.original_tokens is None
        assert baseline.compressed_tokens is None
        assert baseline.tokens_saved is None
        assert baseline.compression_ratio is None


def test_published_phase_five_statuses_and_token_averages_exclude_skips() -> None:
    _, artifact = load_published_artifact()
    paritok_rows = {row.case_id: row for row in artifact.rows if row.mode == "paritok"}

    assert paritok_rows["python-pytest"].status == "compressed"
    assert paritok_rows["docker-build"].status == "compressed"
    for case_id in (
        "typescript-build",
        "dependency-resolution",
        "github-actions-environment",
    ):
        row = paritok_rows[case_id]
        assert row.status == "skipped_low_yield"
        assert row.compression_skip_reason == "below_refusal_threshold"
        assert row.original_tokens is None
        assert row.compressed_tokens is None
        assert row.tokens_saved is None
        assert row.compression_ratio is None
        assert row.error is None

    compressed_rows = [row for row in paritok_rows.values() if row.status == "compressed"]
    savings_percentages = [
        (row.tokens_saved / row.original_tokens) * 100
        for row in compressed_rows
        if row.tokens_saved is not None and row.original_tokens is not None
    ]
    assert artifact.summary.compressed_rows == len(compressed_rows) == 2
    assert artifact.summary.skipped_low_yield_rows == 3
    assert artifact.summary.unavailable_rows == 0
    assert artifact.summary.upstream_failed_rows == 0
    assert artifact.summary.average_token_savings_percent == pytest.approx(
        sum(savings_percentages) / len(compressed_rows),
        abs=0.01,
    )


def test_published_phase_five_quality_and_cost_claims_are_bounded() -> None:
    _, artifact = load_published_artifact()

    paired_rows = [
        [row for row in artifact.rows if row.case_id == case_id] for case_id in FIXED_CASE_IDS
    ]
    valid_pairs = [
        pair
        for pair in paired_rows
        if len(pair) == 2 and all(row.analysis is not None for row in pair)
    ]
    baseline_average = sum(pair[0].quality_score for pair in valid_pairs) / len(valid_pairs)
    paritok_average = sum(pair[1].quality_score for pair in valid_pairs) / len(valid_pairs)

    assert artifact.summary.quality_pair_count == len(valid_pairs) == 5
    assert artifact.summary.baseline_average_quality == pytest.approx(baseline_average)
    assert artifact.summary.paritok_average_quality == pytest.approx(paritok_average)
    assert artifact.summary.quality_change_points == pytest.approx(
        paritok_average - baseline_average
    )
    assert "does not establish universal quality preservation" in (artifact.summary.supported_claim)

    assert artifact.pricing.input_cache_hit_usd_per_m_tokens != 3
    assert artifact.pricing.input_cache_miss_usd_per_m_tokens != 3
    assert "not actual billing" in artifact.pricing.note
    for row in artifact.rows:
        assert "not an actual bill" in row.cost_estimate.disclaimer
