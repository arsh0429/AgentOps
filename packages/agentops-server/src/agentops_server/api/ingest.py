from __future__ import annotations

from typing import Any

from agentops.otel.conventions import AgentOps, GenAI
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlmodel import select

from ..db import engine as _db_engine
from ..db.models import Run, Span, TraceRunMapping
from ..ingestion.parser import compute_run_cost, decode_content, derive_run, parse_span
from ..orchestrator import run_invariants, run_online

_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


def _fallback_run_id(trace_id: str) -> str:
    return f"trace-{trace_id}"


def _apply_root_span(run: Run, root: Span, *, has_error_status: bool = False) -> None:
    """Merge authoritative root-span metadata into a run row."""
    attrs = root.attributes or {}
    run.agent_name = str(attrs.get(AgentOps.AGENT_NAME) or run.agent_name)
    run.started_at = root.started_at
    run.prompt_sha = attrs.get(AgentOps.PROMPT_SHA) or run.prompt_sha
    run.model = (
        attrs.get(GenAI.RESPONSE_MODEL)
        or attrs.get(GenAI.REQUEST_MODEL)
        or run.model
    )

    raw_input = attrs.get(AgentOps.INPUT)
    if raw_input is not None and not run.input:
        run.input = decode_content(raw_input)

    raw_output = attrs.get(AgentOps.OUTPUT)
    if raw_output is not None:
        run.output = decode_content(raw_output)

    if root.ended_at:
        run.ended_at = root.ended_at
        run.status = "succeeded"
        if has_error_status or (run.output and run.output.get("error")):
            run.status = "failed"


router = APIRouter()

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest(payload: dict[str, Any], bg: BackgroundTasks) -> dict[str, int]:
    raw_spans = payload.get("spans", [])
    if not isinstance(raw_spans, list) or any(not isinstance(r, dict) for r in raw_spans):
        raise HTTPException(status_code=422, detail="spans must be a list of objects")
    try:
        parsed = [parse_span(r) for r in raw_spans]
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail="invalid span payload") from exc
    error_span_ids = {
        raw["span_id"] for raw in raw_spans
        if isinstance(raw.get("status"), dict)
        and str(raw["status"].get("code", "")).upper() in {"ERROR", "2"}
    }

    # Group by the trace identifier now stored on every span. A missing trace
    # ID gets an isolated key so unrelated malformed spans are never combined.
    by_trace: dict[str, list[Span]] = {}
    for s in parsed:
        trace_id = s.trace_id or f"missing-{s.id}"
        s.trace_id = trace_id
        by_trace.setdefault(trace_id, []).append(s)

    inserted_spans = 0
    upserted_runs = 0
    affected_run_ids: set[str] = set()
    terminal_run_ids: set[str] = set()
    provisional_runs_to_remove: set[str] = set()

    async with _db_engine.SessionLocal() as session:
        for trace_id, spans in by_trace.items():
            mapping = await session.get(TraceRunMapping, trace_id)
            root = next((s for s in spans if s.parent_span_id is None), None)
            root_claim = root.run_id if root and root.run_id else ""
            any_claim = next((s.run_id for s in spans if s.run_id), "")

            # A root claim is authoritative. A child claim can resolve a new
            # or provisional mapping, but cannot overwrite an already-resolved
            # mapping for the same trace.
            claim = root_claim or any_claim
            if mapping is None:
                run_id = claim or _fallback_run_id(trace_id)
                resolved = bool(claim)
            elif root_claim and root_claim != mapping.run_id:
                run_id = root_claim
                resolved = True
            elif claim and not mapping.is_resolved:
                run_id = claim
                resolved = True
            else:
                run_id = mapping.run_id
                resolved = mapping.is_resolved

            old_provisional_run_id: str | None = None
            if mapping is not None and mapping.run_id != run_id and not mapping.is_resolved:
                old_provisional_run_id = mapping.run_id
                provisional_runs_to_remove.add(old_provisional_run_id)

            # Canonical trace correlation wins over per-span attributes.
            for span in spans:
                span.run_id = run_id

            existing = (await session.exec(select(Run).where(Run.id == run_id))).first()
            was_terminal = existing is not None and existing.status in _TERMINAL_STATUSES
            if existing is None:
                if root is not None:
                    existing = derive_run(spans)
                if existing is None:
                    existing = Run(
                        id=run_id,
                        agent_name="unknown",
                        started_at=min(span.started_at for span in spans),
                        status="running",
                    )
                session.add(existing)
                upserted_runs += 1
                # Insert the target run before reassigning foreign keys from
                # an earlier provisional run.
                await session.flush()

            if mapping is None:
                mapping = TraceRunMapping(
                    trace_id=trace_id,
                    run_id=run_id,
                    is_resolved=resolved,
                )
            else:
                mapping.run_id = run_id
                mapping.is_resolved = resolved
            session.add(mapping)

            if old_provisional_run_id is not None:
                earlier_spans = (await session.exec(
                    select(Span).where(Span.trace_id == trace_id)
                )).all()
                for earlier_span in earlier_spans:
                    earlier_span.run_id = run_id
                    session.add(earlier_span)

            if root is not None:
                _apply_root_span(existing, root, has_error_status=root.id in error_span_ids)
                session.add(existing)
                if not was_terminal and existing.status in _TERMINAL_STATUSES:
                    terminal_run_ids.add(run_id)

            for span in spans:
                in_db = await session.get(Span, span.id)
                if in_db is None:
                    session.add(span)
                    inserted_spans += 1
                else:
                    in_db.trace_id = span.trace_id
                    in_db.run_id = run_id
                    in_db.parent_span_id = span.parent_span_id
                    in_db.name = span.name
                    in_db.role = span.role
                    in_db.started_at = span.started_at
                    in_db.ended_at = span.ended_at
                    in_db.attributes = span.attributes
                    in_db.events = span.events
                    session.add(in_db)

            affected_run_ids.add(run_id)

        # Cost and token totals are derived from all persisted spans for each
        # affected run, not only from the latest ingestion batch.
        await session.flush()
        for run_id in affected_run_ids:
            all_spans = (await session.exec(
                select(Span).where(Span.run_id == run_id)
            )).all()
            run = await session.get(Run, run_id)
            if run is not None:
                run.total_cost, run.total_tokens = compute_run_cost(list(all_spans))
                session.add(run)

        # Once correlation is resolved, remove the synthetic run row that
        # existed only to satisfy early child-span ingestion.
        await session.flush()
        for provisional_run_id in provisional_runs_to_remove:
            remaining = (await session.exec(
                select(Span).where(Span.run_id == provisional_run_id)
            )).first()
            provisional = await session.get(Run, provisional_run_id)
            if remaining is None and provisional is not None:
                await session.delete(provisional)

        await session.commit()

    for run_id in terminal_run_ids:
        bg.add_task(run_invariants, run_id)
        bg.add_task(run_online, run_id)

    return {"runs": upserted_runs, "spans": inserted_spans}
