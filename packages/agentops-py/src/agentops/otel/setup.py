from __future__ import annotations

import atexit
import os

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

from .exporter import AgentOpsSpanExporter


def install(
    endpoint: str | None = None,
    *,
    service_name: str = "agentops-agent",
    batched: bool = False,
) -> None:
    """Wire the AgentOps exporter into OTel's global tracer provider.

    By default uses a SimpleSpanProcessor — each span is exported synchronously
    when it ends. This avoids the buffering hazard where batched spans can be
    lost if the host process exits before BatchSpanProcessor flushes. For
    long-running processes (the AgentOps server itself, or production agents
    with high span throughput), set ``batched=True``.
    """
    provider = TracerProvider()
    exporter = AgentOpsSpanExporter(
        endpoint or os.getenv("AGENTOPS_ENDPOINT") or "http://localhost:8000/ingest"
    )
    processor: BatchSpanProcessor | SimpleSpanProcessor
    if batched:
        processor = BatchSpanProcessor(exporter)
    else:
        processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    # Belt-and-braces: force a final flush at interpreter shutdown so any
    # in-flight spans (including the root) are POSTed before exit.
    atexit.register(provider.shutdown)
