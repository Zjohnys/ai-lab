import pytest


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio only (the anyio plugin would also try trio)."""
    return "asyncio"
