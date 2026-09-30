from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvalMode(StrEnum):
    ONLINE = "online"
    REGRESSION = "regression"
    INVARIANT = "invariant"


class DriftSignal(StrEnum):
    INPUT = "input"
    TOOL_CALL = "tool_call"
    QUALITY = "quality"


RunStatus = Literal["running", "succeeded", "failed"]


class Span(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    trace_id: str = ""
    run_id: str
    parent_span_id: str | None = None
    name: str
    role: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)


class Run(BaseModel):
    id: str
    agent_name: str
    started_at: datetime
    ended_at: datetime | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    prompt_sha: str | None = None
    model: str | None = None
    total_cost: float = 0.0
    total_tokens: int = 0
    status: RunStatus = "running"


class EvalResult(BaseModel):
    run_id: str
    eval_name: str
    mode: EvalMode
    score: float = Field(ge=0.0, le=1.0)
    label: str | None = None
    rationale: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Golden(BaseModel):
    id: str
    input: dict[str, Any]
    expected: dict[str, Any]


class DriftState(BaseModel):
    signal: DriftSignal
    detector_name: str
    window: str
    value: float
    threshold: float
    is_drifted: bool
    updated_at: datetime = Field(default_factory=datetime.utcnow)
