from app.samples import SAMPLE_DEFINITIONS, load_ground_truth, load_sample


def test_every_sample_has_long_safe_context_and_ground_truth() -> None:
    for definition in SAMPLE_DEFINITIONS:
        sample = load_sample(definition.id)
        truth = load_ground_truth(definition.id)

        assert len(sample.log_text.encode("utf-8")) > 30_000
        assert "\x00" not in sample.log_text
        assert 1 <= len(sample.files) <= 5
        assert truth["schema_version"] == 1
        assert truth["sample_id"] == definition.id
        assert truth["minimum_original_tokens"] == 5000
        assert truth["root_cause"]
        assert truth["expected_relevant_files"]
        assert truth["expected_fix_direction"]


def test_sample_generation_is_deterministic() -> None:
    first = load_sample("typescript-build")
    second = load_sample("typescript-build")

    assert first.model_dump() == second.model_dump()
