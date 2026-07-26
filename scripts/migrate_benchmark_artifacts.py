"""Migrate the saved phase-five artifact without any network or model request."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.benchmark import load_results, write_artifacts


def main() -> int:
    artifact = load_results()
    write_artifacts(artifact)
    print(
        "status=migrated_offline "
        f"schema_version={artifact.schema_version} "
        f"rows={len(artifact.rows)} model_api_requests=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
