"""Send one explicitly approved long formal request and verify Paritok metrics."""

import argparse
import json
from typing import Any

import httpx

ANALYZE_URL = "http://127.0.0.1:8000/api/analyze"
MINIMUM_ORIGINAL_TOKENS = 5_000


def build_long_log() -> str:
    """Build bounded inert CI evidence that should comfortably exceed 5,000 Token."""

    return "".join(
        (
            f"step {index:04d}: compiler error TS2345: undefined is not assignable "
            "to the required string configuration value.\n"
        )
        for index in range(1_100)
    )


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one real, billable LeanCI analysis and verify that Paritok reported "
            "more than 5,000 original Token."
        )
    )
    parser.add_argument(
        "--confirm-cost",
        action="store_true",
        help="Explicitly permit one real Paritok/DeepSeek request.",
    )
    args = parser.parse_args()

    if not args.confirm_cost:
        emit(
            {
                "status": "skipped:COST_CONFIRMATION_REQUIRED",
                "model": "deepseek-v4-flash",
                "compression_stats": None,
            }
        )
        return 0

    try:
        response = httpx.post(
            ANALYZE_URL,
            json={"log_text": build_long_log()},
            timeout=httpx.Timeout(180.0, connect=5.0),
        )
    except httpx.HTTPError:
        emit(
            {
                "status": "failed:LEANCI_API_UNAVAILABLE",
                "model": "deepseek-v4-flash",
                "compression_stats": None,
            }
        )
        return 1
    except Exception:  # noqa: BLE001 - never emit a local traceback from this verifier
        emit(
            {
                "status": "failed:LEANCI_VERIFICATION_ERROR",
                "model": "deepseek-v4-flash",
                "compression_stats": None,
            }
        )
        return 1

    try:
        payload = response.json()
    except ValueError:
        emit(
            {
                "status": "failed:LEANCI_INVALID_RESPONSE",
                "model": "deepseek-v4-flash",
                "compression_stats": None,
            }
        )
        return 1

    if response.status_code != 200:
        error = payload.get("error") if isinstance(payload, dict) else None
        safe_code = (
            error.get("code") if isinstance(error, dict) else "LEANCI_ANALYSIS_FAILED"
        )
        emit(
            {
                "status": f"failed:{safe_code}",
                "model": "deepseek-v4-flash",
                "compression_stats": None,
            }
        )
        return 1

    stats = payload.get("compression_stats") if isinstance(payload, dict) else None
    if (
        not isinstance(stats, dict)
        or stats.get("available") is not True
        or not isinstance(stats.get("original_tokens"), int)
        or stats["original_tokens"] <= MINIMUM_ORIGINAL_TOKENS
    ):
        emit(
            {
                "status": "failed:PARITOK_LONG_REQUEST_NOT_VERIFIED",
                "model": "deepseek-v4-flash",
                "compression_stats": None,
            }
        )
        return 1

    safe_keys = (
        "verification",
        "proxy_version",
        "model",
        "proxy_requests",
        "original_tokens",
        "compressed_tokens",
        "saved_tokens",
        "compression_ratio",
        "cumulative",
        "cost_estimate",
    )
    if any(key not in stats for key in safe_keys):
        emit(
            {
                "status": "failed:LEANCI_INVALID_RESPONSE",
                "model": "deepseek-v4-flash",
                "compression_stats": None,
            }
        )
        return 1
    safe_stats = {key: stats[key] for key in safe_keys}
    emit(
        {
            "status": "success",
            "model": "deepseek-v4-flash",
            "compression_stats": safe_stats,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
