import type { DriftState, DriftSignal } from "../api/types";
import { Link } from "react-router-dom";

interface Props {
  signal: DriftSignal;
  state: DriftState | undefined;
}

const LABEL: Record<DriftSignal, string> = {
  input: "Lexical input drift",
  tool_call: "Tool-call drift",
  quality: "Quality drift",
  attribution: "Attribution drift",
};

export default function DriftSignalCard({ signal, state }: Props) {
  const drifted = state?.is_drifted ?? false;
  const value = state?.value;
  return (
    <Link to={`/drift/${signal}`}
      style={{
        display: "block", padding: 16, border: "1px solid #e5e7eb",
        borderLeft: `4px solid ${drifted ? "#c0392b" : "#27ae60"}`,
        borderRadius: 6, textDecoration: "none", color: "inherit",
      }}>
      <div style={{ fontSize: 11, opacity: 0.7, textTransform: "uppercase" }}>{LABEL[signal]}</div>
      <div style={{ fontSize: 22, marginTop: 6, color: drifted ? "#c0392b" : "inherit" }}>
        {state ? <strong>{state.detector_name} {value?.toFixed(3)}</strong> : <span>—</span>}
      </div>
      <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>
        {state ? (drifted ? "▲ drifted" : "stable") : "no data yet"}
      </div>
    </Link>
  );
}
