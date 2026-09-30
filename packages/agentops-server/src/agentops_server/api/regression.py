from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import col, select

from ..db import engine as _db_engine
from ..db.models import RegressionRun
from ..orchestrator.regression import run_regression

router = APIRouter()

class RegressionRequest(BaseModel):
    dataset_id: str
    prompt_sha: str | None = None
    model: str = "claude-sonnet-4-6"

@router.post("/regressions")
async def trigger_regression(req: RegressionRequest, bg: BackgroundTasks) -> dict[str, str]:
    bg.add_task(run_regression, req.dataset_id, req.prompt_sha, req.model)
    return {"status": "scheduled"}

@router.get("/regressions/{run_id}")
async def get_regression(run_id: str) -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        r = (await s.exec(select(RegressionRun).where(RegressionRun.id == run_id))).first()
    return {"regression": r.model_dump() if r else None}

@router.get("/regressions")
async def list_regressions(limit: int = 20) -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        rows = (await s.exec(select(RegressionRun)
                              .order_by(col(RegressionRun.started_at).desc()).limit(limit))).all()
    return {"regressions": [r.model_dump() for r in rows]}
