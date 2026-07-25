"""Strict request and response contracts for the LeanCI API."""

import re
import unicodedata
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_REQUEST_BYTES = 4 * 1024 * 1024
MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_LOG_CHARACTERS = MAX_LOG_BYTES
MAX_UPLOAD_FILES = 5
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_FILE_BYTES = 1024 * 1024
ALLOWED_FILE_EXTENSIONS = frozenset(
    {
        ".cfg",
        ".conf",
        ".css",
        ".csv",
        ".dockerignore",
        ".env.example",
        ".gitignore",
        ".html",
        ".ini",
        ".js",
        ".json",
        ".jsx",
        ".log",
        ".md",
        ".properties",
        ".py",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)
ALLOWED_EXACT_FILENAMES = frozenset({"Dockerfile", "Makefile"})
_WINDOWS_RESERVED_NAMES = frozenset(
    {
        "aux",
        "clock$",
        "con",
        "nul",
        "prn",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
    }
)
_SAFE_FILENAME_CHARACTER = re.compile(r"[^A-Za-z0-9._@()+-]")
DEMO_NOTICE = "Demo data — Paritok not connected"
NonEmptyText = Annotated[str, Field(min_length=1, max_length=8_000)]
ListItemText = Annotated[str, Field(min_length=1, max_length=4_000)]
FileNameText = Annotated[str, Field(min_length=1, max_length=240)]


class StrictModel(BaseModel):
    """Base model that rejects coercion and unknown fields."""

    model_config = ConfigDict(extra="forbid", strict=True)


def _validate_text_content(value: str, *, label: str, byte_limit: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) > byte_limit:
        raise ValueError(f"{label} exceeds the UTF-8 byte limit")
    if "\x00" in value:
        raise ValueError(f"{label} contains a NUL byte")
    if any(ord(character) < 32 and character not in "\n\r\t" for character in value):
        raise ValueError(f"{label} contains unsupported control characters")
    return value


def sanitize_upload_filename(value: str) -> str:
    """Return a safe display filename without permitting any path semantics."""

    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized or normalized in {".", ".."}:
        raise ValueError("file name is empty")
    if "/" in normalized or "\\" in normalized or ":" in normalized:
        raise ValueError("file name must not contain a path")

    sanitized = _SAFE_FILENAME_CHARACTER.sub("_", normalized).strip()
    if not sanitized or sanitized in {".", ".."}:
        raise ValueError("file name cannot be safely normalized")
    if sanitized.endswith((".", " ")):
        raise ValueError("file name must not end with a dot or space")
    if len(sanitized) > 120:
        raise ValueError("file name exceeds 120 characters")

    stem = sanitized.rsplit(".", 1)[0].casefold()
    if stem in _WINDOWS_RESERVED_NAMES:
        raise ValueError("file name is reserved by the operating system")

    lower_name = sanitized.casefold()
    suffixes = sorted(ALLOWED_FILE_EXTENSIONS, key=len, reverse=True)
    if sanitized not in ALLOWED_EXACT_FILENAMES and not any(
        lower_name.endswith(suffix) for suffix in suffixes
    ):
        raise ValueError("file extension is not in the text-file allowlist")
    return sanitized


class UploadedTextFile(StrictModel):
    name: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=MAX_FILE_BYTES)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return sanitize_upload_filename(value)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return _validate_text_content(
            value,
            label="uploaded file",
            byte_limit=MAX_FILE_BYTES,
        )


class AnalyzeRequest(StrictModel):
    log_text: str = Field(min_length=1, max_length=MAX_LOG_CHARACTERS)
    files: list[UploadedTextFile] = Field(default_factory=list, max_length=MAX_UPLOAD_FILES)

    @field_validator("log_text")
    @classmethod
    def validate_log_text(cls, value: str) -> str:
        return _validate_text_content(
            value,
            label="CI log",
            byte_limit=MAX_LOG_BYTES,
        )

    @model_validator(mode="after")
    def validate_file_set(self) -> "AnalyzeRequest":
        total_bytes = sum(len(item.content.encode("utf-8")) for item in self.files)
        if total_bytes > MAX_TOTAL_FILE_BYTES:
            raise ValueError("uploaded files exceed the combined UTF-8 byte limit")
        names = [item.name.casefold() for item in self.files]
        if len(names) != len(set(names)):
            raise ValueError("uploaded file names must be unique")
        return self

    def to_untrusted_context(self) -> str:
        parts = [
            '<CI_LOG source="ci.log">\n',
            self.log_text,
            "\n</CI_LOG>",
        ]
        for item in self.files:
            parts.extend(
                [
                    f'\n\n<UPLOADED_TEXT_FILE name="{item.name}">\n',
                    item.content,
                    "\n</UPLOADED_TEXT_FILE>",
                ]
            )
        return "".join(parts)


class SampleSummary(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=80)
    title: str = Field(min_length=1, max_length=120)
    category: Literal["Python", "TypeScript", "Docker"]
    description: str = Field(min_length=1, max_length=300)
    log_bytes: int = Field(ge=1)
    file_count: int = Field(ge=1, le=MAX_UPLOAD_FILES)


class SamplePayload(SampleSummary):
    log_text: str = Field(min_length=1, max_length=MAX_LOG_CHARACTERS)
    files: list[UploadedTextFile] = Field(min_length=1, max_length=MAX_UPLOAD_FILES)


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
    analysis_time_ms: int = Field(ge=0, le=3_600_000)


class SafeParitokStatsSnapshot(StrictModel):
    total_requests: int = Field(ge=0)
    input_tokens_original: int = Field(ge=0)
    input_tokens_compressed: int = Field(ge=0)
    compression_ratio: float = Field(ge=0)
    tokens_saved: int = Field(ge=0)
    tools_filtered: int = Field(ge=0)


class CapturedStatsDelta(StrictModel):
    proxy_requests: int = Field(ge=1, le=12)
    original_tokens: int = Field(gt=5_000)
    compressed_tokens: int = Field(ge=0)
    saved_tokens: int = Field(ge=0)
    compression_ratio: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_delta(self) -> "CapturedStatsDelta":
        if (
            self.compressed_tokens > self.original_tokens
            or self.saved_tokens != self.original_tokens - self.compressed_tokens
        ):
            raise ValueError("captured stats delta is internally inconsistent")
        expected_ratio = self.compressed_tokens / self.original_tokens
        if abs(self.compression_ratio - expected_ratio) > 0.000001:
            raise ValueError("captured compression ratio is inconsistent")
        return self


class GroundTruthCheck(StrictModel):
    expected_root_cause: NonEmptyText
    matching_relevant_files: list[FileNameText] = Field(min_length=1, max_length=20)


class CapturedSampleResult(StrictModel):
    schema_version: Literal[1]
    sample_id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=80)
    captured_at: datetime
    capture_kind: Literal["real_paritok_stats_delta"]
    screenshot_url: str = Field(
        pattern=r"^http://127\.0\.0\.1:5173/\?capture=[a-z0-9-]+$",
        max_length=180,
    )
    ground_truth_check: GroundTruthCheck
    stats_before: SafeParitokStatsSnapshot
    stats_after: SafeParitokStatsSnapshot
    stats_delta: CapturedStatsDelta
    analysis_result: AnalysisResult

    @model_validator(mode="after")
    def validate_capture_proof(self) -> "CapturedSampleResult":
        if not self.screenshot_url.endswith(self.sample_id):
            raise ValueError("capture URL does not match the sample")
        expected = (
            self.stats_after.total_requests - self.stats_before.total_requests,
            self.stats_after.input_tokens_original - self.stats_before.input_tokens_original,
            self.stats_after.input_tokens_compressed - self.stats_before.input_tokens_compressed,
            self.stats_after.tokens_saved - self.stats_before.tokens_saved,
        )
        actual = (
            self.stats_delta.proxy_requests,
            self.stats_delta.original_tokens,
            self.stats_delta.compressed_tokens,
            self.stats_delta.saved_tokens,
        )
        if expected != actual:
            raise ValueError("capture snapshots do not match the stored delta")
        stats = self.analysis_result.compression_stats
        if not stats.available:
            raise ValueError("capture analysis must contain verified compression stats")
        response = (
            stats.proxy_requests,
            stats.original_tokens,
            stats.compressed_tokens,
            stats.saved_tokens,
        )
        if response != actual:
            raise ValueError("capture analysis does not match the stored delta")
        return self


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
