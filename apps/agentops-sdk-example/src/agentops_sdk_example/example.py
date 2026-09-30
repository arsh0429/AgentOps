"""A minimal agent loop using the Anthropic SDK directly + manual OTel/GenAI
instrumentation, ingested by AgentOps.

Demonstrates: drop-in instrumentation with no agent framework; tool use via
the Anthropic messages API; AgentOps run/role/agent_name attributes.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from agentops.otel import install as install_otel
from agentops.otel.conventions import AgentOps, GenAI
from anthropic import AsyncAnthropic
from opentelemetry import trace
from opentelemetry.trace import StatusCode

TOOLS = [
    {
        "name": "search_arxiv",
        "description": "Mock search returning a couple of paper ids.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]

def _tool_dispatch(name: str, args: dict[str, Any]) -> str:
    if name == "search_arxiv":
        return json.dumps([
            {"id": "2401.00001", "title": "ADWIN-2"},
            {"id": "2402.00012", "title": "Page-Hinkley revisited"},
        ])
    return ""

async def run(research_interest: str) -> str:
    install_otel()
    tracer = trace.get_tracer("agentops-sdk-example")
    run_id = f"bare-{uuid.uuid4().hex[:10]}"
    client = AsyncAnthropic()

    with tracer.start_as_current_span("agent") as root:
        root.set_attribute(AgentOps.RUN_ID, run_id)
        root.set_attribute(AgentOps.AGENT_NAME, "agentops-sdk-example")
        root.set_attribute(AgentOps.ROLE, "agent")
        root.set_attribute(AgentOps.INPUT, json.dumps({"research_interest": research_interest}))

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": (
                f"Find 1-2 papers on: {research_interest}. Use the search_arxiv tool."
            )}
        ]
        for _ in range(3):
            with tracer.start_as_current_span("model.call") as cs:
                cs.set_attribute(GenAI.SYSTEM, "anthropic")
                cs.set_attribute(GenAI.REQUEST_MODEL, "claude-haiku-4-5")
                cs.set_attribute(GenAI.OPERATION_NAME, "chat")
                resp = await client.messages.create(
                    model="claude-haiku-4-5", max_tokens=512,
                    tools=TOOLS, messages=messages,
                )
                cs.set_attribute(GenAI.RESPONSE_MODEL, resp.model)
                cs.set_attribute(GenAI.USAGE_INPUT_TOKENS, resp.usage.input_tokens)
                cs.set_attribute(GenAI.USAGE_OUTPUT_TOKENS, resp.usage.output_tokens)
            if resp.stop_reason == "tool_use":
                tool_uses = [b for b in resp.content if b.type == "tool_use"]
                tool_results = []
                for tu in tool_uses:
                    with tracer.start_as_current_span(tu.name) as ts:
                        ts.set_attribute(AgentOps.RUN_ID, run_id)
                        ts.set_attribute(AgentOps.ROLE, "tool")
                        ts.set_attribute(GenAI.TOOL_NAME, tu.name)
                        out = _tool_dispatch(tu.name, dict(tu.input or {}))
                        tool_results.append({
                            "type": "tool_result", "tool_use_id": tu.id, "content": out,
                        })
                messages.append({"role": "assistant", "content": resp.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                final_text = "".join(b.text for b in resp.content if b.type == "text")
                root.set_attribute(AgentOps.OUTPUT, json.dumps({
                    "answer": final_text, "data_source": "synthetic-mock",
                }))
                return final_text
        root.set_attribute(AgentOps.OUTPUT, json.dumps({"error": "tool loop exhausted"}))
        root.set_status(StatusCode.ERROR, "tool loop exhausted")
        raise RuntimeError("tool loop exhausted")

if __name__ == "__main__":
    print(asyncio.run(run("concept drift in streaming ML")))
