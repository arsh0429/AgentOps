from __future__ import annotations

import json

from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from agentops.models import EvalMode, EvalResult

_client: AsyncAnthropic | None = None

def _get() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()
    return _client

async def llm_judge(*, instructions: str, run_input: str, run_output: str,
                   model: str = "claude-haiku-4-5", run_id: str,
                   eval_name: str, mode: EvalMode = EvalMode.ONLINE) -> EvalResult:
    """Score an output against an instruction. Returns 0..1 + rationale."""
    prompt = (
        f"{instructions}\n\n"
        f"Input given to the system:\n{run_input}\n\n"
        f"System output:\n{run_output}\n\n"
        "Return a single JSON object with fields:\n"
        "  score: float in [0, 1]\n"
        "  label: short tag string\n"
        "  rationale: one or two sentences\n"
        "No prose outside the JSON."
    )
    msg = await _get().messages.create(
        model=model, max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if isinstance(b, TextBlock))
    s, e = text.find("{"), text.rfind("}")
    data = json.loads(text[s:e + 1])
    return EvalResult(
        run_id=run_id, eval_name=eval_name, mode=mode,
        score=float(max(0.0, min(1.0, float(data["score"])))),
        label=str(data.get("label", "")) or None,
        rationale=str(data.get("rationale", "")) or None,
    )
