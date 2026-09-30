import { describe, it, expect, vi, beforeEach } from "vitest";
import { listDigests, getDigest } from "./client";
import type { DigestSummary, DigestDetail } from "./types";

const mockDigestSummary: DigestSummary = {
  run_id: "live-abc123",
  research_interest: "concept drift detection",
  date_from: "2024-01-01",
  date_to: "2024-12-31",
  generated_at: "2026-05-06T10:05:00",
  top_paper_title: "ADWIN-2: Adaptive Windowing",
  model: "claude-sonnet-4-6",
};

const mockDigestDetail: DigestDetail = {
  run_id: "live-abc123",
  research_interest: "concept drift detection",
  date_from: "2024-01-01",
  date_to: "2024-12-31",
  generated_at: "2026-05-06T10:05:00",
  digest: "## Weekly Digest\n- Some finding",
  candidates: [
    { paper_id: "2401.00001", title: "ADWIN-2: Adaptive Windowing", score: 0.95, rationale: "Core topic" },
  ],
  sections: [
    { paper_id: "2401.00001", summary: "ADWIN-2 achieves O(log n) memory." },
  ],
  figures: {},
  model: "claude-sonnet-4-6",
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("listDigests", () => {
  it("parses /api/digests response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ digests: [mockDigestSummary] }),
    }));

    const result = await listDigests();
    expect(result.digests).toHaveLength(1);
    expect(result.digests[0]?.run_id).toBe("live-abc123");
    expect(result.digests[0]?.top_paper_title).toBe("ADWIN-2: Adaptive Windowing");
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    }));

    await expect(listDigests()).rejects.toThrow("500");
  });
});

describe("getDigest", () => {
  it("parses /api/digests/:id response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockDigestDetail,
    }));

    const result = await getDigest("live-abc123");
    expect(result.run_id).toBe("live-abc123");
    expect(result.digest).toContain("Weekly Digest");
    expect(result.candidates).toHaveLength(1);
    expect(result.sections).toHaveLength(1);
  });

  it("throws 404 for unknown id", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
    }));

    await expect(getDigest("no-such-run")).rejects.toThrow("404");
  });
});
