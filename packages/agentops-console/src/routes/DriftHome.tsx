import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import DriftSignalCard from "../components/DriftSignalCard";
import RunRow from "../components/RunRow";
import type { DriftSignal, DriftState } from "../api/types";

const SIGNALS: DriftSignal[] = ["input", "tool_call", "quality", "attribution"];

export default function DriftHome() {
  const drift = useQuery({ queryKey: ["drift"], queryFn: () => api.driftState(), refetchInterval: 5000 });
  const runs = useQuery({ queryKey: ["runs", { limit: 10 }], queryFn: () => api.listRuns({ limit: 10 }) });

  const stateBySignal = new Map<DriftSignal, DriftState>();
  for (const s of drift.data?.signals ?? []) stateBySignal.set(s.signal, s);

  return (
    <div>
      <div style={{ fontSize: 11, opacity: 0.7, textTransform: "uppercase", marginBottom: 8 }}>
        Drift signals · last 7 days
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
        {SIGNALS.map(s => <DriftSignalCard key={s} signal={s} state={stateBySignal.get(s)} />)}
      </div>
      <div style={{ fontSize: 11, opacity: 0.7, textTransform: "uppercase", marginBottom: 8 }}>
        Recent runs
      </div>
      {runs.isLoading && <div>Loading…</div>}
      {runs.data?.runs.map(r => <RunRow key={r.id} run={r} />)}
      {runs.data && runs.data.runs.length === 0 && <div style={{ opacity: 0.6 }}>No runs yet.</div>}
    </div>
  );
}
