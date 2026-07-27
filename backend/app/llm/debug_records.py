"""Privacy-preserving records for invalid structured model responses."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

InvalidAttempt = Literal["initial", "repair"]


def save_invalid_response_record(
    directory: Path,
    *,
    provider: str,
    model: str,
    attempt: InvalidAttempt,
    reason: str,
    completion: Any,
    content: str,
) -> None:
    """Persist metadata that cannot reconstruct model or user content.

    Debugging records deliberately contain only stable classification and
    one-way measurements. A failure to write diagnostics never changes the
    public provider error or triggers another model request.
    """

    choices = getattr(completion, "choices", None)
    finish_reason = getattr(choices[0], "finish_reason", None) if choices else None
    content_bytes = content.encode("utf-8")
    payload = {
        "schema_version": 1,
        "captured_at": datetime.now(UTC).isoformat(),
        "provider": provider,
        "model": model,
        "attempt": attempt,
        "reason": reason,
        "choice_count": len(choices) if isinstance(choices, (list, tuple)) else 0,
        "finish_reason": (finish_reason if isinstance(finish_reason, str) else None),
        "content_characters": len(content),
        "content_bytes": len(content_bytes),
        "content_sha256": hashlib.sha256(content_bytes).hexdigest(),
        "content_saved": False,
    }

    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        filename = f"invalid-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex}.json"
        path = directory / filename
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=True, separators=(",", ":"))
            handle.write("\n")
    except OSError:
        return
