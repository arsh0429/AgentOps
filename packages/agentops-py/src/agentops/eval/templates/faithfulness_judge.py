from __future__ import annotations

import json

from agentops.models import EvalMode, EvalResult, Golden, Run

from ..decorator import eval as agentops_eval
from ..judge import llm_judge


@agentops_eval(name="faithfulness_judge", mode=EvalMode.ONLINE, judge_model="claude-haiku-4-5")
async def faithfulness_judge(run: Run, golden: Golden | None = None) -> EvalResult:
    out = (run.output or {}).get("digest") if run.output else None
    sections = (run.output or {}).get("sections") if run.output else None
    if not out:
        return EvalResult(run_id=run.id, eval_name="faithfulness_judge",
                          mode=EvalMode.ONLINE, score=0.0,
                          label="missing", rationale="no digest")
    src = json.dumps(sections) if sections else "(no per-paper sections recorded)"
    return await llm_judge(
        instructions=("Score 0..1 how faithful the digest is to the per-paper summaries provided. "
                      "Penalize hallucinated facts, claims not present in the source summaries, "
                      "or numerical drift."),
        run_input=src,
        run_output=str(out)[:5000],
        model="claude-haiku-4-5",
        run_id=run.id, eval_name="faithfulness_judge",
    )
