"""Record a bounded benchmark preflight failure without making model calls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.benchmark import build_artifact, build_preflight_failure_rows, write_artifacts
from app.config import Settings

PUBLIC_FAILURES = {
    "PARITOK_GPU_UNAVAILABLE": (
        "PREFLIGHT_FAILED: PARITOK_GPU_UNAVAILABLE: The Paritok hosted GPU was "
        "unavailable after the bounded preflight; no DeepSeek request was sent."
    ),
    "PARITOK_AUTHENTICATION_FAILED": (
        "PREFLIGHT_FAILED: PARITOK_AUTHENTICATION_FAILED: The hosted service rejected "
        "the configured credential; no DeepSeek request was sent."
    ),
    "PARITOK_UNAVAILABLE": (
        "PREFLIGHT_FAILED: PARITOK_UNAVAILABLE: The local Paritok Proxy was unavailable; "
        "no DeepSeek request was sent."
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Persist every planned benchmark row after an already-observed bounded "
            "preflight failure. This command performs no network or model calls."
        )
    )
    parser.add_argument("--code", choices=tuple(PUBLIC_FAILURES), required=True)
    args = parser.parse_args()

    settings = Settings()
    rows = build_preflight_failure_rows(settings, error=PUBLIC_FAILURES[args.code])
    artifact = build_artifact(settings, rows)
    write_artifacts(artifact)
    print(
        json.dumps(
            {
                "status": "recorded_preflight_failure",
                "code": args.code,
                "rows_written": len(rows),
                "model_api_requests": 0,
                "finalized": artifact.finalized,
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
