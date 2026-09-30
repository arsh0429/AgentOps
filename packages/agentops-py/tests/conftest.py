import pytest


@pytest.fixture(autouse=True)
def _reset_eval_registry() -> None:
    """Reset the eval registry before every test in agentops-py to avoid cross-test bleed."""
    try:
        from agentops.eval import registry
        registry.reset_for_tests()
    except ImportError:
        pass
    yield
