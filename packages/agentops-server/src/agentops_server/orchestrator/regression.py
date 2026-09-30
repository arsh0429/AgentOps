from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlmodel import select

from ..db import engine as _db_engine
from ..db.models import DatasetRow, RegressionRun

log = logging.getLogger(__name__)

@dataclass(frozen=True)
class RowScore:
    row_id: str
    recall_paper_ids: float
    theme_coverage: float

def score_against_expected(expected: dict[str, Any],
                            digest_text: str,
                            actual_paper_ids: list[str]) -> RowScore:
    expected_ids = set(expected.get("expected_paper_ids", []))
    actual_ids = set(actual_paper_ids)
    recall = (len(expected_ids & actual_ids) / len(expected_ids)) if expected_ids else 1.0

    themes = expected.get("expected_themes", [])
    digest_low = (digest_text or "").lower()
    hits = sum(1 for t in themes
               if re.search(r'\b' + re.escape(t.lower()) + r'\b', digest_low))
    coverage = (hits / len(themes)) if themes else 1.0

    return RowScore(row_id=str(expected.get("id", "")),
                    recall_paper_ids=recall,
                    theme_coverage=coverage)

async def run_regression(dataset_id: str, prompt_sha: str | None, model: str) -> str:
    """Drive the agent across a dataset and aggregate results."""
    from agentops_research_agent.planner import PlannerInput, build_planner_agent

    rid = f"reg-{uuid.uuid4().hex[:12]}"
    started = datetime.utcnow()

    async with _db_engine.SessionLocal() as s:
        rows = (await s.exec(select(DatasetRow).where(DatasetRow.dataset_id == dataset_id))).all()
        s.add(RegressionRun(id=rid, dataset_id=dataset_id,
                            prompt_sha=prompt_sha, model=model,
                            started_at=started, status="running",
                            summary={"row_count": len(rows)}))
        await s.commit()

    if not rows:
        async with _db_engine.SessionLocal() as s:
            rec = await s.get(RegressionRun, rid)
            if rec is not None:
                rec.status = "succeeded"
                rec.ended_at = datetime.utcnow()
                rec.summary = {"row_count": 0, "per_row": []}
                s.add(rec)
                await s.commit()
        return rid

    agent = build_planner_agent(model)
    scores: list[RowScore] = []
    for row in rows:
        try:
            deps = PlannerInput(
                research_interest=row.input["research_interest"],
                date_from=row.input["date_from"],
                date_to=row.input["date_to"],
            )
            prompt = (
                f"Research interest: {deps.research_interest}\n"
                f"Date window: {deps.date_from} to {deps.date_to}\n"
                "Produce the digest now."
            )
            result = await agent.run(prompt, deps=deps)
            actual_ids = [c.paper_id for c in result.output.candidates[:3]]
            row_expected = dict(row.expected)
            row_expected["id"] = row.id
            scores.append(score_against_expected(row_expected, result.output.digest, actual_ids))
        except Exception:
            log.exception("regression row %s failed", row.id)
            scores.append(RowScore(row_id=row.id, recall_paper_ids=0.0, theme_coverage=0.0))

    summary = {
        "row_count": len(rows),
        "mean_recall": sum(s.recall_paper_ids for s in scores) / len(scores),
        "mean_theme_coverage": sum(s.theme_coverage for s in scores) / len(scores),
        "per_row": [{"row_id": s.row_id, "recall_paper_ids": s.recall_paper_ids,
                      "theme_coverage": s.theme_coverage} for s in scores],
    }
    async with _db_engine.SessionLocal() as s:
        rec = (await s.exec(select(RegressionRun).where(RegressionRun.id == rid))).first()
        if rec is not None:
            rec.ended_at = datetime.utcnow()
            rec.status = "succeeded"
            rec.summary = summary
            s.add(rec)
            await s.commit()
    return rid
