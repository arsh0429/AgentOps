"""Redaction protocol for the AgentOps SDK exporter.

In the multi-tenant deployment model documented at
``docs/architecture/multi-tenant.md``, customers run the agent runtime on
their own infrastructure. Raw payloads — user prompts, model outputs,
retrieved documents — must never leave the customer's perimeter. Telemetry
that *can* leave (timings, tool names, eval scores, drift values) is
shipped to the AgentOps provider's control plane via this exporter.

A redactor is the seam where that policy is enforced. Each serialised span
is passed through `redact(span_dict)` before egress; the redactor returns
the span dict (mutated or fresh) to send, or ``None`` to drop the span
entirely.

The opt-in ``AllowlistRedactor`` preserves a conservative set of
attributes — span structure, GenAI usage / tool names, AgentOps
role/run-id markers, and eval scores — and drops everything else. Most
notably it drops ``agentops.input``, ``agentops.output``, and any
attribute prefixed with ``pii.`` or ``confidential.``. Customers can
register their own redactor by passing it to ``AgentOpsSpanExporter``::

    from agentops.otel import AgentOpsSpanExporter, AllowlistRedactor

    exporter = AgentOpsSpanExporter(
        endpoint="https://agentops.example.com/ingest",
        redactor=AllowlistRedactor(),
    )

This module is the single source of truth for the egress contract. It is
deliberately small — production deployments will swap in a richer policy
that reads from configuration, but the surface area stays the same.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SpanRedactor(Protocol):
    """Filters / transforms a serialised span before it egresses.

    Returns the (possibly mutated) span dict to send, or ``None`` to drop
    the span entirely. Implementations must be idempotent and side-effect
    free — they may be called from a background span-processor thread.
    """

    def redact(self, span: dict[str, Any]) -> dict[str, Any] | None: ...


# Default allowlist for attributes that may leave the customer perimeter.
# Anything not on this list is dropped. Span structure (trace_id, span_id,
# name, parent, timing) is always preserved — only the ``attributes`` and
# ``events`` payloads are filtered.
DEFAULT_ATTRIBUTE_ALLOWLIST: frozenset[str] = frozenset({
    # Structural agent metadata — needed for the platform's traces and drift.
    "agentops.run_id",
    "agentops.role",
    "agentops.agent_name",
    "agentops.prompt_sha",
    # OpenTelemetry GenAI semantic conventions — model and usage data the
    # provider needs for cost/latency monitoring without seeing prompts.
    "gen_ai.system",
    "gen_ai.request.model",
    "gen_ai.response.model",
    "gen_ai.usage.input_tokens",
    "gen_ai.usage.output_tokens",
    "gen_ai.operation.name",
    "gen_ai.tool.name",
    "gen_ai.tool.call.id",
})


class AllowlistRedactor:
    """Privacy-focused redactor: ship structural signal, drop content.

    Allowed by default: the attributes in ``DEFAULT_ATTRIBUTE_ALLOWLIST``
    plus any attribute the constructor caller adds via ``extra_allowlist``.
    Dropped by default: everything else, including ``agentops.input``,
    ``agentops.output``, ``agentops.eval_result`` rationale text, and any
    attribute prefixed with ``pii.`` or ``confidential.``.

    Eval scores ride out under a small carve-out: attributes whose name
    matches ``agentops.eval.<name>.score`` are kept (numeric only). The
    matching rationale text is dropped.
    """

    name = "allowlist"

    def __init__(self, *, extra_allowlist: frozenset[str] | set[str] | None = None) -> None:
        self.allowlist = DEFAULT_ATTRIBUTE_ALLOWLIST | frozenset(extra_allowlist or set())

    def _allowed(self, key: str) -> bool:
        if key.startswith("pii.") or key.startswith("confidential."):
            return False
        if key in self.allowlist:
            return True
        # Eval score carve-out: agentops.eval.<name>.score is numeric, ship.
        if key.startswith("agentops.eval.") and key.endswith(".score"):
            return True
        return False

    def redact(self, span: dict[str, Any]) -> dict[str, Any] | None:
        attrs = span.get("attributes") or {}
        filtered = {k: v for k, v in attrs.items() if self._allowed(k)}
        out = dict(span)
        out["attributes"] = filtered
        # Events can carry the same content we want to redact — wipe their
        # attributes too, keep only the event name + timestamp.
        events = span.get("events") or []
        out["events"] = [
            {"name": e.get("name", ""),
             "timestamp_unix_nano": e.get("timestamp_unix_nano", 0),
             "attributes": {}}
            for e in events
        ]
        return out


class NoOpRedactor:
    """Pass-through redactor — ships everything as-is.

    Default for single-tenant dev deployments where the SDK and the server
    sit in the same trust boundary. Production multi-tenant deployments
    should always use ``AllowlistRedactor`` or a stricter custom subclass.
    """

    name = "noop"

    def redact(self, span: dict[str, Any]) -> dict[str, Any] | None:
        return span
