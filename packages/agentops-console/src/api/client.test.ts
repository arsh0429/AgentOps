import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "./client";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("api.listRuns", () => {
  it("hits /api/runs and returns parsed body", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ runs: [{ id: "r1" }] }), { status: 200 }),
    );
    const out = await api.listRuns({ limit: 10 });
    expect(fetchSpy).toHaveBeenCalledWith("/api/runs?limit=10");
    expect(out.runs[0]?.id).toBe("r1");
  });

  it("throws on non-2xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("nope", { status: 500, statusText: "Server Error" }),
    );
    await expect(api.listRuns()).rejects.toThrow(/500/);
  });
});
