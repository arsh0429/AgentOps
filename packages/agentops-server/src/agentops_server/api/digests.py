from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlmodel import col, select

from ..db import engine as _db_engine
from ..db.models import Run

router = APIRouter()

_REPO_ROOT = Path(__file__).parents[5]


def _top_paper_title(output: dict[str, Any] | None) -> str | None:
    if output is None:
        return None
    candidates = output.get("candidates") or []
    if candidates:
        return str(candidates[0]["title"]) if candidates[0].get("title") else None
    sections = output.get("sections") or []
    if sections:
        return str(sections[0]["paper_id"]) if sections[0].get("paper_id") else None
    return None


@router.get("/digests")
async def list_digests(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        stmt = (select(Run).where(Run.agent_name == "arxiv-planner")
                .order_by(col(Run.started_at).desc()))
        rows = (await s.exec(stmt)).all()

    results = []
    for r in rows:
        if not (r.output and r.output.get("digest")):
            continue
        inp: dict[str, Any] = r.input or {}
        results.append({
            "run_id": r.id,
            "research_interest": inp.get("research_interest"),
            "date_from": inp.get("date_from"),
            "date_to": inp.get("date_to"),
            "generated_at": r.ended_at.isoformat() if r.ended_at else None,
            "top_paper_title": _top_paper_title(r.output),
            "model": r.model,
            "data_source": (r.output or {}).get("data_source"),
        })
        if len(results) == limit:
            break

    return {"digests": results}


@router.get("/digests/{run_id}")
async def get_digest(run_id: str) -> dict[str, Any]:
    async with _db_engine.SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == run_id))).first()

    if run is None:
        raise HTTPException(404, f"digest for run {run_id} not found")

    # For runs with no digest yet, return partial status so polling clients
    # can track progress (or surface a silent failure) without 404s. Includes
    # status=succeeded runs that produced no output (the agent crashed before
    # writing the OUTPUT span attribute) — the consumer UI uses this to
    # detect silent failures and stop spinning.
    if not (run.output and run.output.get("digest")):
        inp: dict[str, Any] = run.input or {}
        out: dict[str, Any] = run.output or {}
        return {
            "run_id": run.id,
            "research_interest": inp.get("research_interest"),
            "date_from": inp.get("date_from"),
            "date_to": inp.get("date_to"),
            "generated_at": run.ended_at.isoformat() if run.ended_at else None,
            "digest": "",
            "candidates": out.get("candidates") or [],
            "sections": out.get("sections") or [],
            "figures": out.get("figures") or {},
            "model": run.model,
            "data_source": out.get("data_source") or inp.get("data_source"),
            "status": run.status,
            "error": out.get("error"),
        }

    input_data: dict[str, Any] = run.input or {}
    output: dict[str, Any] = run.output or {}

    return {
        "run_id": run.id,
        "research_interest": input_data.get("research_interest"),
        "date_from": input_data.get("date_from"),
        "date_to": input_data.get("date_to"),
        "generated_at": run.ended_at.isoformat() if run.ended_at else None,
        "digest": output.get("digest", ""),
        "candidates": output.get("candidates") or [],
        "sections": output.get("sections") or [],
        "figures": output.get("figures") or {},
        "model": run.model,
        "data_source": output.get("data_source") or input_data.get("data_source"),
        "status": run.status,
        "error": output.get("error"),
    }


class CreateDigestRequest(BaseModel):
    research_interest: str = Field(min_length=1, max_length=500)
    date_from: date
    date_to: date
    model: str = Field(default="claude-sonnet-4-6", min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_date_window(self) -> CreateDigestRequest:
        if self.date_from > self.date_to:
            raise ValueError("date_from must be on or before date_to")
        return self


async def _watch_subprocess(proc: asyncio.subprocess.Process, run_id: str) -> None:
    """Ensure a subprocess that produced no digest reaches a terminal state."""
    returncode = await proc.wait()
    async with _db_engine.SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == run_id))).first()
        if run is not None and run.status == "running":
            run.status = "failed"
            run.ended_at = datetime.utcnow()
            run.output = {
                "error": (f"Research agent exited with code {returncode}"
                          if returncode else "Research agent exited without a digest"),
            }
            s.add(run)
            await s.commit()


@router.post("/digests", status_code=202)
async def create_digest(req: CreateDigestRequest) -> dict[str, str]:
    if not req.research_interest.strip():
        raise HTTPException(status_code=422, detail="research_interest must not be empty")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "ANTHROPIC_API_KEY is not set in the server environment. "
                "Start the server with the key exported, e.g.: "
                "set -a; source .env; set +a; make server"
            ),
        )

    run_id = f"live-{uuid.uuid4().hex[:10]}"
    now = datetime.utcnow()

    async with _db_engine.SessionLocal() as s:
        run = Run(
            id=run_id,
            agent_name="arxiv-planner",
            started_at=now,
            status="running",
            input={
                "research_interest": req.research_interest,
                "date_from": req.date_from.isoformat(),
                "date_to": req.date_to.isoformat(),
                "model": req.model,
                "data_source": ("arxiv-abstracts" if os.getenv("AGENTOPS_USE_REAL_ARXIV")
                                else "synthetic-mock"),
            },
            model=req.model,
            output=None,
        )
        s.add(run)
        await s.commit()

    env = {**os.environ, "AGENTOPS_RUN_ID": run_id, "PYTHONUNBUFFERED": "1"}
    agentops_endpoint = os.environ.get("AGENTOPS_ENDPOINT", "http://localhost:8000/ingest")
    env["AGENTOPS_ENDPOINT"] = agentops_endpoint

    try:
        proc = await asyncio.create_subprocess_exec(
            "uv", "run", "python", "-m", "agentops_research_agent",
            req.research_interest, req.date_from.isoformat(), req.date_to.isoformat(),
            "--model", req.model,
            cwd=str(_REPO_ROOT),
            env=env,
            stdout=asyncio.subprocess.DEVNULL,
        )
    except OSError as exc:
        async with _db_engine.SessionLocal() as s:
            failed_run = await s.get(Run, run_id)
            if failed_run is not None:
                failed_run.status = "failed"
                failed_run.ended_at = datetime.utcnow()
                failed_run.output = {"error": "Could not start the research agent"}
                s.add(failed_run)
                await s.commit()
        raise HTTPException(status_code=503, detail="Could not start the research agent") from exc
    asyncio.create_task(_watch_subprocess(proc, run_id))

    return {"run_id": run_id, "status": "running", "model": req.model}
