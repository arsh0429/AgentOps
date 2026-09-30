import { ExportResultCode } from "@opentelemetry/core";
import type { ReadableSpan } from "@opentelemetry/sdk-trace-base";
import { describe, expect, it, vi } from "vitest";

import { AgentOpsSpanExporter } from "./exporter";

function span(): ReadableSpan {
  return {
    spanContext: () => ({ traceId: "1".repeat(32), spanId: "2".repeat(16) }),
    parentSpanId: undefined,
    name: "llm.request",
    kind: 0,
    startTime: [1, 2],
    endTime: [3, 4],
    attributes: { "gen_ai.request.model": "claude-sonnet-4-6" },
    events: [],
    status: { code: 1 },
  } as unknown as ReadableSpan;
}

function response(status: number): Response {
  return { ok: status >= 200 && status <= 299, status } as Response;
}

async function exportOnce(exporter: AgentOpsSpanExporter): Promise<number> {
  return await new Promise((resolve) => {
    exporter.export([span()], (result) => resolve(result.code));
  });
}

describe("AgentOpsSpanExporter", () => {
  it("serializes span and event nanoseconds as exact decimal strings", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response(202));
    const exporter = new AgentOpsSpanExporter({ fetchImpl });
    const preciseSpan = {
      ...span(),
      startTime: [1_777_777_777, 987_654_321],
      endTime: [1_777_777_778, 123],
      events: [{
        name: "tool.completed",
        time: [1_777_777_777, 555_555_555],
        attributes: {},
      }],
    } as unknown as ReadableSpan;

    await new Promise<void>((resolve) => {
      exporter.export([preciseSpan], () => resolve());
    });

    const request = fetchImpl.mock.calls[0]?.[1] as RequestInit;
    const payload = JSON.parse(String(request.body)) as {
      spans: Array<{
        start_time_unix_nano: string;
        end_time_unix_nano: string;
        events: Array<{ timestamp_unix_nano: string }>;
      }>;
    };
    expect(payload.spans[0]?.start_time_unix_nano).toBe("1777777777987654321");
    expect(payload.spans[0]?.end_time_unix_nano).toBe("1777777778000000123");
    expect(payload.spans[0]?.events[0]?.timestamp_unix_nano).toBe(
      "1777777777555555555",
    );
    expect(typeof payload.spans[0]?.start_time_unix_nano).toBe("string");
  });

  it("retries a retryable response and then succeeds", async () => {
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response(503))
      .mockResolvedValueOnce(response(202));
    const exporter = new AgentOpsSpanExporter({
      fetchImpl,
      maxRetries: 2,
      retryBackoffMs: 0,
    });

    expect(await exportOnce(exporter)).toBe(ExportResultCode.SUCCESS);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it("fails immediately for a non-retryable HTTP response", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response(400));
    const logger = { warn: vi.fn() };
    const exporter = new AgentOpsSpanExporter({
      fetchImpl,
      logger,
      maxRetries: 2,
      retryBackoffMs: 0,
    });

    expect(await exportOnce(exporter)).toBe(ExportResultCode.FAILED);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(logger.warn).toHaveBeenCalledWith(expect.stringContaining("HTTP 400"));
  });

  it("bounds transport retries and logs the final failure", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error("server unavailable"));
    const logger = { warn: vi.fn() };
    const exporter = new AgentOpsSpanExporter({
      fetchImpl,
      logger,
      maxRetries: 2,
      retryBackoffMs: 0,
    });

    expect(await exportOnce(exporter)).toBe(ExportResultCode.FAILED);
    expect(fetchImpl).toHaveBeenCalledTimes(3);
    expect(logger.warn).toHaveBeenCalledWith(expect.stringContaining("3 attempt(s)"));
  });

  it("aborts timed-out attempts", async () => {
    vi.useFakeTimers();
    const fetchImpl = vi.fn((
      _input: Parameters<typeof fetch>[0],
      init?: Parameters<typeof fetch>[1],
    ) => new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => reject(new Error("aborted")));
    })) as unknown as typeof fetch;
    const exporter = new AgentOpsSpanExporter({
      fetchImpl,
      timeoutMs: 25,
      maxRetries: 0,
      retryBackoffMs: 0,
      logger: { warn: vi.fn() },
    });

    const result = exportOnce(exporter);
    await vi.advanceTimersByTimeAsync(25);
    expect(await result).toBe(ExportResultCode.FAILED);
    vi.useRealTimers();
  });

  it("waits for an in-flight export during shutdown", async () => {
    let resolveFetch: ((value: Response) => void) | undefined;
    const fetchImpl = vi.fn(() => new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    })) as unknown as typeof fetch;
    const exporter = new AgentOpsSpanExporter({ fetchImpl });
    const callback = vi.fn();
    exporter.export([span()], callback);

    let shutdownFinished = false;
    const shutdown = exporter.shutdown().then(() => { shutdownFinished = true; });
    await Promise.resolve();
    expect(shutdownFinished).toBe(false);
    resolveFetch?.(response(202));
    await shutdown;

    expect(callback).toHaveBeenCalledWith({ code: ExportResultCode.SUCCESS });
    expect(shutdownFinished).toBe(true);
  });

  it("rejects exports after shutdown and validates retry settings", async () => {
    const logger = { warn: vi.fn() };
    const exporter = new AgentOpsSpanExporter({ logger });
    await exporter.shutdown();
    expect(await exportOnce(exporter)).toBe(ExportResultCode.FAILED);
    expect(logger.warn).toHaveBeenCalled();

    expect(() => new AgentOpsSpanExporter({ timeoutMs: 0 })).toThrow();
    expect(() => new AgentOpsSpanExporter({ maxRetries: -1 })).toThrow();
    expect(() => new AgentOpsSpanExporter({ retryBackoffMs: -1 })).toThrow();
  });
});
