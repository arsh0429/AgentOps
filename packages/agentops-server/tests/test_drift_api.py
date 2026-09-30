import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_drift_endpoint_returns_empty_signals_when_no_data(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'d.db'}")
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
        r = await c.get("/drift")
    assert r.status_code == 200
    assert r.json() == {"signals": []}
