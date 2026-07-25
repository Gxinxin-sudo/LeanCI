import pytest


@pytest.fixture
def anyio_backend() -> str:
    """Run async provider tests on the application's asyncio backend."""

    return "asyncio"
