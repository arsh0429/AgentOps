from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
from agentops.otel.exporter import AgentOpsSpanExporter, _serialize_span
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanContext, TraceFlags
from opentelemetry.trace.span import format_span_id, format_trace_id


def _make_readable_span() -> ReadableSpan:
    ctx = SpanContext(trace_id=0x12345678901234567890123456789012,
                      span_id=0xabcdef0123456789, is_remote=False,
                      trace_flags=TraceFlags(0x01))
    return ReadableSpan(
        name="planner.dispatch_worker",
        context=ctx,
        parent=None,
        attributes={"gen_ai.system": "anthropic", "gen_ai.request.model": "claude-haiku-4-5",
                    "agentops.role": "planner", "agentops.run_id": "run-001"},
        start_time=int(datetime(2026, 5, 6, 12, 0, 0).timestamp() * 1e9),
        end_time=int(datetime(2026, 5, 6, 12, 0, 1).timestamp() * 1e9),
    )

def test_serialize_span_emits_genai_attributes() -> None:
    span = _make_readable_span()
    payload = _serialize_span(span)
    assert payload["name"] == "planner.dispatch_worker"
    assert payload["attributes"]["gen_ai.system"] == "anthropic"
    assert payload["attributes"]["agentops.role"] == "planner"
    assert payload["span_id"] == format_span_id(0xabcdef0123456789)
    assert payload["trace_id"] == format_trace_id(0x12345678901234567890123456789012)

def test_exporter_posts_to_endpoint() -> None:
    span = _make_readable_span()
    exporter = AgentOpsSpanExporter(endpoint="http://localhost:8000/ingest")
    fake_response = MagicMock(status_code=200)
    with patch.object(exporter._client, "post", return_value=fake_response) as p:
        result = exporter.export([span])
    assert result.name == "SUCCESS"
    p.assert_called_once()
    body = p.call_args.kwargs["json"]
    assert "spans" in body
    assert body["spans"][0]["attributes"]["gen_ai.system"] == "anthropic"


def test_exporter_retries_retryable_http_failure_then_succeeds() -> None:
    exporter = AgentOpsSpanExporter(max_retries=2, retry_backoff=0)
    responses = [MagicMock(status_code=503), MagicMock(status_code=202)]
    with patch.object(exporter._client, "post", side_effect=responses) as post:
        result = exporter.export([_make_readable_span()])
    assert result.name == "SUCCESS"
    assert post.call_count == 2


def test_exporter_does_not_retry_non_retryable_http_failure(caplog) -> None:
    exporter = AgentOpsSpanExporter(max_retries=2, retry_backoff=0)
    with patch.object(
        exporter._client, "post", return_value=MagicMock(status_code=400)
    ) as post:
        result = exporter.export([_make_readable_span()])
    assert result.name == "FAILURE"
    assert post.call_count == 1
    assert "HTTP 400" in caplog.text


def test_exporter_bounds_transport_retries_and_logs_final_failure(caplog) -> None:
    exporter = AgentOpsSpanExporter(max_retries=2, retry_backoff=0)
    error = httpx.ConnectError("server unavailable")
    with patch.object(exporter._client, "post", side_effect=error) as post:
        result = exporter.export([_make_readable_span()])
    assert result.name == "FAILURE"
    assert post.call_count == 3
    assert "failed after 3 attempt(s)" in caplog.text


def test_exporter_uses_timeout_and_flushes_before_clean_shutdown() -> None:
    exporter = AgentOpsSpanExporter(timeout=1.25)
    assert exporter._client.timeout.connect == 1.25
    assert exporter.force_flush()
    with patch.object(exporter._client, "close") as close:
        exporter.shutdown()
        exporter.shutdown()
    close.assert_called_once()
    assert exporter.export([_make_readable_span()]).name == "FAILURE"


def test_exporter_validates_retry_settings() -> None:
    for kwargs in (
        {"timeout": 0},
        {"max_retries": -1},
        {"retry_backoff": -0.1},
    ):
        try:
            AgentOpsSpanExporter(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {kwargs}")
