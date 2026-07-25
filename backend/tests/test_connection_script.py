import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "test_deepseek_connection.py"


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
