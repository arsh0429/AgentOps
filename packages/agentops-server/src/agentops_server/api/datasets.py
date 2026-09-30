from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from ..db import engine as _db_engine
from ..db.models import Dataset, DatasetRow

router = APIRouter()

@router.get("/datasets")
async def list_datasets() -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        ds = (await s.exec(select(Dataset))).all()
    return {"datasets": [d.model_dump() for d in ds]}

@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str) -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        d = (await s.exec(select(Dataset).where(Dataset.id == dataset_id))).first()
        if d is None:
            raise HTTPException(404, f"dataset {dataset_id} not found")
        rows = (await s.exec(select(DatasetRow).where(DatasetRow.dataset_id == dataset_id))).all()
    return {"dataset": d.model_dump(), "rows": [r.model_dump() for r in rows]}
