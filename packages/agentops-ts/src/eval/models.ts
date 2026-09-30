import { z } from "zod";

export const EvalMode = {
  Online: "online",
  Regression: "regression",
  Invariant: "invariant",
} as const;
export type EvalMode = typeof EvalMode[keyof typeof EvalMode];

export const RunSchema = z.object({
  id: z.string(),
  agentName: z.string(),
  startedAt: z.string(),
  input: z.record(z.unknown()).nullable().default(null),
  output: z.record(z.unknown()).nullable().default(null),
  totalCost: z.number().default(0),
  totalTokens: z.number().default(0),
});
export type Run = z.infer<typeof RunSchema>;

export const EvalResultSchema = z.object({
  runId: z.string(),
  evalName: z.string(),
  mode: z.enum([EvalMode.Online, EvalMode.Regression, EvalMode.Invariant]),
  score: z.number().min(0).max(1),
  label: z.string().optional(),
  rationale: z.string().optional(),
});
export type EvalResult = z.infer<typeof EvalResultSchema>;

export const GoldenSchema = z.object({
  id: z.string(),
  input: z.record(z.unknown()),
  expected: z.record(z.unknown()),
});
export type Golden = z.infer<typeof GoldenSchema>;
