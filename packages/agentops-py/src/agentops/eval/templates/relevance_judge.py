from __future__ import annotations

from agentops.models import EvalMode, EvalResult, Golden, Run

from ..decorator import eval as agentops_eval
from ..judge import llm_judge


@agentops_eval(name="relevance_judge", mode=EvalMode.ONLINE, judge_model="claude-haiku-4-5")
async def relevance_judge(run: Run, golden: Golden | None = None) -> EvalResult:
    inp = (run.input or {}).get("research_interest") if run.input else None
    out = (run.output or {}).get("digest") if run.output else None
    if not inp or not out:
        return EvalResult(run_id=run.id, eval_name="relevance_judge",
                          mode=EvalMode.ONLINE, score=0.0,
                          label="missing", rationale="input or output not present")
    instructions = (
        "Score 0..1 how well the research digest matches the requested research interest. "
        "Penalize off-topic papers, generic restatements, or thin coverage."
    )
    return await llm_judge(
        instructions=instructions,
        run_input=str(inp),
        run_output=str(out)[:5000],
        model="claude-haiku-4-5",
        run_id=run.id, eval_name="relevance_judge",
    )
