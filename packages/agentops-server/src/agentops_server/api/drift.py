from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlmodel import col, select

from ..db import engine as _db_engine
from ..db.models import DriftStateRow

router = APIRouter()

@router.get("/drift")
async def drift_state() -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        rows = (await s.exec(
            select(DriftStateRow).order_by(col(DriftStateRow.updated_at).desc())
        )).all()
    latest: dict[tuple[str, str], DriftStateRow] = {}
    for r in rows:
        key = (r.signal, r.detector_name)
        if key not in latest or r.updated_at > latest[key].updated_at:
            latest[key] = r
    return {"signals": [r.model_dump() for r in latest.values()]}

@router.get("/drift/series/{signal}")
async def drift_series(signal: str, limit: int = 200) -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        rows = (await s.exec(select(DriftStateRow)
                              .where(DriftStateRow.signal == signal)
                              .order_by(col(DriftStateRow.updated_at).desc())
                              .limit(limit))).all()
    return {"points": [r.model_dump() for r in reversed(rows)]}
