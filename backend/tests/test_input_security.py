import pytest
from pydantic import ValidationError

from app.models import (
    MAX_FILE_BYTES,
    MAX_LOG_BYTES,
    MAX_TOTAL_FILE_BYTES,
    AnalyzeRequest,
)


def test_rejects_more_than_five_files() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(
            log_text="failed",
            files=[{"name": f"file-{index}.txt", "content": "text"} for index in range(6)],
        )


@pytest.mark.parametrize(
    "name",
    [
        "../secret.txt",
        "..\\secret.txt",
        "C:\\secret.txt",
        "archive.zip",
        "bundle.tar.gz",
        "image.png",
        "report.pdf",
        "fake.py.exe",
        "run.exe",
        "script.ps1",
        "script.sh",
    ],
)
def test_rejects_paths_archives_executables_and_non_allowlisted_files(name: str) -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(
            log_text="failed",
            files=[{"name": name, "content": "safe text"}],
        )


def test_normalizes_safe_filename_and_accepts_docker_inputs() -> None:
    request = AnalyzeRequest(
        log_text="failed",
        files=[
            {"name": " retry config.py ", "content": "retries = 3"},
            {"name": "Dockerfile", "content": "FROM python:3.12-slim"},
            {"name": ".dockerignore", "content": "*.log"},
        ],
    )

    assert [item.name for item in request.files] == [
        "retry_config.py",
        "Dockerfile",
        ".dockerignore",
    ]


@pytest.mark.parametrize(
    "name",
    [
        "..／secret.txt",
        "C：secret.txt",
        "CON.txt",
        "nul.log",
        "name\u202etxt.exe",
    ],
)
def test_rejects_unicode_path_confusables_reserved_names_and_bidi_controls(
    name: str,
) -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(
            log_text="failed",
            files=[{"name": name, "content": "safe text"}],
        )


def test_rejects_duplicate_names_after_safe_normalization() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(
            log_text="failed",
            files=[
                {"name": "retry config.py", "content": "first"},
                {"name": "retry?config.py", "content": "second"},
            ],
        )


@pytest.mark.parametrize("content", ["binary\x00data", "bell\x07data"])
def test_rejects_binary_and_control_characters(content: str) -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(log_text="failed", files=[{"name": "failure.log", "content": content}])


def test_rejects_oversized_single_file() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(
            log_text="failed",
            files=[{"name": "failure.log", "content": "x" * (MAX_FILE_BYTES + 1)}],
        )


def test_rejects_oversized_combined_files() -> None:
    chunk = "x" * (MAX_TOTAL_FILE_BYTES // 5 + 1)
    with pytest.raises(ValidationError):
        AnalyzeRequest(
            log_text="failed",
            files=[{"name": f"failure-{index}.log", "content": chunk} for index in range(5)],
        )


def test_rejects_log_over_utf8_byte_limit() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(log_text="€" * (MAX_LOG_BYTES // 3 + 1))
