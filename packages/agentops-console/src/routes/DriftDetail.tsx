import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, ReferenceLine } from "recharts";
import { api } from "../api/client";
import type { DriftSignal } from "../api/types";

const TITLES: Record<DriftSignal, string> = {
  input: "Lexical input drift (MMD on SHA-256 token features)",
  tool_call: "Tool-call distribution drift (PSI per role)",
  quality: "Quality drift (ADWIN on relevance_judge)",
  attribution: "Attribution drift (PSI on citation-weight distribution)",
};

export default function DriftDetail() {
  const { signal = "input" } = useParams();
  const sig = signal as DriftSignal;
  const series = useQuery({
    queryKey: ["drift-series", sig],
    queryFn: () => api.driftSeries(sig),
    refetchInterval: 5000,
  });

  const points = (series.data?.points ?? []).map((p, i) => ({
    idx: i, value: p.value, threshold: p.threshold, drifted: p.is_drifted ? 1 : 0,
  }));
  const last = points.length > 0 ? points[points.length - 1] : null;

  return (
    <div>
      <Link to="/" style={{ fontSize: 12 }}>← back to monitoring</Link>
      <h2>{TITLES[sig] ?? "Drift detail"}</h2>
      <div style={{ marginTop: 8, fontSize: 13 }}>
        Latest: {last
          ? <><strong>{last.value.toFixed(4)}</strong> (threshold {last.threshold.toFixed(4)}) — {last.drifted ? "▲ drifted" : "stable"}</>
          : "no data"}
      </div>
      <div style={{ height: 240, marginTop: 16 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points}>
            <XAxis dataKey="idx" hide />
            <YAxis />
            <Tooltip />
            <Line dataKey="value" dot={false} stroke="#4a90e2" />
            {last && <ReferenceLine y={last.threshold} stroke="#c0392b" strokeDasharray="3 3" />}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
