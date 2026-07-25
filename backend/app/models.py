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
    request_attempts: int = Field(default=0, ge=0, le=12)


class UnavailableCompressionStats(StrictModel):
    available: Literal[False] = False
    paritok_connected: Literal[False] = False
    original_tokens: int | None = None
    compressed_tokens: int | None = None
    saved_tokens: int | None = None
    compression_ratio: float | None = None
    message: Literal["Demo data — Paritok not connected"] = DEMO_NOTICE


class CumulativeParitokStats(StrictModel):
    """Safe cumulative counters from Paritok; its dollar estimate is excluded."""

    total_requests: int = Field(ge=0)
    input_tokens_original: int = Field(ge=0)
    input_tokens_compressed: int = Field(ge=0)
    compression_ratio: float = Field(ge=0)
    tokens_saved: int = Field(ge=0)
    tools_filtered: int = Field(ge=0)


class DeepSeekCostEstimate(StrictModel):
    """LeanCI-owned estimate based only on the configured DeepSeek price."""

    estimated_input_cost_saved_usd: float = Field(ge=0)
    input_cache_miss_usd_per_m_tokens: float = Field(ge=0)
    pricing_snapshot_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    disclaimer: Literal["Estimate from LeanCI's configured DeepSeek price; not an actual bill."] = (
        "Estimate from LeanCI's configured DeepSeek price; not an actual bill."
    )


class VerifiedCompressionStats(StrictModel):
    available: Literal[True] = True
    paritok_connected: Literal[True] = True
    hosted_gpu_available: Literal[True] = True
    verification: Literal["local_health+hosted_gpu_preflight+stats_delta"] = (
        "local_health+hosted_gpu_preflight+stats_delta"
    )
    proxy_version: str = Field(min_length=1, max_length=80)
    model: Literal["deepseek-v4-flash"]
    proxy_requests: int = Field(ge=1, le=12)
    original_tokens: int = Field(ge=0)
    compressed_tokens: int = Field(ge=0)
    saved_tokens: int = Field(ge=0)
    compression_ratio: float = Field(ge=0)
    cumulative: CumulativeParitokStats
    cost_estimate: DeepSeekCostEstimate
    message: Literal[
        "Verified through Paritok; Token metrics come only from this request's stats delta."
    ] = "Verified through Paritok; Token metrics come only from this request's stats delta."


CompressionStats = Annotated[
    UnavailableCompressionStats | VerifiedCompressionStats,
    Field(discriminator="available"),
]


class AnalysisResult(DiagnosticAnalysis):
    compression_stats: CompressionStats


class HealthResponse(StrictModel):
    status: Literal["ok", "degraded"]
    service: Literal["leanci-api"]
    mode: Literal["paritok"]
    paritok_connected: bool
    hosted_gpu_available: bool
    proxy_version: str | None = Field(default=None, max_length=80)
    model: Literal["deepseek-v4-flash"]
    deepseek_called: Literal[False]
    message: str = Field(min_length=1, max_length=300)


class ConfigStatusResponse(StrictModel):
    deepseek_api_key_configured: bool
    paritok_api_key_configured: bool
    llm_provider: Literal["mock", "paritok"]
    model: Literal["deepseek-v4-flash"] = "deepseek-v4-flash"


class ErrorDetail(StrictModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(StrictModel):
    error: ErrorDetail
