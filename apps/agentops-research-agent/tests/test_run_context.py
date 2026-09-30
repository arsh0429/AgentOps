import asyncio

import pytest
from agentops_research_agent import tools
from agentops_research_agent.run_context import (
    bind_run_context,
    current_run_context,
    get_run_figures,
    record_run_figures,
    reset_run_context,
)


def test_each_binding_gets_fresh_state_even_for_the_same_run_id() -> None:
    first_token = bind_run_context("run-reused")
    try:
        record_run_figures("paper-a", [{"caption": "first"}])
        assert set(get_run_figures()) == {"paper-a"}
    finally:
        reset_run_context(first_token)

    second_token = bind_run_context("run-reused")
    try:
        assert get_run_figures() == {}
        context = current_run_context()
        assert context is not None
        assert context.run_id == "run-reused"
    finally:
        reset_run_context(second_token)

    assert current_run_context() is None


def test_figure_snapshots_cannot_mutate_the_bound_context() -> None:
    token = bind_run_context("run-snapshot")
    try:
        record_run_figures("paper-a", [{"caption": "original"}])
        snapshot = get_run_figures()
        snapshot["paper-a"][0]["caption"] = "changed"
        snapshot["paper-b"] = []

        assert get_run_figures() == {"paper-a": [{"caption": "original"}]}
    finally:
        reset_run_context(token)


@pytest.mark.asyncio
async def test_concurrent_tool_calls_keep_figures_in_their_own_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered: set[str] = set()
    both_entered = asyncio.Event()

    async def overlapping_vision(*_args: object, **_kwargs: object) -> str:
        context = current_run_context()
        assert context is not None
        entered.add(context.run_id)
        if len(entered) == 2:
            both_entered.set()
        await asyncio.wait_for(both_entered.wait(), timeout=1)
        await asyncio.sleep(0)
        return f"description-for-{context.run_id}"

    monkeypatch.setattr(tools.llm, "vision", overlapping_vision)

    async def extract_for(run_id: str, paper_id: str) -> dict[str, list[dict]]:
        token = bind_run_context(run_id)
        try:
            await tools.extract_figures(paper_id)
            context = current_run_context()
            assert context is not None
            assert context.run_id == run_id
            return get_run_figures()
        finally:
            reset_run_context(token)

    first, second = await asyncio.gather(
        extract_for("run-a", "2401.00001"),
        extract_for("run-b", "2402.00012"),
    )

    assert set(first) == {"2401.00001"}
    assert set(second) == {"2402.00012"}
    assert first["2401.00001"][0]["description"] == "description-for-run-a"
    assert second["2402.00012"][0]["description"] == "description-for-run-b"
    assert current_run_context() is None


def test_worker_fallback_does_not_replace_deterministic_tool_figures() -> None:
    token = bind_run_context("run-precedence")
    try:
        record_run_figures(
            "paper-a",
            [{"caption": "tool", "filename": "exact.jpg"}],
        )
        record_run_figures(
            "paper-a",
            [{"caption": "worker", "filename": "paraphrased.jpg"}],
            overwrite=False,
        )
        assert get_run_figures()["paper-a"] == [
            {"caption": "tool", "filename": "exact.jpg"}
        ]
    finally:
        reset_run_context(token)
