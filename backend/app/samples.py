"""Fixed bundled demo samples; no caller-controlled filesystem paths are accepted."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.models import CapturedSampleResult, SamplePayload, SampleSummary, UploadedTextFile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLES_ROOT = PROJECT_ROOT / "examples"


@dataclass(frozen=True)
class SampleDefinition:
    id: str
    title: str
    category: Literal["Python", "TypeScript", "Docker"]
    description: str
    directory: str
    files: tuple[str, ...]


SAMPLE_DEFINITIONS = (
    SampleDefinition(
        id="python-pytest",
        title="Python pytest failure",
        category="Python",
        description="A deterministic retry-backoff assertion failure with a precedence bug.",
        directory="python-pytest",
        files=("src/retry.py", "tests/test_retry.py", "pyproject.toml"),
    ),
    SampleDefinition(
        id="typescript-build",
        title="TypeScript build failure",
        category="TypeScript",
        description="A strict TypeScript build catches an unchecked optional environment value.",
        directory="typescript-build",
        files=("src/config.ts", "src/deploy.ts", "tsconfig.json"),
    ),
    SampleDefinition(
        id="docker-build",
        title="Docker build failure",
        category="Docker",
        description="BuildKit cannot copy package manifests excluded by an over-broad ignore rule.",
        directory="docker-build",
        files=("Dockerfile", ".dockerignore", "package.json"),
    ),
)
_SAMPLES_BY_ID = {sample.id: sample for sample in SAMPLE_DEFINITIONS}


class SampleNotFoundError(LookupError):
    """Raised when a sample identifier is not one of the fixed definitions."""


class SampleCaptureNotFoundError(LookupError):
    """Raised when a fixed sample has not yet been captured through the real route."""


def _definition(sample_id: str) -> SampleDefinition:
    try:
        return _SAMPLES_BY_ID[sample_id]
    except KeyError as exc:
        raise SampleNotFoundError(sample_id) from exc


def _sample_root(definition: SampleDefinition) -> Path:
    root = (SAMPLES_ROOT / definition.directory).resolve()
    if root.parent != SAMPLES_ROOT.resolve():
        raise RuntimeError("Bundled sample definition escaped the examples directory.")
    return root


def load_sample(sample_id: str) -> SamplePayload:
    definition = _definition(sample_id)
    root = _sample_root(definition)
    log_text = (root / "ci.log").read_text(encoding="utf-8")
    files = [
        UploadedTextFile(
            name=Path(relative_path).name,
            content=(root / relative_path).read_text(encoding="utf-8"),
        )
        for relative_path in definition.files
    ]
    return SamplePayload(
        id=definition.id,
        title=definition.title,
        category=definition.category,
        description=definition.description,
        log_bytes=len(log_text.encode("utf-8")),
        file_count=len(files),
        log_text=log_text,
        files=files,
    )


def list_samples() -> list[SampleSummary]:
    summaries: list[SampleSummary] = []
    for definition in SAMPLE_DEFINITIONS:
        payload = load_sample(definition.id)
        summaries.append(SampleSummary(**payload.model_dump(exclude={"log_text", "files"})))
    return summaries


def load_ground_truth(sample_id: str) -> dict[str, object]:
    """Load a fixed evaluation asset for tests and the explicit demo runner only."""

    definition = _definition(sample_id)
    path = _sample_root(definition) / "ground_truth.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("ground_truth.json must contain an object")
    return value


def load_sample_capture(sample_id: str) -> CapturedSampleResult:
    """Load a saved real-run response for screenshots, never as live telemetry."""

    definition = _definition(sample_id)
    path = _sample_root(definition) / "demo_result.json"
    if not path.is_file():
        raise SampleCaptureNotFoundError(sample_id)
    return CapturedSampleResult.model_validate_json(path.read_text(encoding="utf-8"))
