from __future__ import annotations

import base64
import json
import os
from typing import Any, Literal, cast

from agentops.otel.conventions import GenAI
from anthropic import AsyncAnthropic
from anthropic.types import ImageBlockParam, TextBlock, TextBlockParam
from opentelemetry import trace as _trace

_client: AsyncAnthropic | None = None
_tracer = _trace.get_tracer("agentops_research_agent.llm")

# Chars stored in gen_ai.prompt / gen_ai.completion span attributes.
# Long enough to be useful; short enough to avoid bloating the DB.
_PROMPT_LIMIT = 4000
_COMPLETION_LIMIT = 2000


def _get() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()
    return _client


CHEAP = os.getenv("AGENTOPS_CHEAP_MODEL", "claude-haiku-4-5")
QUALITY = os.getenv("AGENTOPS_QUALITY_MODEL", "claude-sonnet-4-6")


async def text(prompt: str, *, model: str = CHEAP, system: str | None = None,
               max_tokens: int = 1024) -> str:
    with _tracer.start_as_current_span("llm.text") as span:
        span.set_attribute(GenAI.SYSTEM, "anthropic")
        span.set_attribute(GenAI.REQUEST_MODEL, model)
        span.set_attribute(GenAI.OPERATION_NAME, "chat")
        span.set_attribute("gen_ai.prompt", prompt[:_PROMPT_LIMIT])
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        msg = await _get().messages.create(**kwargs)
        result = "".join(b.text for b in msg.content if isinstance(b, TextBlock))
        span.set_attribute(GenAI.USAGE_INPUT_TOKENS, msg.usage.input_tokens)
        span.set_attribute(GenAI.USAGE_OUTPUT_TOKENS, msg.usage.output_tokens)
        span.set_attribute("gen_ai.completion", result[:_COMPLETION_LIMIT])
        return result


async def vision(prompt: str, image_bytes: bytes, content_type: str = "image/jpeg",
                 *, model: str = CHEAP, max_tokens: int = 512) -> str:
    if content_type not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
        raise ValueError(f"unsupported image content type: {content_type}")
    media_type = cast(Literal["image/jpeg", "image/png", "image/gif", "image/webp"],
                      content_type)
    with _tracer.start_as_current_span("llm.vision") as span:
        span.set_attribute(GenAI.SYSTEM, "anthropic")
        span.set_attribute(GenAI.REQUEST_MODEL, model)
        span.set_attribute(GenAI.OPERATION_NAME, "chat")
        span.set_attribute("gen_ai.prompt", prompt[:_PROMPT_LIMIT])
        span.set_attribute("gen_ai.content_type", content_type)
        image_b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        content: list[ImageBlockParam | TextBlockParam] = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": image_b64},
            },
            {"type": "text", "text": prompt},
        ]
        msg = await _get().messages.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": content}],
        )
        result = "".join(b.text for b in msg.content if isinstance(b, TextBlock))
        span.set_attribute(GenAI.USAGE_INPUT_TOKENS, msg.usage.input_tokens)
        span.set_attribute(GenAI.USAGE_OUTPUT_TOKENS, msg.usage.output_tokens)
        span.set_attribute("gen_ai.completion", result[:_COMPLETION_LIMIT])
        return result


async def json_call(prompt: str, *, model: str = CHEAP,
                    max_tokens: int = 512) -> dict[str, Any]:
    # text() is already instrumented — json_call's span is its child.
    raw = await text(prompt + "\n\nRespond with a single valid JSON object, no prose.",
                     model=model, max_tokens=max_tokens)
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in response: {raw!r}")
    parsed = json.loads(raw[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("model response must be a JSON object")
    return cast(dict[str, Any], parsed)
