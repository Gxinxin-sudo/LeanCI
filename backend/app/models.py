"""Strict request and response contracts for the phase-one API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_LOG_CHARACTERS = 120_000
DEMO_NOTICE = "Demo data — Paritok not connected"


class StrictModel(BaseModel):
    """Base model that rejects coercion and unknown fields."""

    model_config = ConfigDict(extra="forbid", strict=True)


class AnalyzeRequest(StrictModel):
    log_text: str = Field(min_length=1, max_length=MAX_LOG_CHARACTERS)


class EvidenceItem(StrictModel):
    source: str = Field(min_length=1, max_length=240)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    excerpt: str = Field(min_length=1, max_length=2_000)
    explanation: str = Field(min_length=1, max_length=2_000)


class CompressionStats(StrictModel):
    available: Literal[False] = False
    paritok_connected: Literal[False] = False
    original_tokens: int | None = None
    compressed_tokens: int | None = None
    saved_tokens: int | None = None
    compression_ratio: float | None = None
    message: Literal["Demo data — Paritok not connected"] = DEMO_NOTICE


class AnalysisResult(StrictModel):
    summary: str = Field(min_length=1)
    root_cause: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceItem]
    relevant_files: list[str]
    recommended_changes: list[str]
    patch: str
    verification_commands: list[str]
    risks: list[str]
    missing_information: list[str]
    compression_stats: CompressionStats


class HealthResponse(StrictModel):
    status: Literal["ok"]
    service: Literal["leanci-api"]
    mode: Literal["demo"]
    paritok_connected: Literal[False]
    deepseek_called: Literal[False]
    message: Literal["Demo data — Paritok not connected"]


class ConfigStatusResponse(StrictModel):
    deepseek_api_key_configured: bool
    paritok_api_key_configured: bool


class ErrorDetail(StrictModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(StrictModel):
    error: ErrorDetail
