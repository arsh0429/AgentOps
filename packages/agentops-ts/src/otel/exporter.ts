import { ExportResult, ExportResultCode } from "@opentelemetry/core";
import type { ReadableSpan, SpanExporter } from "@opentelemetry/sdk-trace-base";

interface SerializedSpan {
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
  name: string;
  kind: string;
  start_time_unix_nano: string;
  end_time_unix_nano: string;
  attributes: Record<string, unknown>;
  events: Array<{ name: string; timestamp_unix_nano: string; attributes: Record<string, unknown> }>;
  status: { code: string; description: string };
}

export interface AgentOpsSpanExporterOptions {
  endpoint?: string;
  timeoutMs?: number;
  maxRetries?: number;
  retryBackoffMs?: number;
  fetchImpl?: typeof fetch;
  logger?: Pick<Console, "warn">;
}

const RETRYABLE_STATUS_CODES = new Set([408, 429]);
const NANOSECONDS_PER_SECOND = 1_000_000_000n;

function isRetryableStatus(status: number): boolean {
  return RETRYABLE_STATUS_CODES.has(status) || (status >= 500 && status <= 599);
}

function asError(value: unknown): Error {
  return value instanceof Error ? value : new Error(String(value));
}

function hrTimeToUnixNano([seconds, nanoseconds]: [number, number]): string {
  return (
    BigInt(seconds) * NANOSECONDS_PER_SECOND + BigInt(nanoseconds)
  ).toString();
}

function _serialize(span: ReadableSpan): SerializedSpan {
  const ctx = span.spanContext();
  return {
    trace_id: ctx.traceId,
    span_id: ctx.spanId,
    parent_span_id: span.parentSpanId ?? null,
    name: span.name,
    kind: String(span.kind),
    start_time_unix_nano: hrTimeToUnixNano(span.startTime),
    end_time_unix_nano: hrTimeToUnixNano(span.endTime),
    attributes: { ...span.attributes },
    events: span.events.map(e => ({
      name: e.name,
      timestamp_unix_nano: hrTimeToUnixNano(e.time),
      attributes: { ...(e.attributes ?? {}) },
    })),
    status: { code: String(span.status.code), description: span.status.message ?? "" },
  };
}

export class AgentOpsSpanExporter implements SpanExporter {
  public readonly endpoint: string;
  private readonly timeoutMs: number;
  private readonly maxRetries: number;
  private readonly retryBackoffMs: number;
  private readonly fetchImpl: typeof fetch;
  private readonly logger: Pick<Console, "warn">;
  private readonly pending = new Set<Promise<void>>();
  private stopped = false;

  constructor(options: string | AgentOpsSpanExporterOptions = {}) {
    const resolved = typeof options === "string" ? { endpoint: options } : options;
    this.endpoint = resolved.endpoint
      ?? process.env.AGENTOPS_ENDPOINT
      ?? "http://localhost:8000/ingest";
    this.timeoutMs = resolved.timeoutMs ?? 5_000;
    this.maxRetries = resolved.maxRetries ?? 2;
    this.retryBackoffMs = resolved.retryBackoffMs ?? 100;
    this.fetchImpl = resolved.fetchImpl ?? fetch;
    this.logger = resolved.logger ?? console;

    if (this.timeoutMs <= 0) throw new Error("timeoutMs must be positive");
    if (!Number.isInteger(this.maxRetries) || this.maxRetries < 0) {
      throw new Error("maxRetries must be a non-negative integer");
    }
    if (this.retryBackoffMs < 0) throw new Error("retryBackoffMs must be non-negative");
  }

  export(spans: ReadableSpan[], cb: (result: ExportResult) => void): void {
    if (this.stopped) {
      const error = new Error("AgentOps exporter is shut down");
      this.logger.warn(error.message);
      cb({ code: ExportResultCode.FAILED, error });
      return;
    }
    if (spans.length === 0) {
      cb({ code: ExportResultCode.SUCCESS });
      return;
    }

    const payload = { spans: spans.map(_serialize) };
    const operation = (async () => {
      try {
        await this.sendWithRetry(payload);
        cb({ code: ExportResultCode.SUCCESS });
      } catch (value) {
        const error = asError(value);
        this.logger.warn(`AgentOps exporter failed: ${error.message}`);
        cb({ code: ExportResultCode.FAILED, error });
      }
    })();
    this.pending.add(operation);
    const removePending = () => this.pending.delete(operation);
    void operation.then(removePending, removePending);
  }

  async forceFlush(): Promise<void> {
    await Promise.allSettled([...this.pending]);
  }

  async shutdown(): Promise<void> {
    this.stopped = true;
    await this.forceFlush();
  }

  private async sendWithRetry(payload: { spans: SerializedSpan[] }): Promise<void> {
    const attempts = this.maxRetries + 1;
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      let response: Response;
      try {
        response = await this.fetchWithTimeout(payload);
      } catch (value) {
        const error = asError(value);
        if (attempt === this.maxRetries) {
          throw new Error(`failed after ${attempts} attempt(s): ${error.message}`, {
            cause: error,
          });
        }
        const delay = this.retryBackoffMs * (2 ** attempt);
        if (delay > 0) await new Promise((resolve) => setTimeout(resolve, delay));
        continue;
      }

      if (response.ok) return;
      if (!isRetryableStatus(response.status) || attempt === this.maxRetries) {
        throw new Error(`HTTP ${response.status} after ${attempt + 1} attempt(s)`);
      }
      const delay = this.retryBackoffMs * (2 ** attempt);
      if (delay > 0) await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  private async fetchWithTimeout(payload: { spans: SerializedSpan[] }): Promise<Response> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      return await this.fetchImpl(this.endpoint, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeout);
    }
  }
}
