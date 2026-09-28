import pytest


@pytest.fixture
def anyio_backend() -> str:
    """Run `@pytest.mark.anyio` tests on asyncio only (the app's event loop)."""
    return "asyncio"
