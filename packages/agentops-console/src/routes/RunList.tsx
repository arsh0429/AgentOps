import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import RunRow from "../components/RunRow";

export default function RunList() {
  const [filter, setFilter] = useState("");
  const runs = useQuery({ queryKey: ["runs", { limit: 200 }], queryFn: () => api.listRuns({ limit: 200 }), refetchInterval: 10_000 });
  const filtered = (runs.data?.runs ?? []).filter((r) =>
    !filter ||
    r.id.includes(filter) ||
    r.agent_name.includes(filter) ||
    (r.input ? JSON.stringify(r.input).toLowerCase().includes(filter.toLowerCase()) : false));
  return (
    <div>
      <h2>Traces</h2>
      <input value={filter} onChange={(e) => setFilter(e.target.value)}
        placeholder="search runs (id, agent, input)…"
        style={{ width: "100%", padding: 8, border: "1px solid #ddd", marginBottom: 12 }} />
      {filtered.map((r) => <RunRow key={r.id} run={r} />)}
      {filtered.length === 0 && <div style={{ opacity: 0.6 }}>No runs match.</div>}
    </div>
  );
}
