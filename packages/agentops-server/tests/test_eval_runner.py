from datetime import datetime

import pytest
from sqlmodel import select


@pytest.mark.asyncio
async def test_run_invariants_writes_results(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'e.db'}")
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    import agentops_server.orchestrator.eval_runner as er
    importlib.reload(cfg)
    importlib.reload(eng)
    # Re-register eval templates in case an autouse fixture cleared the registry.
    for _sub in ("structural_completeness", "cost_within_budget",
                 "relevance_judge", "faithfulness_judge"):
        importlib.reload(importlib.import_module(f"agentops.eval.templates.{_sub}"))
    importlib.reload(er)
    from agentops_server.db.engine import SessionLocal, init_db
    from agentops_server.db.models import EvalResult, Run
    from agentops_server.orchestrator.eval_runner import run_invariants
    await init_db()
    async with SessionLocal() as s:
        s.add(Run(id="rx", agent_name="a", started_at=datetime.utcnow(),
                  ended_at=datetime.utcnow(), status="succeeded", total_cost=0.01,
                  output={"digest": "## p\n- s\n2401.00001"}))
        await s.commit()

    await run_invariants("rx")

    async with SessionLocal() as s:
        rows = (await s.exec(select(EvalResult).where(EvalResult.run_id == "rx"))).all()
    names = {r.eval_name for r in rows}
    assert "structural_completeness" in names
    assert "cost_within_budget" in names


@pytest.mark.asyncio
async def test_persist_updates_same_logical_evaluation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'upsert.db'}")
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    import agentops_server.orchestrator.eval_runner as er
    importlib.reload(cfg)
    importlib.reload(eng)
    importlib.reload(er)
    from agentops.models import EvalMode
    from agentops.models import EvalResult as EvalResultModel
    from agentops_server.db.engine import SessionLocal, init_db
    from agentops_server.db.models import EvalResult, Run
    await init_db()

    async with SessionLocal() as s:
        s.add(Run(id="run-upsert", agent_name="agent", started_at=datetime.utcnow()))
        await s.commit()

    await er._persist(EvalResultModel(
        run_id="run-upsert",
        eval_name="structural_completeness",
        mode=EvalMode.INVARIANT,
        score=0.25,
        label="first",
    ))
    await er._persist(EvalResultModel(
        run_id="run-upsert",
        eval_name="structural_completeness",
        mode=EvalMode.INVARIANT,
        score=1.0,
        label="updated",
    ))

    async with SessionLocal() as s:
        rows = (await s.exec(select(EvalResult).where(
            EvalResult.run_id == "run-upsert"
        ))).all()

    assert len(rows) == 1
    assert rows[0].score == 1.0
    assert rows[0].label == "updated"
