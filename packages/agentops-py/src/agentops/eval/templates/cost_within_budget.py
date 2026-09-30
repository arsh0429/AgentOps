from __future__ import annotations

import os

from agentops.models import EvalMode, EvalResult, Golden, Run

from ..decorator import eval as agentops_eval

DEFAULT_BUDGET = float(os.getenv("AGENTOPS_COST_BUDGET_USD", "0.50"))

@agentops_eval(name="cost_within_budget", mode=EvalMode.INVARIANT)
async def cost_within_budget(run: Run, golden: Golden | None = None) -> EvalResult:
    cost = run.total_cost
    if cost <= DEFAULT_BUDGET:
        score, label = 1.0, "within"
    elif cost <= DEFAULT_BUDGET * 2:
        score, label = 0.5, "exceeded"
    else:
        score, label = 0.0, "blown"
    return EvalResult(run_id=run.id, eval_name="cost_within_budget",
                      mode=EvalMode.INVARIANT, score=score, label=label,
                      rationale=f"cost ${cost:.4f} vs budget ${DEFAULT_BUDGET:.2f}")
