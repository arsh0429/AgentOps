import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { api } from "../api/client";

const NAMES = ["relevance_judge", "faithfulness_judge", "structural_completeness", "cost_within_budget"];

export default function EvalResults() {
  const q1 = useQuery({ queryKey: ["evals", NAMES[0]], queryFn: () => api.evalsRecent({ evalName: NAMES[0], limit: 50 }) });
  const q2 = useQuery({ queryKey: ["evals", NAMES[1]], queryFn: () => api.evalsRecent({ evalName: NAMES[1], limit: 50 }) });
  const q3 = useQuery({ queryKey: ["evals", NAMES[2]], queryFn: () => api.evalsRecent({ evalName: NAMES[2], limit: 50 }) });
  const q4 = useQuery({ queryKey: ["evals", NAMES[3]], queryFn: () => api.evalsRecent({ evalName: NAMES[3], limit: 50 }) });
  const queries = [q1, q2, q3, q4];

  return (
    <div>
      <h2>Eval results</h2>
      {NAMES.map((name, i) => {
        const data = queries[i]?.data?.results ?? [];
        const series = [...data].reverse().map((r, idx) => ({ idx, score: r.score }));
        const latest = data[0];
        return (
          <section key={name} style={{ marginBottom: 24, border: "1px solid #eee", padding: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div><strong>{name}</strong> · n={data.length}</div>
              <div>latest: {latest ? latest.score.toFixed(3) : "—"}</div>
            </div>
            <div style={{ height: 100, marginTop: 8 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series}>
                  <XAxis dataKey="idx" hide />
                  <YAxis domain={[0, 1]} width={32} />
                  <Tooltip />
                  <Line dataKey="score" dot={false} stroke="#4a90e2" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div style={{ marginTop: 8, fontFamily: "ui-monospace, monospace", fontSize: 11 }}>
              {data.slice(0, 5).map((r) => (
                <Link key={`${r.run_id}-${r.eval_name}-${r.created_at}`}
                  to={`/runs/${r.run_id}`}
                  style={{ display: "block", textDecoration: "none", color: "inherit" }}>
                  {r.created_at} · {r.run_id} · {r.score.toFixed(3)}{r.label ? ` · ${r.label}` : ""}
                </Link>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
