import { describe, it, expect, vi, beforeEach } from "vitest";
import { defineEval, EvalMode, listEvals, getEval, _resetForTests, type Run } from "./eval/define";
import { runInvariants } from "./eval/invariants";

beforeEach(() => _resetForTests());

describe("defineEval", () => {
  it("registers an eval and lists it", () => {
    defineEval({
      name: "x_inv",
      mode: EvalMode.Invariant,
      fn: async (run: Run) => ({ runId: run.id, evalName: "x_inv", mode: EvalMode.Invariant, score: 1 }),
    });
    expect(listEvals()).toContain("x_inv");
    expect(getEval("x_inv").mode).toBe(EvalMode.Invariant);
  });

  it("throws on duplicate registration", () => {
    defineEval({ name: "dup", mode: EvalMode.Invariant, fn: async (r) => ({ runId: r.id, evalName: "dup", mode: EvalMode.Invariant, score: 0 }) });
    expect(() => defineEval({ name: "dup", mode: EvalMode.Invariant, fn: async (r) => ({ runId: r.id, evalName: "dup", mode: EvalMode.Invariant, score: 0 }) })).toThrow();
  });
});

describe("runInvariants", () => {
  it("dispatches all invariant evals against a run", async () => {
    const fn = vi.fn(async (run: Run) => ({ runId: run.id, evalName: "ok", mode: EvalMode.Invariant, score: 1 }));
    defineEval({ name: "ok", mode: EvalMode.Invariant, fn });
    const results = await runInvariants({
      id: "r1", agentName: "a", startedAt: new Date().toISOString(),
      input: null, output: null, totalCost: 0, totalTokens: 0,
    });
    expect(results).toHaveLength(1);
    expect(results[0]?.score).toBe(1);
    expect(fn).toHaveBeenCalled();
  });
});
