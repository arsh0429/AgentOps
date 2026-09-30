import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import ScoreCard from "../components/ScoreCard";

export default function RunComparison() {
  const [params] = useSearchParams();
  const a = params.get("a") ?? "";
  const b = params.get("b") ?? "";
  const cmp = useQuery({
    queryKey: ["compare", a, b],
    queryFn: () => api.compareRuns(a, b),
    enabled: Boolean(a && b),
  });
  if (!a || !b) return <div>Provide ?a=&lt;run-id&gt;&amp;b=&lt;run-id&gt;.</div>;
  if (cmp.isLoading || !cmp.data) return <div>Loading…</div>;
  const { a: ra, b: rb, tool_distribution, scores } = cmp.data;
  const findScore = (n: string) => scores.find(s => s.eval_name === n);
  const rel = findScore("relevance_judge");
  const fa = findScore("faithfulness_judge");

  return (
    <div>
      <div style={{ fontSize: 13, marginBottom: 8 }}>
        <strong>{ra.id}</strong> &nbsp;vs&nbsp; <strong>{rb.id}</strong>
        &nbsp;<span style={{ opacity: 0.6 }}>(prompt {ra.prompt_sha ?? "—"} → {rb.prompt_sha ?? "—"})</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 18 }}>
        <ScoreCard label="Relevance" a={rel?.a} b={rel?.b} />
        <ScoreCard label="Faithfulness" a={fa?.a} b={fa?.b} />
        <ScoreCard label="Cost" a={ra.total_cost} b={rb.total_cost} format={(v) => `$${v.toFixed(4)}`} />
        <ScoreCard label="Tokens" a={ra.total_tokens} b={rb.total_tokens} format={(v) => `${Math.round(v)}`} />
      </div>

      <div style={{ fontSize: 11, opacity: 0.75, textTransform: "uppercase", marginTop: 12 }}>
        Tool-call distribution shift
      </div>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${tool_distribution.length || 1}, 1fr)`, gap: 6, marginTop: 6 }}>
        {tool_distribution.map((t) => {
          const delta = t.b_count - t.a_count;
          return (
            <div key={t.tool} style={{ padding: 8, border: "1px solid #eee", textAlign: "center" }}>
              <div style={{ fontSize: 10, opacity: 0.7 }}>{t.tool}</div>
              <div style={{ fontSize: 11, marginTop: 4 }}>
                {t.a_count} → {t.b_count} <span style={{ color: delta > 0 ? "#c0392b" : delta < 0 ? "#27ae60" : "inherit" }}>
                  {delta === 0 ? "·" : delta > 0 ? `+${delta}` : delta}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
