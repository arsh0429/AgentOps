from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from ..db import engine as _db_engine
from ..db.models import Run, Span

router = APIRouter()

@router.get("/runs")
async def list_runs(limit: int = 50, offset: int = 0,
                    agent_name: str | None = None) -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        stmt = select(Run).order_by(col(Run.started_at).desc()).limit(limit).offset(offset)
        if agent_name:
            stmt = stmt.where(Run.agent_name == agent_name)
        rows = (await s.exec(stmt)).all()
    return {"runs": [r.model_dump() for r in rows]}

@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == run_id))).first()
        if run is None:
            raise HTTPException(404, f"run {run_id} not found")
        spans = (await s.exec(select(Span).where(Span.run_id == run_id)
                              .order_by(col(Span.started_at)))).all()
    return {"run": run.model_dump(), "spans": [sp.model_dump() for sp in spans]}
