from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from agentops_server.orchestrator import regression
from agentops_server.orchestrator.regression import score_against_expected


def test_score_against_expected_rewards_overlap() -> None:
    expected = {"expected_paper_ids": ["2401.00001", "2402.00012"],
                "expected_themes": ["concept drift", "Hoeffding bound"]}
    actual_digest = "## 2401.00001\nNotes about concept drift and Hoeffding bound."
    actual_papers = ["2401.00001"]
    s = score_against_expected(expected, actual_digest, actual_papers)
    assert 0.0 <= s.recall_paper_ids <= 1.0
    assert 0.0 <= s.theme_coverage <= 1.0
    assert s.recall_paper_ids == 0.5

def test_score_against_expected_zero_when_no_overlap() -> None:
    s = score_against_expected({"expected_paper_ids": ["x"], "expected_themes": ["y"]},
                               "completely off-topic", [])
    assert s.recall_paper_ids == 0.0
    assert s.theme_coverage == 0.0


@pytest.mark.asyncio
async def test_run_regression_uses_selected_model(monkeypatch) -> None:
    row = SimpleNamespace(
        id="row-1",
        input={
            "research_interest": "concept drift",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        },
        expected={"expected_paper_ids": [], "expected_themes": []},
    )
    saved_regression = SimpleNamespace()

    class Result:
        def __init__(self, *, rows=None, first=None):
            self._rows = rows or []
            self._first = first

        def all(self):
            return self._rows

        def first(self):
            return self._first

    class Session:
        def __init__(self, result):
            self.result = result

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def exec(self, _statement):
            return self.result

        def add(self, _record):
            return None

        async def commit(self):
            return None

    sessions = iter([
        Session(Result(rows=[row])),
        Session(Result(first=saved_regression)),
    ])
    monkeypatch.setattr(regression._db_engine, "SessionLocal", lambda: next(sessions))

    agent = MagicMock()
    agent.run = AsyncMock(return_value=SimpleNamespace(output=SimpleNamespace(
        candidates=[],
        digest="digest",
    )))
    build_agent = MagicMock(return_value=agent)
    import agentops_research_agent.planner as planner
    monkeypatch.setattr(planner, "build_planner_agent", build_agent)

    await regression.run_regression("dataset-1", "prompt-sha", "claude-haiku-4-5")

    build_agent.assert_called_once_with("claude-haiku-4-5")
    prompt = agent.run.await_args.args[0]
    deps = agent.run.await_args.kwargs["deps"]
    assert "concept drift" in prompt
    assert deps.research_interest == "concept drift"
