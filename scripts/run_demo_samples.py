"""Run the three fixed samples through the real API and save verified capture state."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_IDS = ("python-pytest", "typescript-build", "docker-build")
API_BASE = "http://127.0.0.1:8000/api"
STATS_URL = "http://127.0.0.1:8080/stats"
MINIMUM_ORIGINAL_TOKENS = 5_000
SAFE_STATS_KEYS = (
    "total_requests",
    "input_tokens_original",
    "input_tokens_compressed",
    "compression_ratio",
    "tokens_saved",
    "tools_filtered",
)


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False))


def safe_http_error(response: httpx.Response) -> dict[str, str]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    if not isinstance(payload, dict) or not isinstance(payload.get("error"), dict):
        return {}
    error = payload["error"]
    result: dict[str, str] = {}
    if isinstance(error.get("code"), str):
        result["error_code"] = error["code"]
    if isinstance(error.get("message"), str):
        result["error_message"] = error["message"]
    return result


def safe_stats(value: object) -> dict[str, int | float]:
    if not isinstance(value, dict):
        raise TypeError("stats payload is not an object")
    result: dict[str, int | float] = {}
    for key in SAFE_STATS_KEYS:
        item = value.get(key)
        if key == "compression_ratio":
            if not isinstance(item, int | float) or isinstance(item, bool):
                raise TypeError(f"stats field {key} is invalid")
            result[key] = float(item)
        else:
            if not isinstance(item, int) or isinstance(item, bool):
                raise TypeError(f"stats field {key} is invalid")
            result[key] = item
    return result


def stats_delta(
    before: dict[str, int | float],
    after: dict[str, int | float],
) -> dict[str, int | float]:
    original = int(after["input_tokens_original"] - before["input_tokens_original"])
    compressed = int(
        after["input_tokens_compressed"] - before["input_tokens_compressed"]
    )
    saved = int(after["tokens_saved"] - before["tokens_saved"])
    requests = int(after["total_requests"] - before["total_requests"])
    if (
        min(original, compressed, saved, requests) < 0
        or compressed > original
        or saved != original - compressed
    ):
        raise ValueError("stats delta is invalid")
    return {
        "proxy_requests": requests,
        "original_tokens": original,
        "compressed_tokens": compressed,
        "saved_tokens": saved,
        "compression_ratio": round(compressed / original, 6) if original else 0.0,
    }


def validate_result(
    sample_id: str,
    result: object,
    delta: dict[str, int | float],
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(result, dict):
        raise TypeError("analysis response is not an object")
    compression = result.get("compression_stats")
    if not isinstance(compression, dict) or compression.get("available") is not True:
        raise ValueError("analysis response has no verified compression stats")
    if compression.get("model") != "deepseek-v4-flash":
        raise ValueError("analysis response used an unexpected model")
    for result_key, delta_key in (
        ("proxy_requests", "proxy_requests"),
        ("original_tokens", "original_tokens"),
        ("compressed_tokens", "compressed_tokens"),
        ("saved_tokens", "saved_tokens"),
    ):
        if compression.get(result_key) != delta[delta_key]:
            raise ValueError(
                f"analysis {result_key} does not match outer stats snapshots"
            )
    if int(delta["original_tokens"]) <= MINIMUM_ORIGINAL_TOKENS:
        raise ValueError("sample did not exceed the 5,000 original Token requirement")

    truth_path = PROJECT_ROOT / "examples" / sample_id / "ground_truth.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    expected_files = {
        str(item).casefold() for item in truth.get("expected_relevant_files", [])
    }
    required_files = {
        str(item).casefold() for item in truth.get("required_relevant_files", [])
    }
    actual_files = {
        Path(str(item)).name.casefold() for item in result.get("relevant_files", [])
    }
    matches = sorted(expected_files.intersection(actual_files))
    if not matches:
        raise ValueError("analysis did not identify any ground-truth relevant file")
    if not required_files.issubset(actual_files):
        raise ValueError("analysis omitted a required ground-truth relevant file")

    answer_text = " ".join(
        [
            str(result.get("root_cause", "")),
            *[str(item) for item in result.get("recommended_changes", [])],
            str(result.get("patch", "")),
        ]
    ).casefold()
    required_terms = [
        str(item).casefold() for item in truth.get("required_answer_terms", [])
    ]
    if any(term not in answer_text for term in required_terms):
        raise ValueError("analysis omitted a required ground-truth root-cause term")
    return truth, matches


def capture_sample(client: httpx.Client, sample_id: str) -> dict[str, Any]:
    sample_response = client.get(f"{API_BASE}/samples/{sample_id}")
    sample_response.raise_for_status()
    sample = sample_response.json()

    before_response = client.get(STATS_URL)
    before_response.raise_for_status()
    before = safe_stats(before_response.json())

    analysis_response = client.post(
        f"{API_BASE}/analyze",
        json={"log_text": sample["log_text"], "files": sample["files"]},
    )
    analysis_response.raise_for_status()
    analysis = analysis_response.json()

    after_response = client.get(STATS_URL)
    after_response.raise_for_status()
    after = safe_stats(after_response.json())
    delta = stats_delta(before, after)
    truth, matching_files = validate_result(sample_id, analysis, delta)

    captured_at = datetime.now(UTC).isoformat()
    capture = {
        "schema_version": 1,
        "sample_id": sample_id,
        "captured_at": captured_at,
        "capture_kind": "real_paritok_stats_delta",
        "screenshot_url": f"http://127.0.0.1:5173/?capture={sample_id}",
        "ground_truth_check": {
            "expected_root_cause": truth["root_cause"],
            "matching_relevant_files": matching_files,
        },
        "stats_before": before,
        "stats_after": after,
        "stats_delta": delta,
        "analysis_result": analysis,
    }
    output_path = PROJECT_ROOT / "examples" / sample_id / "demo_result.json"
    output_path.write_text(
        json.dumps(capture, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "sample_id": sample_id,
        "status": "success",
        "captured_at": captured_at,
        "original_tokens": delta["original_tokens"],
        "compressed_tokens": delta["compressed_tokens"],
        "saved_tokens": delta["saved_tokens"],
        "output": str(output_path.relative_to(PROJECT_ROOT)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run fixed samples through FastAPI -> Paritok -> DeepSeek and "
            "save their real stats snapshots."
        )
    )
    parser.add_argument(
        "--confirm-cost",
        action="store_true",
        help="Explicitly permit three real Paritok/DeepSeek requests.",
    )
    parser.add_argument(
        "--sample",
        choices=SAMPLE_IDS,
        help="Run exactly one fixed sample so each paid call has its own timeout.",
    )
    args = parser.parse_args()
    sample_ids = (args.sample,) if args.sample else SAMPLE_IDS
    if not args.confirm_cost:
        emit(
            {
                "status": "skipped:COST_CONFIRMATION_REQUIRED",
                "sample_count": len(sample_ids),
                "captures_written": 0,
            }
        )
        return 0

    timeout = httpx.Timeout(110.0, connect=5.0)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            for sample_id in sample_ids:
                emit(capture_sample(client, sample_id))
    except httpx.HTTPStatusError as exc:
        emit(
            {
                "status": "failed:HTTP_ERROR",
                "http_status": exc.response.status_code,
                **safe_http_error(exc.response),
                "captures_written": sum(
                    (PROJECT_ROOT / "examples" / item / "demo_result.json").is_file()
                    for item in sample_ids
                ),
            }
        )
        return 1
    except httpx.HTTPError:
        emit(
            {
                "status": "failed:DEMO_CAPTURE_TRANSPORT",
                "captures_written": sum(
                    (PROJECT_ROOT / "examples" / item / "demo_result.json").is_file()
                    for item in sample_ids
                ),
            }
        )
        return 1
    except (KeyError, TypeError, ValueError) as exc:
        emit(
            {
                "status": "failed:DEMO_CAPTURE_VALIDATION",
                "validation_error": str(exc),
                "captures_written": sum(
                    (PROJECT_ROOT / "examples" / item / "demo_result.json").is_file()
                    for item in sample_ids
                ),
            }
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
