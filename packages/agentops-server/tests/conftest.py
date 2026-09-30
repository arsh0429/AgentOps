"""Server-side test fixtures.

Mirrors the agentops-py conftest.py: reset the global eval registry between
tests so that re-imports / module reloads don't trigger double-registration
collisions when a test imports the orchestrator (which in turn imports the
eval templates).
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_eval_registry() -> None:
    try:
        from agentops.eval import registry
        registry.reset_for_tests()
    except ImportError:
        pass
    yield
