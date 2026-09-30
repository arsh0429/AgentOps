from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlmodel import col, select

from ..db import engine as _db_engine
from ..db.models import EvalResult

router = APIRouter()

@router.get("/runs/{run_id}/evals")
async def evals_for_run(run_id: str) -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        rows = (await s.exec(select(EvalResult).where(EvalResult.run_id == run_id))).all()
    return {"results": [r.model_dump() for r in rows]}

@router.get("/evals/recent")
async def recent_evals(eval_name: str | None = None, limit: int = 100) -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        stmt = select(EvalResult).order_by(col(EvalResult.created_at).desc()).limit(limit)
        if eval_name:
            stmt = stmt.where(EvalResult.eval_name == eval_name)
        rows = (await s.exec(stmt)).all()
    return {"results": [r.model_dump() for r in rows]}
