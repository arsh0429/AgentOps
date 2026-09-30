from datetime import datetime

import pytest
from agentops.models import DriftSignal, EvalMode, EvalResult, Run


def test_run_round_trips() -> None:
    r = Run(id="run-1", agent_name="arxiv", started_at=datetime.utcnow(),
            input={"x": 1}, output=None, prompt_sha="abcd", model="claude-haiku-4-5",
            total_cost=0.01, total_tokens=420, status="running")
    assert Run.model_validate_json(r.model_dump_json()) == r


def test_eval_result_unit_interval_score() -> None:
    EvalResult(run_id="r", eval_name="x", mode=EvalMode.ONLINE, score=0.5)
    with pytest.raises(ValueError):
        EvalResult(run_id="r", eval_name="x", mode=EvalMode.ONLINE, score=1.5)


def test_drift_state_signals_enum_complete() -> None:
    assert {s.value for s in DriftSignal} == {"input", "tool_call", "quality"}
