
from src.retry import RetryPolicy


def test_zero_attempt_uses_base_delay() -> None:
    assert RetryPolicy(base_delay=2, max_delay=16).delay_for(attempt=0) == 1


def test_retry_backoff_caps_at_maximum() -> None:
    policy = RetryPolicy(base_delay=2, max_delay=16)
    assert policy.delay_for(attempt=4) == 16
