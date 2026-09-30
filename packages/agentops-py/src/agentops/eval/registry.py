from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from agentops.models import EvalMode, EvalResult, Golden, Run

EvalFn = Callable[[Run, Golden | None], Awaitable[EvalResult]]

@dataclass(frozen=True)
class EvalSpec:
    name: str
    mode: EvalMode
    fn: EvalFn
    judge_model: str | None = None

_REGISTRY: dict[str, EvalSpec] = {}

def register(spec: EvalSpec) -> None:
    if spec.name in _REGISTRY:
        raise ValueError(f"eval '{spec.name}' is already registered")
    _REGISTRY[spec.name] = spec

def get_eval(name: str) -> EvalSpec:
    return _REGISTRY[name]

def list_evals() -> list[str]:
    return sorted(_REGISTRY.keys())

def evals_for_mode(mode: EvalMode) -> list[EvalSpec]:
    return [s for s in _REGISTRY.values() if s.mode == mode]

def reset_for_tests() -> None:
    _REGISTRY.clear()
