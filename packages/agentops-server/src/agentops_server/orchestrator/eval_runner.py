from __future__ import annotations

import asyncio
import logging
import random

from agentops.eval import (
    registry,
    templates,  # noqa: F401  -- import triggers registration
)
from agentops.eval.registry import EvalSpec
from agentops.models import EvalMode
from agentops.models import EvalResult as EvalResultModel
from agentops.models import Run as RunModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from ..config import settings
from ..db import engine as _db_engine
from ..db.models import EvalResult as EvalResultRow
from ..db.models import Run

log = logging.getLogger(__name__)

def _to_domain(run: Run) -> RunModel:
    return RunModel(
        id=run.id, agent_name=run.agent_name, started_at=run.started_at,
        ended_at=run.ended_at, input=run.input, output=run.output,
        prompt_sha=run.prompt_sha, model=run.model,
        total_cost=run.total_cost, total_tokens=run.total_tokens,
        status=run.status,  # type: ignore[arg-type]
    )

def _apply_result(row: EvalResultRow, result: EvalResultModel, mode: str) -> None:
    row.mode = mode
    row.score = result.score
    row.label = result.label
    row.rationale = result.rationale
    row.created_at = result.created_at


async def _persist(result: EvalResultModel) -> None:
    """Insert or update one logical evaluation result.

    The database uniqueness rule is the final concurrency guard. The retry
    path handles two workers racing after both initially observe no row.
    """
    mode = result.mode.value if hasattr(result.mode, "value") else str(result.mode)
    async with _db_engine.SessionLocal() as s:
        existing = (await s.exec(
            select(EvalResultRow).where(
                EvalResultRow.run_id == result.run_id,
                EvalResultRow.eval_name == result.eval_name,
                EvalResultRow.mode == mode,
            )
        )).first()
        if existing is not None:
            _apply_result(existing, result, mode)
            s.add(existing)
            await s.commit()
            return

        s.add(EvalResultRow(
            run_id=result.run_id,
            eval_name=result.eval_name,
            mode=mode,
            score=result.score,
            label=result.label,
            rationale=result.rationale,
            created_at=result.created_at,
        ))
        try:
            await s.commit()
        except IntegrityError:
            await s.rollback()
            existing = (await s.exec(
                select(EvalResultRow).where(
                    EvalResultRow.run_id == result.run_id,
                    EvalResultRow.eval_name == result.eval_name,
                    EvalResultRow.mode == mode,
                )
            )).first()
            if existing is None:
                raise
            _apply_result(existing, result, mode)
            s.add(existing)
            await s.commit()

async def run_invariants(run_id: str) -> None:
    async with _db_engine.SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == run_id))).first()
    if run is None:
        log.warning("run %s not found for invariants", run_id)
        return
    domain = _to_domain(run)
    for spec in registry.evals_for_mode(EvalMode.INVARIANT):
        try:
            res = await spec.fn(domain, None)
            await _persist(res)
        except Exception:
            log.exception("invariant eval %s failed for run %s", spec.name, run_id)

async def run_online(run_id: str) -> None:
    if random.random() > settings.online_eval_sample_rate:
        return
    async with _db_engine.SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == run_id))).first()
    if run is None:
        return
    domain = _to_domain(run)
    tasks = []
    for spec in registry.evals_for_mode(EvalMode.ONLINE):
        tasks.append(asyncio.create_task(_run_one(spec, domain)))
    await asyncio.gather(*tasks, return_exceptions=True)

async def _run_one(spec: EvalSpec, domain: RunModel) -> None:
    try:
        res = await spec.fn(domain, None)
        await _persist(res)
    except Exception:
        log.exception("online eval %s failed for run %s", spec.name, domain.id)
