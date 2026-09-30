from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from ..config import settings

engine = create_async_engine(settings.db_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _apply_compatibility_migrations(connection: Connection) -> None:
    """Apply additive migrations needed by pre-Alembic development databases.

    ``SQLModel.metadata.create_all`` creates new tables but does not add new
    columns to an existing table. AgentOps is still intentionally migration-
    tool free, so keep this small compatibility bridge until Alembic is
    introduced.
    """
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())

    if "span" in table_names:
        span_columns = {column["name"] for column in inspector.get_columns("span")}
        if "trace_id" not in span_columns:
            connection.exec_driver_sql(
                "ALTER TABLE span ADD COLUMN trace_id VARCHAR NOT NULL DEFAULT ''"
            )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_span_trace_id ON span (trace_id)"
        )

    if "evalresult" in table_names:
        target_columns = {"run_id", "eval_name", "mode"}
        unique_constraints = inspector.get_unique_constraints("evalresult")
        unique_indexes = [
            index for index in inspector.get_indexes("evalresult") if index.get("unique")
        ]
        has_eval_identity_constraint = any(
            set(cast(list[str], item.get("column_names") or [])) == target_columns
            for item in [*unique_constraints, *unique_indexes]
        )
        if not has_eval_identity_constraint:
            # Preserve the most recently inserted row from each duplicate
            # group before enforcing the identity rule on a legacy database.
            connection.exec_driver_sql(
                "DELETE FROM evalresult WHERE id NOT IN ("
                "SELECT MAX(id) FROM evalresult GROUP BY run_id, eval_name, mode"
                ")"
            )
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX uq_evalresult_run_eval_mode "
                "ON evalresult (run_id, eval_name, mode)"
            )


async def init_db() -> None:
    from . import models  # noqa: F401  -- triggers SQLModel metadata population
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.run_sync(_apply_compatibility_migrations)

async def session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        yield s
