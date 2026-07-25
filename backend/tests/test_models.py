import pytest
from pydantic import ValidationError

from app.models import AnalysisResult


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
