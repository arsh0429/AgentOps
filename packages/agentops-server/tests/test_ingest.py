from datetime import datetime

import pytest
from agentops_server.db.models import Run, Span, TraceRunMapping
from httpx import ASGITransport, AsyncClient
from sqlmodel import select


def _ns(dt: datetime) -> int:
    return int(dt.timestamp() * 1e9)


def test_error_status_on_root_marks_run_failed() -> None:
    from agentops_server.api.ingest import _apply_root_span

    started = datetime(2026, 5, 6, 12)
    run = Run(id="failed-run", agent_name="agent", started_at=started)
    root = Span(id="root", trace_id="trace", run_id="failed-run", name="agent",
                started_at=started, ended_at=started,
                attributes={"agentops.output": '{"answer":"partial"}'})
    _apply_root_span(run, root, has_error_status=True)
    assert run.status == "failed"

@pytest.mark.asyncio
async def test_ingest_creates_run_and_spans(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    import agentops_server.main as mn
    importlib.reload(cfg)
    importlib.reload(eng)
    importlib.reload(mn)
    from agentops_server.db.engine import SessionLocal, init_db
    from agentops_server.main import app as fresh_app
    await init_db()

    payload = {
        "spans": [
            {
                "trace_id": "0" * 32, "span_id": "1" * 16, "parent_span_id": None,
                "name": "planner", "kind": "INTERNAL",
                "start_time_unix_nano": str(_ns(datetime(2026, 5, 6, 12, 0, 0))),
                "end_time_unix_nano":   str(_ns(datetime(2026, 5, 6, 12, 0, 5))),
                "attributes": {"agentops.run_id": "run-001",
                               "agentops.role": "planner",
                               "agentops.agent_name": "arxiv-planner",
                               "agentops.input": '{"research_interest":"x"}'},
                "events": [], "status": {"code": "OK", "description": ""},
            },
            {
                "trace_id": "0" * 32, "span_id": "2" * 16, "parent_span_id": "1" * 16,
                "name": "worker", "kind": "INTERNAL",
                "start_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 1)),
                "end_time_unix_nano":   _ns(datetime(2026, 5, 6, 12, 0, 4)),
                "attributes": {"agentops.run_id": "run-001",
                               "agentops.role": "worker"},
                "events": [], "status": {"code": "OK", "description": ""},
            },
        ]
    }

    transport = ASGITransport(app=fresh_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/ingest", json=payload)
    assert r.status_code == 202

    async with SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == "run-001"))).first()
        spans = (await s.exec(select(Span).where(Span.run_id == "run-001"))).all()
    assert run is not None
    assert run.agent_name == "arxiv-planner"
    assert len(spans) == 2

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        malformed = await c.post("/ingest", json={"spans": [{"name": "missing id"}]})
        wrong_shape = await c.post("/ingest", json={"spans": "not a list"})
    assert malformed.status_code == 422
    assert wrong_shape.status_code == 422


@pytest.mark.asyncio
async def test_child_span_arriving_before_root_is_reattached(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'ordered.db'}")
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    import agentops_server.main as mn
    importlib.reload(cfg)
    importlib.reload(eng)
    importlib.reload(mn)
    from agentops_server.db.engine import SessionLocal, init_db
    from agentops_server.main import app as fresh_app
    await init_db()

    trace_id = "a" * 32
    root_span_id = "1" * 16
    child_span_id = "2" * 16
    fallback_run_id = f"trace-{trace_id}"
    child_payload = {
        "spans": [{
            "trace_id": trace_id,
            "span_id": child_span_id,
            "parent_span_id": root_span_id,
            "name": "llm.text",
            "kind": "INTERNAL",
            "start_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 1)),
            "end_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 2)),
            "attributes": {
                "agentops.role": "worker",
                "gen_ai.request.model": "claude-haiku-4-5",
                "gen_ai.usage.input_tokens": 100,
                "gen_ai.usage.output_tokens": 20,
            },
            "events": [],
            "status": {"code": "OK", "description": ""},
        }],
    }
    root_payload = {
        "spans": [{
            "trace_id": trace_id,
            "span_id": root_span_id,
            "parent_span_id": None,
            "name": "agentops_research_agent.run",
            "kind": "INTERNAL",
            "start_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 0)),
            "end_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 3)),
            "attributes": {
                "agentops.run_id": "run-out-of-order",
                "agentops.role": "planner",
                "agentops.agent_name": "arxiv-planner",
                "agentops.input": '{"research_interest":"drift"}',
            },
            "events": [],
            "status": {"code": "OK", "description": ""},
        }],
    }

    async with AsyncClient(
        transport=ASGITransport(app=fresh_app), base_url="http://test"
    ) as client:
        first = await client.post("/ingest", json=child_payload)
        assert first.status_code == 202

        async with SessionLocal() as session:
            early_span = await session.get(Span, child_span_id)
            mapping = await session.get(TraceRunMapping, trace_id)
        assert early_span is not None
        assert early_span.run_id == fallback_run_id
        assert mapping is not None
        assert mapping.run_id == fallback_run_id
        assert not mapping.is_resolved

        second = await client.post("/ingest", json=root_payload)
        assert second.status_code == 202

    async with SessionLocal() as session:
        run = await session.get(Run, "run-out-of-order")
        old_run = await session.get(Run, fallback_run_id)
        mapping = await session.get(TraceRunMapping, trace_id)
        spans = (await session.exec(
            select(Span).where(Span.trace_id == trace_id)
        )).all()

    assert run is not None
    assert run.status == "succeeded"
    assert run.total_tokens == 120
    assert run.total_cost == pytest.approx(0.00016)
    assert old_run is None
    assert mapping is not None
    assert mapping.run_id == "run-out-of-order"
    assert mapping.is_resolved
    assert {span.run_id for span in spans} == {"run-out-of-order"}
    assert {span.id for span in spans} == {root_span_id, child_span_id}


@pytest.mark.asyncio
async def test_cost_is_recalculated_across_ingestion_batches(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'cost.db'}")
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    import agentops_server.main as mn
    importlib.reload(cfg)
    importlib.reload(eng)
    importlib.reload(mn)
    from agentops_server.db.engine import SessionLocal, init_db
    from agentops_server.main import app as fresh_app
    await init_db()

    trace_id = "b" * 32
    root_span_id = "3" * 16

    def raw_span(span_id: str, input_tokens: int, output_tokens: int) -> dict:
        return {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": root_span_id,
            "name": "llm.text",
            "kind": "INTERNAL",
            "start_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 1)),
            "end_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 2)),
            "attributes": {
                "gen_ai.request.model": "claude-haiku-4-5",
                "gen_ai.usage.input_tokens": input_tokens,
                "gen_ai.usage.output_tokens": output_tokens,
            },
            "events": [],
            "status": {"code": "OK", "description": ""},
        }

    root_payload = {
        "spans": [{
            "trace_id": trace_id,
            "span_id": root_span_id,
            "parent_span_id": None,
            "name": "agentops_research_agent.run",
            "kind": "INTERNAL",
            "start_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 0)),
            "end_time_unix_nano": None,
            "attributes": {
                "agentops.run_id": "run-multi-batch",
                "agentops.agent_name": "arxiv-planner",
            },
            "events": [],
            "status": {"code": "UNSET", "description": ""},
        }],
    }
    first_llm_payload = {"spans": [raw_span("4" * 16, 100, 20)]}
    second_llm_payload = {"spans": [raw_span("5" * 16, 200, 40)]}

    async with AsyncClient(
        transport=ASGITransport(app=fresh_app), base_url="http://test"
    ) as client:
        assert (await client.post("/ingest", json=root_payload)).status_code == 202
        assert (await client.post("/ingest", json=first_llm_payload)).status_code == 202
        assert (await client.post("/ingest", json=second_llm_payload)).status_code == 202
        # Re-sending an existing span updates it; it must not double-count it.
        assert (await client.post("/ingest", json=second_llm_payload)).status_code == 202

    async with SessionLocal() as session:
        run = await session.get(Run, "run-multi-batch")
        spans = (await session.exec(
            select(Span).where(Span.run_id == "run-multi-batch")
        )).all()

    assert run is not None
    assert run.total_tokens == 360
    assert run.total_cost == pytest.approx(0.00048)
    assert len(spans) == 3
    assert {span.trace_id for span in spans} == {trace_id}


@pytest.mark.asyncio
async def test_reingested_terminal_root_schedules_evaluations_once(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'terminal.db'}")
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    import agentops_server.main as mn
    importlib.reload(cfg)
    importlib.reload(eng)
    importlib.reload(mn)
    import agentops_server.api.ingest as ingest_api
    from agentops_server.db.engine import init_db
    from agentops_server.main import app as fresh_app
    await init_db()

    calls: list[tuple[str, str]] = []

    async def fake_invariants(run_id: str) -> None:
        calls.append(("invariants", run_id))

    async def fake_online(run_id: str) -> None:
        calls.append(("online", run_id))

    monkeypatch.setattr(ingest_api, "run_invariants", fake_invariants)
    monkeypatch.setattr(ingest_api, "run_online", fake_online)

    payload = {
        "spans": [{
            "trace_id": "c" * 32,
            "span_id": "6" * 16,
            "parent_span_id": None,
            "name": "agentops_research_agent.run",
            "kind": "INTERNAL",
            "start_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 0)),
            "end_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 2)),
            "attributes": {
                "agentops.run_id": "run-terminal-once",
                "agentops.agent_name": "arxiv-planner",
            },
            "events": [],
            "status": {"code": "OK", "description": ""},
        }],
    }

    async with AsyncClient(
        transport=ASGITransport(app=fresh_app), base_url="http://test"
    ) as client:
        assert (await client.post("/ingest", json=payload)).status_code == 202
        assert (await client.post("/ingest", json=payload)).status_code == 202

    assert calls == [
        ("invariants", "run-terminal-once"),
        ("online", "run-terminal-once"),
    ]
