import pytest
from agentops_server.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_healthcheck_responds_ok() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_db_tables_exist_on_startup(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "agentops_test.sqlite"
    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    importlib.reload(cfg)
    importlib.reload(eng)
    from agentops_server.db.engine import init_db
    await init_db()
    import sqlite3
    conn = sqlite3.connect(db_path)
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"run", "span", "evalresult", "driftstaterow", "dataset",
            "datasetrow", "regressionrun", "tracerunmapping",
            "driftcheckpoint", "driftreference"} <= names


@pytest.mark.asyncio
async def test_init_db_adds_trace_id_to_existing_span_table(tmp_path, monkeypatch) -> None:
    import sqlite3

    db_path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE span (id VARCHAR PRIMARY KEY, run_id VARCHAR NOT NULL)"
        )

    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    importlib.reload(cfg)
    importlib.reload(eng)
    from agentops_server.db.engine import init_db
    await init_db()

    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(span)")}
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(span)")}

    assert "trace_id" in columns
    assert "ix_span_trace_id" in indexes


@pytest.mark.asyncio
async def test_init_db_deduplicates_legacy_evaluations(tmp_path, monkeypatch) -> None:
    import sqlite3

    db_path = tmp_path / "legacy_evals.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE evalresult ("
            "id INTEGER PRIMARY KEY, run_id VARCHAR NOT NULL, "
            "eval_name VARCHAR NOT NULL, mode VARCHAR NOT NULL, "
            "score FLOAT NOT NULL, label VARCHAR, rationale VARCHAR, "
            "created_at DATETIME NOT NULL)"
        )
        connection.execute(
            "INSERT INTO evalresult "
            "(run_id, eval_name, mode, score, created_at) "
            "VALUES ('run-1', 'quality', 'online', 0.2, '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO evalresult "
            "(run_id, eval_name, mode, score, created_at) "
            "VALUES ('run-1', 'quality', 'online', 0.9, '2026-01-02')"
        )

    monkeypatch.setenv("AGENTOPS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    import importlib

    import agentops_server.config as cfg
    import agentops_server.db.engine as eng
    importlib.reload(cfg)
    importlib.reload(eng)
    from agentops_server.db.engine import init_db
    await init_db()

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT score FROM evalresult "
            "WHERE run_id='run-1' AND eval_name='quality' AND mode='online'"
        ).fetchall()
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(evalresult)")}
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO evalresult "
                "(run_id, eval_name, mode, score, created_at) "
                "VALUES ('run-1', 'quality', 'online', 0.1, '2026-01-03')"
            )

    assert rows == [(0.9,)]
    assert "uq_evalresult_run_eval_mode" in indexes
