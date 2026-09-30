from typing import Any

import pytest
from agentops_research_agent import planner


class _CaptureExporter:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

    def export(self, spans):
        from agentops.otel.exporter import _serialize_span
        self.calls.append([_serialize_span(s) for s in spans])
        from opentelemetry.sdk.trace.export import SpanExportResult
        return SpanExportResult.SUCCESS

    def shutdown(self): pass

@pytest.mark.live
async def test_planner_emits_agentops_attributes(monkeypatch) -> None:
    cap = _CaptureExporter()
    monkeypatch.setattr("agentops.otel.setup.AgentOpsSpanExporter", lambda *a, **k: cap)
    import agentops.otel as otel
    otel.install()
    agent = planner.build_planner_agent()
    await agent.run(planner.PlannerInput(
        research_interest="concept drift",
        date_from="2024-01-01", date_to="2024-12-31",
    ))
    flat = [s for batch in cap.calls for s in batch]
    assert any(s["attributes"].get("agentops.role") == "planner" for s in flat)
