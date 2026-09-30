import pytest


def test_module_imports() -> None:
    """Smoke check that the example module is importable (no syntax errors,
    all imports resolve). Doesn't run the agent."""
    from agentops_sdk_example import example  # noqa: F401
    assert hasattr(example, "run")
    assert callable(example.run)

@pytest.mark.live
async def test_bare_example_returns_text() -> None:
    from agentops_sdk_example.example import run
    out = await run("a small test interest")
    assert isinstance(out, str)
    assert out
