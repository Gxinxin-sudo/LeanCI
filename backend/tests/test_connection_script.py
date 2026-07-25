import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "test_deepseek_connection.py"
PARITOK_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "test_paritok_connection.py"
LONG_REQUEST_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "verify_paritok_long_request.py"
PARITOK_START_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "start_paritok.ps1"


def run_script_with_environment(**overrides: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(overrides)
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )


def run_paritok_script_with_environment(
    **overrides: str,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(overrides)
    return subprocess.run(
        [sys.executable, str(PARITOK_SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )


def test_connection_script_safely_skips_without_key() -> None:
    result = run_script_with_environment(DEEPSEEK_API_KEY="")
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert result.stderr == ""
    assert payload == {
        "status": "skipped",
        "model": "deepseek-v4-flash",
        "usage": None,
    }


def test_connection_script_hides_invalid_configuration_details() -> None:
    result = run_script_with_environment(
        DEEPSEEK_API_KEY="",
        DEEPSEEK_MODEL="deepseek-chat",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert result.stderr == ""
    assert payload == {
        "status": "failed:INVALID_CONFIGURATION",
        "model": "deepseek-v4-flash",
        "usage": None,
    }


def test_paritok_connection_script_safely_skips_without_key() -> None:
    result = run_paritok_script_with_environment(PARITOK_API_KEY="")
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert result.stderr == ""
    assert payload == {
        "status": "skipped",
        "model": "deepseek-v4-flash",
        "proxy": None,
        "hosted_gpu": None,
        "stats": None,
    }


def test_paritok_connection_script_hides_invalid_configuration_details() -> None:
    result = run_paritok_script_with_environment(
        PARITOK_API_KEY="",
        PARITOK_STATS_URL="https://example.com/stats",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert result.stderr == ""
    assert payload == {
        "status": "failed:INVALID_CONFIGURATION",
        "model": "deepseek-v4-flash",
        "proxy": None,
        "hosted_gpu": None,
        "stats": None,
    }


def test_paritok_start_script_fails_closed_before_launching_proxy() -> None:
    script = PARITOK_START_SCRIPT_PATH.read_text(encoding="utf-8")

    preflight = script.index("Invoke-RestMethod")
    proxy_launch = script.index("& $ParitokExecutable proxy")
    assert preflight < proxy_launch
    assert "$GpuStatus.gpu_available -ne $true" in script
    assert "The local Proxy was not started." in script


def test_long_request_script_requires_explicit_cost_confirmation() -> None:
    result = subprocess.run(
        [sys.executable, str(LONG_REQUEST_SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert result.stderr == ""
    assert payload == {
        "status": "skipped:COST_CONFIRMATION_REQUIRED",
        "model": "deepseek-v4-flash",
        "compression_stats": None,
    }
