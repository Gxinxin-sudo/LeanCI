import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_demo_runner_requires_explicit_cost_confirmation() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/run_demo_samples.py"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert payload == {
        "status": "skipped:COST_CONFIRMATION_REQUIRED",
        "sample_count": 3,
        "captures_written": 0,
    }


def test_demo_runner_can_select_one_sample_without_making_a_request() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_demo_samples.py",
            "--sample",
            "python-pytest",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert payload == {
        "status": "skipped:COST_CONFIRMATION_REQUIRED",
        "sample_count": 1,
        "captures_written": 0,
    }
