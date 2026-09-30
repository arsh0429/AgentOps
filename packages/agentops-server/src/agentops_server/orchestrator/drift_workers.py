from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
from datetime import UTC, datetime

import numpy as np
from agentops.drift import ADWIN, MMDDetector, PSIDetector
from sqlmodel import col, select

from ..db import engine as _db_engine
from ..db.models import (
    DriftCheckpoint,
    DriftReference,
    DriftStateRow,
    EvalResult,
    Span,
)
from ..db.models import Run as RunRow
from .input_encoding import (
    LEXICAL_ENCODER_NAME,
    LEXICAL_FEATURE_DIMENSIONS,
    lexical_hash_vector,
)

log = logging.getLogger(__name__)

_QUALITY_WINDOW = 500
_TOOL_QUERY_WINDOW = 500
_TOOL_DETECTOR_WINDOW = 200
_INPUT_REFERENCE_WINDOW = 50
_INPUT_RECENT_WINDOW = 50

# Tunables for attribution drift. Reference threshold is intentionally low
# so the worker stops returning "no data yet" after a small number of live
# runs in dev. Production tuning would raise this and add a manual reset
# endpoint when the agent is intentionally retrained.
_ATTRIBUTION_REFERENCE_THRESHOLD = 10
_ATTRIBUTION_RECENT_WINDOW = 50
_ATTRIBUTION_PSI_THRESHOLD = 0.2
_ATTRIBUTION_SMOOTHING = 1e-4

_TOOL_REFERENCE: dict[str, dict[str, float]] = {
    "planner": {"search_arxiv": 1.0, "fetch_metadata": 4.0,
                "score_candidate": 4.0, "compose_digest": 1.0,
                "dispatch_worker": 3.0},
    "worker":  {"fetch_paper": 3.0, "extract_figures": 3.0,
                "summarize": 3.0, "query_paper": 0.5},
}


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


async def _persist_state_if_changed(
    *, checkpoint_key: str, source_fingerprint: str, state: DriftStateRow
) -> bool:
    """Persist one point only when the detector's source snapshot changed."""
    async with _db_engine.SessionLocal() as session:
        checkpoint = await session.get(DriftCheckpoint, checkpoint_key)
        if checkpoint is not None and checkpoint.source_fingerprint == source_fingerprint:
            return False

        session.add(state)
        if checkpoint is None:
            checkpoint = DriftCheckpoint(
                key=checkpoint_key,
                source_fingerprint=source_fingerprint,
            )
        else:
            checkpoint.source_fingerprint = source_fingerprint
            checkpoint.updated_at = datetime.now(UTC).replace(tzinfo=None)
        session.add(checkpoint)
        await session.commit()
        return True


async def quality_drift_tick() -> None:
    """Rebuild ADWIN from a bounded recent quality window."""
    async with _db_engine.SessionLocal() as s:
        rows_desc = (await s.exec(
            select(EvalResult)
            .where(EvalResult.eval_name == "relevance_judge")
            .order_by(col(EvalResult.created_at).desc())
            .limit(_QUALITY_WINDOW)
        )).all()
    rows = list(reversed(rows_desc))
    if not rows:
        return

    source_fingerprint = _fingerprint([
        (row.id, row.score, row.created_at) for row in rows
    ])
    det = ADWIN(delta=1.0)
    last_drifted = False
    for r in rows:
        last_drifted = det.update(float(r.score)) or last_drifted

    await _persist_state_if_changed(
        checkpoint_key="quality:relevance_judge",
        source_fingerprint=source_fingerprint,
        state=DriftStateRow(
            signal="quality", detector_name="adwin",
            window=str(len(rows)), value=det.value(),
            threshold=det.threshold(),
            is_drifted=det.is_drifted() or last_drifted,
        ),
    )

async def tool_call_drift_tick() -> None:
    """Rebuild PSI per role from bounded recent tool-call spans."""
    async with _db_engine.SessionLocal() as s:
        spans_desc = (await s.exec(
            select(Span)
            .where(col(Span.role).in_(["planner", "worker"]))
            .order_by(col(Span.started_at).desc())
            .limit(_TOOL_QUERY_WINDOW)
        )).all()
    spans = list(reversed(spans_desc))
    by_role: dict[str, list[Span]] = {"planner": [], "worker": []}
    for sp in spans:
        role = sp.role
        if role in by_role and sp.parent_span_id is not None:
            by_role[role].append(sp)
    for role, role_spans in by_role.items():
        if not role_spans:
            continue
        source_fingerprint = _fingerprint([
            (span.id, span.name, span.started_at) for span in role_spans
        ])
        det = PSIDetector(
            reference=_TOOL_REFERENCE[role],
            threshold=0.2,
            window=_TOOL_DETECTOR_WINDOW,
        )
        for span in role_spans:
            det.update(span.name)
        await _persist_state_if_changed(
            checkpoint_key=f"tool_call:{role}",
            source_fingerprint=source_fingerprint,
            state=DriftStateRow(
                signal="tool_call", detector_name=f"psi:{role}",
                window=str(len(role_spans)), value=det.value(),
                threshold=det.threshold(), is_drifted=det.is_drifted(),
            ),
        )

async def input_drift_tick() -> None:
    """Rebuild lexical-input MMD from fixed reference and recent windows."""
    async with _db_engine.SessionLocal() as s:
        reference_rows = (await s.exec(
            select(RunRow)
            .order_by(col(RunRow.started_at))
            .limit(_INPUT_REFERENCE_WINDOW)
        )).all()
        recent_rows_desc = (await s.exec(
            select(RunRow)
            .order_by(col(RunRow.started_at).desc())
            .limit(_INPUT_RECENT_WINDOW)
        )).all()
    recent_rows = list(reversed(recent_rows_desc))
    if len(reference_rows) < _INPUT_REFERENCE_WINDOW or not recent_rows:
        return

    reference_interests = [
        str((row.input or {}).get("research_interest", "")) for row in reference_rows
    ]
    recent_interests = [
        str((row.input or {}).get("research_interest", "")) for row in recent_rows
    ]
    source_fingerprint = _fingerprint({
        "encoder": LEXICAL_ENCODER_NAME,
        "dimensions": LEXICAL_FEATURE_DIMENSIONS,
        "reference": [
            (row.id, interest, row.started_at)
            for row, interest in zip(reference_rows, reference_interests, strict=True)
        ],
        "recent": [
            (row.id, interest, row.started_at)
            for row, interest in zip(recent_rows, recent_interests, strict=True)
        ],
    })

    refs = np.stack(
        [lexical_hash_vector(interest) for interest in reference_interests],
        axis=0,
    )
    detector = MMDDetector(
        reference=refs,
        threshold=0.05,
        window=_INPUT_RECENT_WINDOW,
    )
    last_drifted = False
    for interest in recent_interests:
        last_drifted = detector.update(lexical_hash_vector(interest)) or last_drifted

    await _persist_state_if_changed(
        checkpoint_key=f"input:mmd_rbf:{LEXICAL_ENCODER_NAME}",
        source_fingerprint=source_fingerprint,
        state=DriftStateRow(
            signal="input", detector_name="mmd_rbf",
            window=str(len(recent_interests)),
            value=detector.value(),
            threshold=detector.threshold(),
            is_drifted=detector.is_drifted() or last_drifted,
        ),
    )

def _aggregate_attribution(runs: list[RunRow]) -> dict[str, float]:
    """Sum per-paper attribution weights across runs, then renormalise to 1."""
    agg: dict[str, float] = {}
    for r in runs:
        attr = (r.output or {}).get("attribution") if r.output else None
        if not isinstance(attr, dict):
            continue
        for paper_id, weight in attr.items():
            try:
                w = float(weight)
            except (TypeError, ValueError):
                continue
            agg[str(paper_id)] = agg.get(str(paper_id), 0.0) + w
    total = sum(agg.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in agg.items()}


def _psi(current: dict[str, float], reference: dict[str, float],
         smoothing: float) -> float:
    """PSI(current || reference) over the union of paper_ids.

    Same equation the streaming PSIDetector uses, but operating directly
    on aggregated distributions rather than a sample buffer. Citation
    attribution is naturally per-run (a distribution per digest), not a
    stream of single categorical samples.
    """
    keys = set(current) | set(reference)
    psi = 0.0
    for k in keys:
        cur = max(current.get(k, 0.0), smoothing)
        ref = max(reference.get(k, 0.0), smoothing)
        psi += (cur - ref) * math.log(cur / ref)
    return float(psi)


async def attribution_drift_tick() -> None:
    """PSI on the per-paper citation attribution distribution.

    Reference is the aggregate over the first N succeeded runs that emit a
    non-empty attribution dict; once frozen, every subsequent tick compares
    the aggregate over the most-recent runs against it. Detects the agent
    shifting which sources it relies on, even when output quality and
    tool-call patterns look unchanged.
    """
    async with _db_engine.SessionLocal() as s:
        reference_row = await s.get(DriftReference, "attribution:citation_weight")
        if reference_row is None:
            oldest_runs = (await s.exec(
                select(RunRow)
                .where(RunRow.status == "succeeded")
                .order_by(col(RunRow.started_at))
                .limit(500)
            )).all()
            eligible_reference = [
                run for run in oldest_runs
                if run.output
                and isinstance(run.output.get("attribution"), dict)
                and run.output["attribution"]
            ]
            if len(eligible_reference) < _ATTRIBUTION_REFERENCE_THRESHOLD:
                return
            reference = _aggregate_attribution(
                eligible_reference[:_ATTRIBUTION_REFERENCE_THRESHOLD]
            )
            if not reference:
                return
            reference_row = DriftReference(
                key="attribution:citation_weight",
                payload=reference,
            )
            s.add(reference_row)
            await s.commit()
        else:
            reference = {
                str(paper_id): float(weight)
                for paper_id, weight in reference_row.payload.items()
            }

        recent_runs = (await s.exec(
            select(RunRow)
            .where(RunRow.status == "succeeded")
            .order_by(col(RunRow.started_at).desc())
            .limit(500)
        )).all()

    eligible_recent = [
        run for run in recent_runs
        if run.output
        and isinstance(run.output.get("attribution"), dict)
        and run.output["attribution"]
    ][:_ATTRIBUTION_RECENT_WINDOW]
    if not eligible_recent:
        return

    current = _aggregate_attribution(eligible_recent)
    if not current:
        return

    source_fingerprint = _fingerprint([
        (run.id, (run.output or {}).get("attribution"), run.started_at)
        for run in eligible_recent
    ])
    psi = _psi(current, reference, _ATTRIBUTION_SMOOTHING)
    drifted = psi >= _ATTRIBUTION_PSI_THRESHOLD

    await _persist_state_if_changed(
        checkpoint_key="attribution:psi:citation_weight",
        source_fingerprint=source_fingerprint,
        state=DriftStateRow(
            signal="attribution",
            detector_name="psi:citation_weight",
            window=str(len(eligible_recent)),
            value=psi,
            threshold=_ATTRIBUTION_PSI_THRESHOLD,
            is_drifted=drifted,
        ),
    )


async def drift_loop(interval_s: float = 5.0) -> None:
    while True:
        try:
            await asyncio.gather(
                quality_drift_tick(),
                tool_call_drift_tick(),
                input_drift_tick(),
                attribution_drift_tick(),
            )
        except Exception:
            log.exception("drift tick failed")
        await asyncio.sleep(interval_s)
