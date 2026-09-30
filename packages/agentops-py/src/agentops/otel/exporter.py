from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from typing import Any

import httpx
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace.span import format_span_id, format_trace_id

from .redactor import NoOpRedactor, SpanRedactor

log = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = {408, 429}


def _is_retryable_status(status_code: int) -> bool:
    return status_code in _RETRYABLE_STATUS_CODES or 500 <= status_code <= 599


def _serialize_span(span: ReadableSpan) -> dict[str, Any]:
    ctx = span.get_span_context()
    if ctx is None:
        raise ValueError("cannot export span without a span context")
    parent = span.parent
    return {
        "trace_id": format_trace_id(ctx.trace_id),
        "span_id": format_span_id(ctx.span_id),
        "parent_span_id": format_span_id(parent.span_id) if parent else None,
        "name": span.name,
        "kind": str(span.kind),
        "start_time_unix_nano": span.start_time,
        "end_time_unix_nano": span.end_time,
        "attributes": dict(span.attributes or {}),
        "events": [
            {"name": e.name, "timestamp_unix_nano": e.timestamp,
             "attributes": dict(e.attributes or {})}
            for e in (span.events or [])
        ],
        "status": {"code": span.status.status_code.name,
                   "description": span.status.description or ""},
    }


class AgentOpsSpanExporter(SpanExporter):
    """OTel exporter that POSTs serialized spans to the AgentOps server.

    BatchSpanProcessor calls export() from a dedicated worker thread, so a
    synchronous HTTP client is correct here — it avoids the event-loop
    coordination issues that an async client would introduce when the host
    process is itself running asyncio (and would otherwise cause spans to
    be lost on process exit).
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:8000/ingest",
        timeout: float = 5.0,
        max_retries: int = 2,
        retry_backoff: float = 0.1,
        redactor: SpanRedactor | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if retry_backoff < 0:
            raise ValueError("retry_backoff must be non-negative")
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self._shutdown = False
        # Default to no-op for single-tenant dev usage. Production multi-tenant
        # deployments should pass an AllowlistRedactor (or a stricter custom
        # subclass) so customer prompts and model outputs never leave the
        # customer perimeter. See agentops.otel.redactor for the contract and
        # docs/architecture/multi-tenant.md for the deployment story.
        self.redactor: SpanRedactor = redactor or NoOpRedactor()
        self._client = httpx.Client(timeout=timeout)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            log.warning("agentops exporter rejected spans after shutdown")
            return SpanExportResult.FAILURE
        if not spans:
            return SpanExportResult.SUCCESS
        serialised = (_serialize_span(s) for s in spans)
        redacted = (self.redactor.redact(s) for s in serialised)
        payload = {"spans": [s for s in redacted if s is not None]}
        if not payload["spans"]:
            return SpanExportResult.SUCCESS
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                response = self._client.post(self.endpoint, json=payload)
            except httpx.HTTPError as exc:
                if attempt < self.max_retries:
                    self._backoff(attempt)
                    continue
                log.warning(
                    "agentops exporter failed after %d attempt(s): %s",
                    attempts,
                    exc,
                )
                return SpanExportResult.FAILURE
            except Exception:
                log.warning("agentops exporter failed unexpectedly", exc_info=True)
                return SpanExportResult.FAILURE

            if 200 <= response.status_code <= 299:
                return SpanExportResult.SUCCESS
            if _is_retryable_status(response.status_code) and attempt < self.max_retries:
                self._backoff(attempt)
                continue

            log.warning(
                "agentops exporter received HTTP %d after %d attempt(s)",
                response.status_code,
                attempt + 1,
            )
            return SpanExportResult.FAILURE

        return SpanExportResult.FAILURE

    def _backoff(self, attempt: int) -> None:
        delay = self.retry_backoff * (2**attempt)
        if delay:
            time.sleep(delay)

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        """Return after all exports submitted to this synchronous exporter finish."""
        return True

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        try:
            self._client.close()
        except Exception:
            log.warning("agentops exporter client failed to close", exc_info=True)
