"""Scan the current Git tree and every commit without printing matched values."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMMAND_TIMEOUT_SECONDS = 30
MAX_SCANNED_FILE_BYTES = 25 * 1024 * 1024

_HIGH_CONFIDENCE_PATTERNS = (
    (
        "openai_style_key",
        re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}"),
    ),
    (
        "github_token",
        re.compile(
            r"(?<![A-Za-z0-9])(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,})"
        ),
    ),
    (
        "aws_access_key",
        re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"),
    ),
    (
        "google_api_key",
        re.compile(r"(?<![A-Za-z0-9])AIza[0-9A-Za-z_-]{35}(?![A-Za-z0-9_-])"),
    ),
    (
        "slack_token",
        re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[0-9A-Za-z-]{10,}"),
    ),
    (
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
)
_GENERIC_ASSIGNMENT = re.compile(
    r"""(?ix)
    (?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|private[_-]?key)
    \s*[:=]\s*["']?
    ([A-Za-z0-9_+/=-]{20,})
    """
)


@dataclass(frozen=True)
class Finding:
    scope: str
    detector: str
    path: str
    commit: str | None = None
    line: int | None = None


def detector_names(text: str) -> set[str]:
    """Return detector labels only, never the secret-like matched value."""

    names = {
        name
        for name, pattern in _HIGH_CONFIDENCE_PATTERNS
        if pattern.search(text) is not None
    }
    for match in _GENERIC_ASSIGNMENT.finditer(text):
        value = match.group(1)
        if any(character.isalpha() for character in value) and any(
            character.isdigit() for character in value
        ):
            names.add("high_entropy_secret_assignment")
    return names


def _git(*arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    return completed.stdout


def _current_findings() -> tuple[list[Finding], int, list[str]]:
    paths = [
        item.decode("utf-8", errors="surrogateescape")
        for item in _git("ls-files", "-co", "--exclude-standard", "-z").split(b"\0")
        if item
    ]
    findings: list[Finding] = []
    skipped: list[str] = []
    scanned = 0
    for relative_path in paths:
        path = PROJECT_ROOT / relative_path
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_SCANNED_FILE_BYTES:
            skipped.append(relative_path)
            continue
        try:
            lines = path.read_bytes().decode("latin-1").splitlines()
        except OSError:
            continue
        scanned += 1
        for line_number, line in enumerate(lines, start=1):
            findings.extend(
                Finding(
                    scope="current",
                    detector=detector,
                    path=relative_path,
                    line=line_number,
                )
                for detector in detector_names(line)
            )
    return findings, scanned, skipped


def _history_findings() -> tuple[list[Finding], int]:
    history = _git(
        "log",
        "--all",
        "--format=@@LEANCICOMMIT:%H",
        "-p",
        "--full-history",
        "--no-color",
        "--no-ext-diff",
    ).decode("latin-1")
    current_commit: str | None = None
    current_path = "unknown"
    findings: list[Finding] = []
    commits: set[str] = set()
    for line in history.splitlines():
        if line.startswith("@@LEANCICOMMIT:"):
            current_commit = line.removeprefix("@@LEANCICOMMIT:")
            commits.add(current_commit)
            continue
        diff_match = re.match(r"^diff --git a/(.+) b/(.+)$", line)
        if diff_match:
            current_path = diff_match.group(2)
            continue
        if not line.startswith(("+", "-")) or line.startswith(("+++ ", "--- ")):
            continue
        findings.extend(
            Finding(
                scope="history",
                detector=detector,
                path=current_path,
                commit=current_commit,
            )
            for detector in detector_names(line[1:])
        )
    return findings, len(commits)


def main() -> int:
    try:
        current, scanned_files, skipped_files = _current_findings()
        history, scanned_commits = _history_findings()
    except (OSError, subprocess.SubprocessError):
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "Secret scan could not complete its fixed local Git checks.",
                },
                separators=(",", ":"),
            )
        )
        return 2

    unique = {
        (item.scope, item.detector, item.path, item.commit, item.line): item
        for item in [*current, *history]
    }
    findings = [
        asdict(item)
        for item in sorted(
            unique.values(),
            key=lambda item: (
                item.scope,
                item.path,
                item.commit or "",
                item.line or 0,
                item.detector,
            ),
        )
    ]
    status = "failed" if findings or skipped_files else "passed"
    print(
        json.dumps(
            {
                "status": status,
                "scanned_current_files": scanned_files,
                "scanned_commits": scanned_commits,
                "skipped_oversized_files": skipped_files,
                "findings": findings,
            },
            separators=(",", ":"),
        )
    )
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
