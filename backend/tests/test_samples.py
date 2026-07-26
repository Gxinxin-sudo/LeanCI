from app.samples import (
    SAMPLE_DEFINITIONS,
    load_ground_truth,
    load_sample,
    load_sample_capture,
)

CAPTURED_STAGE_FOUR_SAMPLE_IDS = (
    "python-pytest",
    "typescript-build",
    "docker-build",
)


def test_every_sample_has_long_safe_context_and_ground_truth() -> None:
    for definition in SAMPLE_DEFINITIONS:
        sample = load_sample(definition.id)
        truth = load_ground_truth(definition.id)

        assert len(sample.log_text.encode("utf-8")) > 30_000
        assert "\x00" not in sample.log_text
        assert 1 <= len(sample.files) <= 5
        assert truth["schema_version"] == 2
        assert truth["case_id"] == definition.id
        assert truth["minimum_original_tokens"] == 5000
        assert truth["expected_root_cause"]
        assert truth["root_cause_term_groups"]
        assert truth["expected_evidence"]
        assert truth["expected_relevant_files"]
        assert truth["expected_fix_direction"]
        assert truth["fix_direction_term_groups"]


def test_sample_generation_is_deterministic() -> None:
    first = load_sample("typescript-build")
    second = load_sample("typescript-build")

    assert first.model_dump() == second.model_dump()


def test_every_saved_capture_has_strict_real_stats_proof() -> None:
    for sample_id in CAPTURED_STAGE_FOUR_SAMPLE_IDS:
        capture = load_sample_capture(sample_id)

        assert capture.capture_kind == "real_paritok_stats_delta"
        assert capture.stats_delta.original_tokens > 5_000
        assert capture.analysis_result.compression_stats.original_tokens == (
            capture.stats_delta.original_tokens
        )
        assert capture.ground_truth_check.matching_relevant_files
