import type { RunDetail, RunsList, DriftState, DriftSignal, EvalResult, CompareResult, DatasetSummary, DatasetDetail, RegressionSummary } from "./types";

const BASE = "/api";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  listRuns: (params: { limit?: number; offset?: number } = {}): Promise<RunsList> => {
    const q = new URLSearchParams();
    if (params.limit !== undefined) q.set("limit", String(params.limit));
    if (params.offset !== undefined) q.set("offset", String(params.offset));
    const qs = q.toString();
    return getJson<RunsList>(`/runs${qs ? `?${qs}` : ""}`);
  },
  getRun: (id: string): Promise<RunDetail> => getJson<RunDetail>(`/runs/${id}`),
  driftState: (): Promise<{ signals: DriftState[] }> =>
    getJson<{ signals: DriftState[] }>(`/drift`),
  driftSeries: (signal: DriftSignal): Promise<{ points: DriftState[] }> =>
    getJson<{ points: DriftState[] }>(`/drift/series/${signal}`),
  evalsRecent: (params: { evalName?: string; limit?: number } = {}): Promise<{ results: EvalResult[] }> => {
    const q = new URLSearchParams();
    if (params.evalName) q.set("eval_name", params.evalName);
    if (params.limit !== undefined) q.set("limit", String(params.limit));
    const qs = q.toString();
    return getJson<{ results: EvalResult[] }>(`/evals/recent${qs ? `?${qs}` : ""}`);
  },
  compareRuns: (a: string, b: string): Promise<CompareResult> =>
    getJson<CompareResult>(`/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`),
  listDatasets: (): Promise<{ datasets: DatasetSummary[] }> => getJson<{ datasets: DatasetSummary[] }>(`/datasets`),
  getDataset: (id: string): Promise<DatasetDetail> => getJson<DatasetDetail>(`/datasets/${id}`),
  listRegressions: (): Promise<{ regressions: RegressionSummary[] }> => getJson<{ regressions: RegressionSummary[] }>(`/regressions`),
  triggerRegression: async (req: { dataset_id: string; prompt_sha?: string; model?: string }) => {
    const res = await fetch(`${BASE}/regressions`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  },
};
