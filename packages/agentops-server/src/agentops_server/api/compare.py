from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from ..db import engine as _db_engine
from ..db.models import EvalResult, Run, Span

router = APIRouter()

@router.get("/compare")
async def compare(a: str, b: str) -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        run_a = (await s.exec(select(Run).where(Run.id == a))).first()
        run_b = (await s.exec(select(Run).where(Run.id == b))).first()
        if not run_a or not run_b:
            raise HTTPException(404, "one or both runs not found")
        spans_a = (await s.exec(select(Span).where(Span.run_id == a))).all()
        spans_b = (await s.exec(select(Span).where(Span.run_id == b))).all()
        evals_a = (await s.exec(select(EvalResult).where(EvalResult.run_id == a))).all()
        evals_b = (await s.exec(select(EvalResult).where(EvalResult.run_id == b))).all()

    def _tool_dist(spans: Sequence[Span]) -> Counter[str]:
        return Counter(sp.name for sp in spans if sp.parent_span_id is not None)

    dist_a, dist_b = _tool_dist(spans_a), _tool_dist(spans_b)
    all_tools = sorted(set(dist_a) | set(dist_b))

    scores: dict[str, dict[str, float]] = {}
    for r in evals_a:
        scores.setdefault(r.eval_name, {})["a"] = r.score
    for r in evals_b:
        scores.setdefault(r.eval_name, {})["b"] = r.score

    return {
        "a": run_a.model_dump(),
        "b": run_b.model_dump(),
        "tool_distribution": [
            {"tool": t, "a_count": dist_a.get(t, 0), "b_count": dist_b.get(t, 0)}
            for t in all_tools
        ],
        "scores": [{"eval_name": k, **v} for k, v in scores.items()],
    }
