import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";

export default function Datasets() {
  const qc = useQueryClient();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: () => api.listDatasets() });
  const regressions = useQuery({ queryKey: ["regressions"], queryFn: () => api.listRegressions(), refetchInterval: 5000 });
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useQuery({ queryKey: ["dataset", selected], queryFn: () => api.getDataset(selected!), enabled: Boolean(selected) });
  const trigger = useMutation({
    mutationFn: (datasetId: string) => api.triggerRegression({ dataset_id: datasetId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["regressions"] }),
  });

  return (
    <div>
      <h2>Datasets</h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 16 }}>
        <div>
          {(datasets.data?.datasets ?? []).map((d) => (
            <button key={d.id} onClick={() => setSelected(d.id)}
              style={{ display: "block", padding: 8, marginBottom: 6, width: "100%",
                       textAlign: "left", border: selected === d.id ? "2px solid #4a90e2" : "1px solid #eee",
                       background: "white", cursor: "pointer" }}>
              <strong>{d.name}</strong>
              <div style={{ fontSize: 11, opacity: 0.7 }}>{d.description}</div>
            </button>
          ))}
          {(datasets.data?.datasets ?? []).length === 0 && (
            <div style={{ fontSize: 12, opacity: 0.6 }}>No datasets — run scripts/load_golden.py.</div>
          )}
        </div>
        <div>
          {detail.data && (
            <>
              <div style={{ marginBottom: 8 }}>
                <strong>{detail.data.dataset.name}</strong> — {detail.data.rows.length} rows
                <button onClick={() => trigger.mutate(detail.data!.dataset.id)}
                  style={{ marginLeft: 12, padding: "4px 8px", border: "1px solid #4a90e2",
                           background: "white", cursor: "pointer" }}>
                  Run regression
                </button>
              </div>
              <pre style={{ background: "#f7f7f7", padding: 8, fontSize: 11, maxHeight: 200, overflow: "auto" }}>
                {JSON.stringify(detail.data.rows.slice(0, 3), null, 2)}
              </pre>
            </>
          )}
          <h3 style={{ marginTop: 24 }}>Recent regression runs</h3>
          {(regressions.data?.regressions ?? []).map((r) => {
            const summ = r.summary as Record<string, number | undefined>;
            const meanRecall = typeof summ?.mean_recall === "number" ? summ.mean_recall.toFixed(3) : "—";
            const meanTheme = typeof summ?.mean_theme_coverage === "number" ? summ.mean_theme_coverage.toFixed(3) : "—";
            return (
              <div key={r.id} style={{ fontSize: 11, fontFamily: "ui-monospace, monospace",
                                        padding: 6, borderBottom: "1px solid #eee" }}>
                {r.id} · {r.dataset_id} · {r.status}
                &nbsp;·&nbsp; mean_recall={meanRecall}
                &nbsp;·&nbsp; mean_theme={meanTheme}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
