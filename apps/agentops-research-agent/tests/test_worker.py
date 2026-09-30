from unittest.mock import patch

import pytest
from agentops_research_agent.worker import WorkerInput, WorkerResult, build_worker_agent


@pytest.mark.live
async def test_worker_processes_known_paper() -> None:
    agent = build_worker_agent()
    res = await agent.run(WorkerInput(
        paper_id="2401.00001",
        research_interest="concept drift detection in streaming ML",
    ))
    assert isinstance(res.output, WorkerResult)
    assert res.output.paper_id == "2401.00001"
    assert res.output.summary
    assert len(res.output.figure_descriptions) >= 1

def test_worker_input_model_validates() -> None:
    with pytest.raises(ValueError):
        WorkerInput(paper_id="", research_interest="x")


def test_worker_uses_selected_model() -> None:
    with (
        patch("agentops_research_agent.worker.AnthropicModel") as model_cls,
        patch("agentops_research_agent.worker.Agent"),
    ):
        build_worker_agent("claude-haiku-4-5")

    model_cls.assert_called_once_with("claude-haiku-4-5")
