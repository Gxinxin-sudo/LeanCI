import pytest
from pydantic import ValidationError

from app.models import AnalysisResult, DiagnosticAnalysis


def test_analysis_result_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(
            {
                "summary": "summary",
                "root_cause": "cause",
                "confidence": 0.5,
                "evidence": [],
                "relevant_files": [],
                "recommended_changes": [],
                "patch": "",
                "verification_commands": [],
                "risks": [],
                "missing_information": [],
                "analysis_time_ms": 0,
                "compression_stats": {
                    "available": False,
                    "paritok_connected": False,
                    "original_tokens": None,
                    "compressed_tokens": None,
                    "saved_tokens": None,
                    "compression_ratio": None,
                    "message": "Demo data — Paritok not connected",
                },
                "unexpected": "rejected",
            }
        )


def test_diagnostic_analysis_rejects_missing_required_fields() -> None:
    with pytest.raises(ValidationError):
        DiagnosticAnalysis.model_validate(
            {
                "root_cause": "cause",
                "confidence": 0.5,
                "evidence": [],
                "relevant_files": [],
                "recommended_changes": [],
                "patch": "",
                "verification_commands": [],
                "risks": [],
                "missing_information": [],
            }
        )


def test_evidence_rejects_reversed_line_range() -> None:
    with pytest.raises(ValidationError):
        DiagnosticAnalysis.model_validate(
            {
                "summary": "summary",
                "root_cause": "cause",
                "confidence": 0.5,
                "evidence": [
                    {
                        "source": "ci.log",
                        "line_start": 10,
                        "line_end": 2,
                        "excerpt": "failure",
                        "explanation": "bad line range",
                    }
                ],
                "relevant_files": [],
                "recommended_changes": [],
                "patch": "",
                "verification_commands": [],
                "risks": [],
                "missing_information": [],
            }
        )
