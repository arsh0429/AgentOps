import { type Run, type Golden, type EvalResult, EvalMode } from "./models";

export { type Run, type Golden, type EvalResult, EvalMode };

export type EvalFn = (run: Run, golden: Golden | null) => Promise<EvalResult>;

export interface EvalSpec {
  name: string;
  mode: EvalMode;
  judgeModel?: string;
  fn: EvalFn;
}

const _registry = new Map<string, EvalSpec>();

export function defineEval(spec: EvalSpec): void {
  if (_registry.has(spec.name)) {
    throw new Error(`eval '${spec.name}' is already registered`);
  }
  _registry.set(spec.name, spec);
}

export function getEval(name: string): EvalSpec {
  const spec = _registry.get(name);
  if (!spec) throw new Error(`eval '${name}' not registered`);
  return spec;
}

export function listEvals(): string[] {
  return [..._registry.keys()].sort();
}

export function evalsForMode(mode: EvalMode): EvalSpec[] {
  return [..._registry.values()].filter((s) => s.mode === mode);
}

/** @internal */
export function _resetForTests(): void { _registry.clear(); }
