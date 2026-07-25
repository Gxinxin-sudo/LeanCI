"""Verify Paritok proxy, hosted GPU, and safe cumulative stats without an LLM call."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import DEFAULT_DEEPSEEK_MODEL, Settings
from app.paritok import ParitokClient, ParitokClientError


def emit(payload: dict[str, Any]) -> None:
    """Print one bounded JSON object without secrets or Paritok dollar estimates."""

    print(json.dumps(payload, ensure_ascii=False))


async def run() -> int:
    try:
        settings = Settings()
    except ValidationError:
        emit(
            {
                "status": "failed:INVALID_CONFIGURATION",
                "model": DEFAULT_DEEPSEEK_MODEL,
                "proxy": None,
                "hosted_gpu": None,
                "stats": None,
            }
        )
        return 1

    if not settings.paritok_api_key_configured:
        emit(
            {
                "status": "skipped",
                "model": settings.deepseek_model,
                "proxy": None,
                "hosted_gpu": None,
                "stats": None,
            }
        )
        return 0

    client = ParitokClient(settings)
    try:
        health = await client.health()
        gpu = await client.hosted_gpu()
        stats = await client.stats()
    except ParitokClientError as exc:
        emit(
            {
                "status": f"failed:{exc.code}",
                "model": settings.deepseek_model,
                "proxy": None,
                "hosted_gpu": None,
                "stats": None,
            }
        )
        return 1
    except Exception:  # noqa: BLE001 - never emit a secret-bearing CLI traceback
        emit(
            {
                "status": "failed:PARITOK_CONNECTION_TEST_ERROR",
                "model": settings.deepseek_model,
                "proxy": None,
                "hosted_gpu": None,
                "stats": None,
            }
        )
        return 1
    finally:
        await client.aclose()

    emit(
        {
            "status": "success",
            "model": settings.deepseek_model,
            "proxy": {"status": health.status, "version": health.version},
            "hosted_gpu": {"available": gpu.gpu_available},
            "stats": stats.to_public().model_dump(),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
