from __future__ import annotations

from collections.abc import Callable

from agentops.models import EvalMode

from .registry import EvalFn, EvalSpec, register


def eval(*, name: str, mode: EvalMode,
         judge_model: str | None = None) -> Callable[[EvalFn], EvalFn]:
    def decorator(fn: EvalFn) -> EvalFn:
        register(EvalSpec(name=name, mode=mode, fn=fn, judge_model=judge_model))
        return fn
    return decorator
