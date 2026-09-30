from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid

from agentops.otel import install as install_otel
from agentops.otel.conventions import AgentOps, GenAI
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from .planner import PaperSection, PlannerInput, build_planner_agent
from .run_context import bind_run_context, get_run_figures, reset_run_context
from .worker import DEFAULT_MODEL


def _compute_citation_attribution(sections: list[PaperSection]) -> dict[str, float]:
    """Per-paper share of the digest body length, normalised to sum to 1.

    Used by the attribution drift worker (server-side) to detect shifts in
    *which sources* the agent leans on, even when output quality and
    tool-call patterns look unchanged. Section length is the cheapest
    available proxy for "how much this paper contributed"; embedding-based
    attribution is a follow-up.
    """
    weights: dict[str, float] = {}
    for s in sections:
        weights[s.paper_id] = weights.get(s.paper_id, 0.0) + len(s.summary or "")
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in weights.items()}


async def _main(
    research_interest: str,
    date_from: str,
    date_to: str,
    model: str = DEFAULT_MODEL,
) -> None:
    install_otel()
    tracer = trace.get_tracer("agentops_research_agent.cli")
    run_id = os.environ.get("AGENTOPS_RUN_ID") or f"live-{uuid.uuid4().hex[:10]}"
    data_source = "arxiv-abstracts" if os.getenv("AGENTOPS_USE_REAL_ARXIV") else "synthetic-mock"
    run_context_token = bind_run_context(run_id)

    try:
        with tracer.start_as_current_span("agentops_research_agent.run") as root:
            root.set_attribute(AgentOps.RUN_ID, run_id)
            root.set_attribute(AgentOps.AGENT_NAME, "arxiv-planner")
            root.set_attribute(AgentOps.ROLE, "planner")
            root.set_attribute(GenAI.REQUEST_MODEL, model)
            root.set_attribute(
                AgentOps.INPUT,
                json.dumps({
                    "research_interest": research_interest,
                    "date_from": date_from,
                    "date_to": date_to,
                    "data_source": data_source,
                }),
            )

            agent = build_planner_agent(model)
            deps = PlannerInput(
                research_interest=research_interest,
                date_from=date_from, date_to=date_to,
            )
            user_prompt = (
                f"Research interest: {research_interest}\n"
                f"Date window: {date_from} to {date_to}\n"
                "Produce the digest now."
            )
            try:
                res = await agent.run(user_prompt, deps=deps)
            except Exception as exc:
                # Mark the run as failed so the digest endpoint and consumer
                # UI can stop polling and surface a clear error rather than
                # spin forever.
                root.set_attribute(
                    AgentOps.OUTPUT,
                    json.dumps({
                        "digest": "",
                        "candidates": [],
                        "sections": [],
                        "figures": {},
                        "data_source": data_source,
                        "error": f"{type(exc).__name__}: {exc}",
                    }),
                )
                root.set_status(StatusCode.ERROR, str(exc))
                print(json.dumps({"run_id": run_id, "error": str(exc)}, indent=2),
                      file=sys.stderr)
                raise SystemExit(1) from exc

            # LLM-populated figures are a fallback. The execution context is
            # populated directly by tools and workers, so it wins with exact
            # filenames without being shared with another concurrent run.
            llm_figures = {
                pid: [f.model_dump() for f in figs]
                for pid, figs in res.output.figures.items()
            }
            merged_figures = {**llm_figures, **get_run_figures()}

            attribution = _compute_citation_attribution(res.output.sections)
            root.set_attribute(
                AgentOps.OUTPUT,
                json.dumps({
                    "digest": res.output.digest,
                    "candidates": [c.model_dump() for c in res.output.candidates],
                    "sections": [s.model_dump() for s in res.output.sections],
                    "figures": merged_figures,
                    "data_source": data_source,
                    "attribution": attribution,
                }),
            )
            if attribution:
                root.set_attribute(AgentOps.ATTRIBUTION, json.dumps(attribution))
    finally:
        reset_run_context(run_context_token)

    print(json.dumps({
        "run_id": run_id,
        "digest": res.output.digest,
        "candidates": [c.model_dump() for c in res.output.candidates],
    }, indent=2))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an arXiv research digest.")
    parser.add_argument(
        "research_interest",
        nargs="?",
        default="concept drift detection in streaming ML",
    )
    parser.add_argument("date_from", nargs="?", default="2024-01-01")
    parser.add_argument("date_to", nargs="?", default="2024-12-31")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(_main(args.research_interest, args.date_from, args.date_to, args.model))
