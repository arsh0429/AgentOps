from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


class Run(SQLModel, table=True):
    id: str = Field(primary_key=True)
    agent_name: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "running"
    prompt_sha: str | None = None
    model: str | None = None
    total_cost: float = 0.0
    total_tokens: int = 0
    input: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    output: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

class Span(SQLModel, table=True):
    id: str = Field(primary_key=True)
    trace_id: str = Field(default="", index=True)
    run_id: str = Field(index=True, foreign_key="run.id")
    parent_span_id: str | None = Field(default=None, index=True)
    name: str
    role: str | None = Field(default=None, index=True)
    started_at: datetime
    ended_at: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    events: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))


class TraceRunMapping(SQLModel, table=True):
    """Persistent correlation between an OTel trace and its AgentOps run.

    A provisional mapping is created when child spans arrive before their
    root. Once a span carrying the real ``agentops.run_id`` arrives, the
    mapping is resolved and every earlier span for the trace is reattached.
    """

    trace_id: str = Field(primary_key=True)
    run_id: str = Field(index=True, foreign_key="run.id")
    is_resolved: bool = False

class EvalResult(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "run_id", "eval_name", "mode", name="uq_evalresult_run_eval_mode"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True, foreign_key="run.id")
    eval_name: str = Field(index=True)
    mode: str
    score: float
    label: str | None = None
    rationale: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DriftStateRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    signal: str = Field(index=True)
    detector_name: str
    window: str
    value: float
    threshold: float
    is_drifted: bool
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DriftCheckpoint(SQLModel, table=True):
    """Last source snapshot processed by one drift signal worker."""

    key: str = Field(primary_key=True)
    source_fingerprint: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DriftReference(SQLModel, table=True):
    """Frozen detector reference data that must survive process restarts."""

    key: str = Field(primary_key=True)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Dataset(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    description: str | None = None

class DatasetRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset_id: str = Field(index=True, foreign_key="dataset.id")
    input: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    expected: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class RegressionRun(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset_id: str = Field(index=True, foreign_key="dataset.id")
    prompt_sha: str | None = None
    model: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "running"
    summary: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
