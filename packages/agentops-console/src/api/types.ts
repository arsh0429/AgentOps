export type RunStatus = "running" | "succeeded" | "failed";

export interface Run {
  id: string;
  agent_name: string;
  started_at: string;
  ended_at: string | null;
  status: RunStatus;
  prompt_sha: string | null;
  model: string | null;
  total_cost: number;
  total_tokens: number;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
}

export interface Span {
  id: string;
  trace_id: string;
  run_id: string;
  parent_span_id: string | null;
  name: string;
  role: string | null;
  started_at: string;
  ended_at: string | null;
  attributes: Record<string, unknown>;
  events: Array<Record<string, unknown>>;
}

export interface RunDetail { run: Run; spans: Span[] }
export interface RunsList { runs: Run[] }

export type DriftSignal = "input" | "tool_call" | "quality" | "attribution";

export interface DriftState {
  signal: DriftSignal;
  detector_name: string;
  window: string;
  value: number;
  threshold: number;
  is_drifted: boolean;
  updated_at: string;
}

export type EvalMode = "online" | "regression" | "invariant";

export interface EvalResult {
  run_id: string;
  eval_name: string;
  mode: EvalMode;
  score: number;
  label: string | null;
  rationale: string | null;
  created_at: string;
}

export interface CompareResult {
  a: Run;
  b: Run;
  tool_distribution: Array<{ tool: string; a_count: number; b_count: number }>;
  scores: Array<{ eval_name: string; a?: number; b?: number }>;
}

export interface DatasetSummary { id: string; name: string; description: string | null }
export interface DatasetRow { id: string; dataset_id: string; input: Record<string, unknown>; expected: Record<string, unknown> }
export interface DatasetDetail { dataset: DatasetSummary; rows: DatasetRow[] }
export interface RegressionSummary {
  id: string; dataset_id: string; prompt_sha: string | null; model: string | null;
  started_at: string; ended_at: string | null; status: string;
  summary: Record<string, unknown>;
}
