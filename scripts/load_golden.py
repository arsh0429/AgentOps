"""Load evaluations/golden/dataset.json into the AgentOps database."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

GOLDEN = Path(__file__).resolve().parent.parent / "evaluations" / "golden" / "dataset.json"

async def main() -> None:
    from agentops_server.db.engine import SessionLocal, init_db
    from agentops_server.db.models import Dataset, DatasetRow
    from sqlmodel import select

    await init_db()
    data = json.loads(GOLDEN.read_text())
    ds_id = "golden-arxiv-v1"
    async with SessionLocal() as s:
        existing = (await s.exec(select(Dataset).where(Dataset.id == ds_id))).first()
        if existing is None:
            s.add(Dataset(id=ds_id, name=data["name"],
                          description=data.get("description")))
        for row in data["rows"]:
            row_existing = await s.get(DatasetRow, row["id"])
            if row_existing is None:
                s.add(DatasetRow(id=row["id"], dataset_id=ds_id,
                                 input=row["input"], expected=row["expected"]))
        await s.commit()
    print(f"loaded {len(data['rows'])} rows into dataset {ds_id}")

if __name__ == "__main__":
    asyncio.run(main())
