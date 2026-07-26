"""Run one fixed LeanCI benchmark pair with explicit paid-call consent."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.benchmark import (
    CASE_IDS,
    RESULTS_JSON_PATH,
    BenchmarkRunner,
    build_artifact,
    load_results,
    merge_case_rows,
    write_artifacts,
)
from app.config import Settings
from app.paritok import ParitokClient


def emit(value: dict[str, object]) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


async def run_case(case_id: str) -> int:
    settings = Settings()
    client = ParitokClient(settings)
    try:
        runner = BenchmarkRunner(settings, client)
        case_rows = await runner.run_case(case_id)
    finally:
        await client.aclose()

    existing = load_results() if RESULTS_JSON_PATH.is_file() else None
    artifact = build_artifact(settings, merge_case_rows(existing, case_rows))
    write_artifacts(artifact)
    emit(
        {
            "status": (
                "completed"
                if all(row.status != "failed" for row in case_rows)
                else "completed_with_failure"
            ),
            "case_id": case_id,
            "rows_written": len(case_rows),
            "successful_rows": sum(row.status == "success" for row in case_rows),
            "compression_skipped_rows": sum(
                row.status == "compression_skipped" for row in case_rows
            ),
            "failed_rows": sum(row.status == "failed" for row in case_rows),
            "finalized": artifact.finalized,
            "expected_model_api_requests": 2,
            "maximum_model_api_requests_with_json_repairs": 4,
            "network_retries": 0,
        }
    )
    return 0 if all(row.status != "failed" for row in case_rows) else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one fixed case in baseline_uncompressed then Paritok mode. "
            "The command never accepts arbitrary logs or paths."
        )
    )
    parser.add_argument("--case", choices=CASE_IDS, required=True)
    parser.add_argument(
        "--confirm-cost",
        action="store_true",
        help=(
            "Permit two expected DeepSeek calls for this case, with at most one JSON "
            "repair per mode (four calls maximum) and zero network retries."
        ),
    )
    args = parser.parse_args()
    if not args.confirm_cost:
        emit(
            {
                "status": "skipped:COST_CONFIRMATION_REQUIRED",
                "case_id": args.case,
                "model_api_requests": 0,
                "rows_written": 0,
            }
        )
        return 0
    return asyncio.run(run_case(args.case))


if __name__ == "__main__":
    raise SystemExit(main())
