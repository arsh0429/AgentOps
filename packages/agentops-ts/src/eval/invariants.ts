import { evalsForMode, EvalMode, type Run, type EvalResult } from "./define";

export async function runInvariants(run: Run): Promise<EvalResult[]> {
  const specs = evalsForMode(EvalMode.Invariant);
  const results: EvalResult[] = [];
  for (const spec of specs) {
    try {
      results.push(await spec.fn(run, null));
    } catch (err) {
      results.push({
        runId: run.id, evalName: spec.name, mode: EvalMode.Invariant,
        score: 0, label: "error",
        rationale: err instanceof Error ? err.message : String(err),
      });
    }
  }
  return results;
}
