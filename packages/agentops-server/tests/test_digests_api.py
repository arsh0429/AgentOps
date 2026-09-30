from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def app_with_digest(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'d.db'}")
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    import agentops_server.main as mn
    importlib.reload(cfg)
    importlib.reload(eng)
    importlib.reload(mn)
    from agentops_server.db.engine import SessionLocal, init_db
    from agentops_server.db.models import Run
    await init_db()
    async with SessionLocal() as s:
        s.add(Run(
            id="digest-test-1",
            agent_name="arxiv-planner",
            started_at=datetime(2026, 5, 6, 10),
            ended_at=datetime(2026, 5, 6, 10, 5),
            status="succeeded",
            input={
                "research_interest": "concept drift",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
            },
            output={
                "digest": "## hi\n- thing",
                "candidates": [{"paper_id": "x", "title": "X", "score": 0.9, "rationale": "r"}],
                "sections": [],
            },
        ))
        s.add(Run(
            id="no-digest-run",
            agent_name="arxiv-planner",
            started_at=datetime(2026, 5, 5, 10),
            ended_at=datetime(2026, 5, 5, 10, 5),
            status="succeeded",
            input={"research_interest": "other"},
            output=None,
        ))
        await s.commit()
    return mn.app


@pytest.mark.asyncio
async def test_list_digests(app_with_digest) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_digest), base_url="http://t") as c:
        r = await c.get("/digests")
    assert r.status_code == 200
    body = r.json()
    ids = [d["run_id"] for d in body["digests"]]
    assert "digest-test-1" in ids
    assert "no-digest-run" not in ids
    row = next(d for d in body["digests"] if d["run_id"] == "digest-test-1")
    assert row["top_paper_title"] == "X"
    assert row["research_interest"] == "concept drift"


@pytest.mark.asyncio
async def test_get_digest(app_with_digest) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_digest), base_url="http://t") as c:
        r = await c.get("/digests/digest-test-1")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == "digest-test-1"
    assert body["digest"] == "## hi\n- thing"
    assert len(body["candidates"]) == 1
    assert body["candidates"][0]["title"] == "X"
    assert body["sections"] == []


@pytest.mark.asyncio
async def test_get_digest_not_found(app_with_digest) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_digest), base_url="http://t") as c:
        r = await c.get("/digests/no-such-run")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_digest_no_digest_output(app_with_digest) -> None:
    """A run that exists but has no digest still returns 200 with empty
    fields so polling clients can detect silent agent failures (status
    succeeded but digest empty) and surface a clear error rather than
    spin forever on 404s.
    """
    async with AsyncClient(transport=ASGITransport(app=app_with_digest), base_url="http://t") as c:
        r = await c.get("/digests/no-digest-run")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == "no-digest-run"
    assert body["digest"] == ""
    assert body["status"] in {"running", "succeeded", "failed"}


# ---------------------------------------------------------------------------
# POST /digests tests
# ---------------------------------------------------------------------------

@pytest.fixture
async def app_for_post(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'p.db'}")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    import agentops_server.main as mn
    importlib.reload(cfg)
    importlib.reload(eng)
    importlib.reload(mn)
    from agentops_server.db.engine import init_db
    await init_db()
    return mn.app


@pytest.mark.asyncio
async def test_post_digest_creates_run(app_for_post) -> None:
    """POST /digests stubs the subprocess, returns 202, and creates a running row."""
    fake_proc = MagicMock()
    fake_proc.wait = AsyncMock(return_value=0)

    create_subprocess = AsyncMock(return_value=fake_proc)
    with patch("asyncio.create_subprocess_exec", create_subprocess):
        async with AsyncClient(transport=ASGITransport(app=app_for_post), base_url="http://t") as c:
            r = await c.post("/digests", json={
                "research_interest": "concept drift in streaming ML",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
                "model": "claude-haiku-4-5",
            })

    assert r.status_code == 202
    body = r.json()
    assert "run_id" in body
    assert body["run_id"].startswith("live-")
    assert body["status"] == "running"
    assert body["model"] == "claude-haiku-4-5"

    command = create_subprocess.await_args.args
    assert command[-2:] == ("--model", "claude-haiku-4-5")
    child_env = create_subprocess.await_args.kwargs["env"]
    assert child_env["AGENTOPS_ENDPOINT"] == "http://localhost:8000/ingest"

    # Verify the placeholder row was committed
    from agentops_server.db.engine import SessionLocal
    from agentops_server.db.models import Run
    from sqlmodel import select

    async with SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == body["run_id"]))).first()
    assert run is not None
    assert run.status == "running"
    assert run.model == "claude-haiku-4-5"
    assert run.input["research_interest"] == "concept drift in streaming ML"
    assert run.input["model"] == "claude-haiku-4-5"


@pytest.mark.asyncio
async def test_post_digest_empty_interest_returns_422(app_for_post) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_for_post), base_url="http://t") as c:
        r = await c.post("/digests", json={
            "research_interest": "",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_post_digest_rejects_invalid_date_window(app_for_post) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_for_post), base_url="http://t") as c:
        r = await c.post("/digests", json={
            "research_interest": "concept drift",
            "date_from": "2024-12-31",
            "date_to": "2024-01-01",
        })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_post_digest_records_spawn_failure(app_for_post) -> None:
    with patch("asyncio.create_subprocess_exec", AsyncMock(side_effect=OSError("missing uv"))):
        async with AsyncClient(transport=ASGITransport(app=app_for_post), base_url="http://t") as c:
            r = await c.post("/digests", json={
                "research_interest": "concept drift",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
            })
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_post_digest_missing_field_returns_422(app_for_post) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_for_post), base_url="http://t") as c:
        r = await c.post("/digests", json={
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_post_digest_no_api_key_returns_503(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'n.db'}")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    import agentops_server.main as mn
    importlib.reload(cfg)
    importlib.reload(eng)
    importlib.reload(mn)
    from agentops_server.db.engine import init_db
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=mn.app), base_url="http://t") as c:
        r = await c.post("/digests", json={
            "research_interest": "test",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        })
    assert r.status_code == 503
