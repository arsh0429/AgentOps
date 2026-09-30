from __future__ import annotations

import re

from agentops.models import EvalMode, EvalResult, Golden, Run

from ..decorator import eval as agentops_eval


@agentops_eval(name="structural_completeness", mode=EvalMode.INVARIANT)
async def structural_completeness(run: Run, golden: Golden | None = None) -> EvalResult:
    digest = (run.output or {}).get("digest") if run.output else None
    if not isinstance(digest, str) or not digest.strip():
        return EvalResult(run_id=run.id, eval_name="structural_completeness",
                          mode=EvalMode.INVARIANT, score=0.0,
                          label="empty",
                          rationale="digest is missing or empty")
    sections = len(re.findall(r"^##\s+", digest, flags=re.M))
    has_summary = bool("summary" in digest.lower() or re.search(r"^- ", digest, flags=re.M))
    has_citation = bool(re.search(r"\d{4}\.\d{4,5}", digest))
    score = 1.0 if sections >= 1 and has_summary and has_citation else (0.5 if sections else 0.0)
    return EvalResult(run_id=run.id, eval_name="structural_completeness",
                      mode=EvalMode.INVARIANT, score=score,
                      label=f"sections={sections}",
                      rationale="checked section headers, bullet summaries, and citation format")
