import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.scan_secrets import detector_names  # noqa: E402


def test_secret_detectors_return_labels_without_matched_values() -> None:
    fake_value = "sk-" + ("A1" * 16)
    generic_value = "B7" * 16

    assert detector_names(f"token={fake_value}") == {"openai_style_key"}
    assert detector_names(f"DEEPSEEK_API_KEY={generic_value}") == {"high_entropy_secret_assignment"}


def test_repository_and_complete_history_pass_the_redacted_secret_scan() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/scan_secrets.py"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert payload["status"] == "passed"
    assert payload["scanned_commits"] >= 1
    assert payload["skipped_oversized_files"] == []
    assert payload["findings"] == []
