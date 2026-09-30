from datetime import datetime

import pytest
from agentops.eval import registry
from agentops.models import Run


@pytest.fixture(autouse=True)
def _reload_templates() -> None:
    """Re-import templates after the autouse registry reset (from conftest).

    Ensures the 4 templates are registered for each test.
    """
    import importlib
    for sub in ("structural_completeness", "cost_within_budget",
                "relevance_judge", "faithfulness_judge"):
        importlib.reload(__import__(f"agentops.eval.templates.{sub}", fromlist=[sub]))
    yield

def test_all_four_registered() -> None:
    names = set(registry.list_evals())
    assert {"relevance_judge", "faithfulness_judge",
            "structural_completeness", "cost_within_budget"} <= names

@pytest.mark.asyncio
async def test_structural_completeness_passes_when_digest_complete() -> None:
    run = Run(id="r1", agent_name="a", started_at=datetime.utcnow(),
              output={"digest": "## P1\n- summary\n- score: 0.9\n[citation: 2401.00001]"})
    spec = registry.get_eval("structural_completeness")
    res = await spec.fn(run, None)
    assert res.score == 1.0

@pytest.mark.asyncio
async def test_structural_completeness_fails_when_digest_empty() -> None:
    run = Run(id="r1", agent_name="a", started_at=datetime.utcnow(), output={"digest": ""})
    spec = registry.get_eval("structural_completeness")
    res = await spec.fn(run, None)
    assert res.score == 0.0

@pytest.mark.asyncio
async def test_cost_within_budget_score() -> None:
    spec = registry.get_eval("cost_within_budget")
    cheap = Run(id="r-cheap", agent_name="a", started_at=datetime.utcnow(), total_cost=0.05)
    expensive = Run(id="r-expensive", agent_name="a", started_at=datetime.utcnow(), total_cost=2.0)
    assert (await spec.fn(cheap, None)).score == 1.0
    assert (await spec.fn(expensive, None)).score < 1.0
