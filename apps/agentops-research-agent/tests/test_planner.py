from unittest.mock import patch

import pytest
from agentops_research_agent.planner import PlannerInput, PlannerResult, build_planner_agent


def test_planner_input_validates() -> None:
    PlannerInput(research_interest="concept drift", date_from="2024-01-01", date_to="2024-12-31")
    with pytest.raises(ValueError):
        PlannerInput(research_interest="", date_from="2024-01-01", date_to="2024-12-31")


def test_planner_and_worker_use_selected_model() -> None:
    with (
        patch("agentops_research_agent.planner.AnthropicModel") as model_cls,
        patch("agentops_research_agent.planner.build_worker_agent") as build_worker,
        patch("agentops_research_agent.planner.Agent"),
    ):
        build_planner_agent("claude-haiku-4-5")

    model_cls.assert_called_once_with("claude-haiku-4-5")
    build_worker.assert_called_once_with("claude-haiku-4-5")

@pytest.mark.live
async def test_planner_produces_digest_for_drift_interest() -> None:
    agent = build_planner_agent()
    res = await agent.run(PlannerInput(
        research_interest="concept drift detection in streaming ML",
        date_from="2024-01-01", date_to="2024-12-31",
    ))
    assert isinstance(res.output, PlannerResult)
    assert "##" in res.output.digest
    assert len(res.output.candidates) >= 3
    assert res.output.candidates[0].score >= 0.0
