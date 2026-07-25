"""Strict request and response contracts for the LeanCI API."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_LOG_CHARACTERS = 120_000
DEMO_NOTICE = "Demo data — Paritok not connected"
NonEmptyText = Annotated[str, Field(min_length=1, max_length=8_000)]
ListItemText = Annotated[str, Field(min_length=1, max_length=4_000)]
FileNameText = Annotated[str, Field(min_length=1, max_length=240)]


class StrictModel(BaseModel):
    """Base model that rejects coercion and unknown fields."""

    model_config = ConfigDict(extra="forbid", strict=True)


class AnalyzeRequest(StrictModel):
    log_text: str = Field(min_length=1, max_length=MAX_LOG_CHARACTERS)


class EvidenceItem(StrictModel):
    source: FileNameText
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    excerpt: str = Field(min_length=1, max_length=2_000)
    explanation: str = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def validate_line_range(self) -> "EvidenceItem":
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("line_end must be greater than or equal to line_start")
        return self


class DiagnosticAnalysis(StrictModel):
    """Model-generated fields only; trusted metrics are deliberately excluded."""

    summary: NonEmptyText
    root_cause: NonEmptyText
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceItem] = Field(max_length=50)
    relevant_files: list[FileNameText] = Field(max_length=100)
    recommended_changes: list[ListItemText] = Field(max_length=50)
    patch: str = Field(max_length=50_000)
    verification_commands: list[ListItemText] = Field(max_length=50)
    risks: list[ListItemText] = Field(max_length=50)
    missing_information: list[ListItemText] = Field(max_length=50)


class ProviderUsage(StrictModel):
    """Direct-test/baseline usage reported upstream, never estimated by LeanCI."""

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    prompt_cache_hit_tokens: int | None = Field(default=None, ge=0)
    prompt_cache_miss_tokens: int | None = Field(default=None, ge=0)


class ProviderResult(StrictModel):
    """Unified result; formal Paritok metrics remain outside ``usage``."""

    provider: Literal["mock", "direct_deepseek", "paritok_deepseek"]
    model: str = Field(min_length=1, max_length=120)
    analysis: DiagnosticAnalysis
    usage: ProviderUsage | None


class CompressionStats(StrictModel):
    available: Literal[False] = False
    paritok_connected: Literal[False] = False
    original_tokens: int | None = None
    compressed_tokens: int | None = None
    saved_tokens: int | None = None
    compression_ratio: float | None = None
    message: Literal["Demo data — Paritok not connected"] = DEMO_NOTICE


class AnalysisResult(DiagnosticAnalysis):
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
