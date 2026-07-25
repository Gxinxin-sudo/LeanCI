"""Deterministic application analysis data.

This module does not import, configure, or call Paritok, DeepSeek, or any other
external service.
"""

from app.models import AnalysisResult, EvidenceItem, UnavailableCompressionStats


def build_mock_analysis() -> AnalysisResult:
    """Return a stable UI-development contract with unavailable token metrics."""

    return AnalysisResult(
        summary=(
            "The TypeScript build stops while compiling the report service because "
            "an optional environment value is assigned to a required string."
        ),
        root_cause=(
            "`process.env.REPORT_BUCKET` has the type `string | undefined`, but "
            "`uploadReport` requires a definite string. Strict null checks correctly "
            "reject the call before the bundle is produced."
        ),
        confidence=0.94,
        evidence=[
            EvidenceItem(
                source="ci.log",
                line_start=8,
                line_end=9,
                excerpt=(
                    "src/services/report.ts(42,19): error TS2345: Argument of type "
                    "'string | undefined' is not assignable to parameter of type 'string'."
                ),
                explanation=(
                    "The compiler points to the upload destination argument and identifies "
                    "the exact nullable type mismatch."
                ),
            ),
            EvidenceItem(
                source="src/services/report.ts",
                line_start=42,
                line_end=42,
                excerpt="await uploadReport(process.env.REPORT_BUCKET, payload)",
                explanation=(
                    "The environment variable is read at the call site without validation "
                    "or a fallback."
                ),
            ),
        ],
        relevant_files=[
            "src/services/report.ts",
            "src/config/env.ts",
            ".github/workflows/ci.yml",
        ],
        recommended_changes=[
            "Validate REPORT_BUCKET once during application startup.",
            "Pass the validated configuration value into the report service.",
            "Add a regression test for the missing-variable failure path.",
        ],
        patch=(
            "diff --git a/src/config/env.ts b/src/config/env.ts\n"
            "index 132fa11..8be1c22 100644\n"
            "--- a/src/config/env.ts\n"
            "+++ b/src/config/env.ts\n"
            "@@ -1,3 +1,8 @@\n"
            "+const reportBucket = process.env.REPORT_BUCKET\n"
            "+\n"
            "+if (!reportBucket) {\n"
            "+  throw new Error('REPORT_BUCKET is required')\n"
            "+}\n"
            "+\n"
            "+export { reportBucket }\n"
        ),
        verification_commands=[
            "npm run typecheck",
            "npm test -- src/config/env.test.ts",
            "npm run build",
        ],
        risks=[
            "Failing at startup changes when the configuration error becomes visible.",
            "Existing deployment environments must define REPORT_BUCKET.",
        ],
        missing_information=[
            "The current deployment environment variable inventory was not provided.",
            "No report service unit test was included with this demo log.",
        ],
        compression_stats=UnavailableCompressionStats(),
        analysis_time_ms=0,
    )
