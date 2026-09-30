interface Props {
  label: string;
  a: number | null | undefined;
  b: number | null | undefined;
  format?: (v: number) => string;
}

export default function ScoreCard({ label, a, b, format = (v) => v.toFixed(3) }: Props) {
  const have = a !== undefined && a !== null && b !== undefined && b !== null;
  const delta = have ? (b! - a!) : null;
  const pct = have && a !== 0 ? ((b! - a!) / Math.abs(a!)) * 100 : null;
  const color = delta === null ? "inherit" : delta > 0 ? "#27ae60" : delta < 0 ? "#c0392b" : "inherit";
  return (
    <div style={{ padding: 12, border: "1px solid #eee", textAlign: "left" }}>
      <div style={{ fontSize: 10, opacity: 0.75, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 16, marginTop: 4 }}>
        <strong>{a !== null && a !== undefined ? format(a!) : "—"} → {b !== null && b !== undefined ? format(b!) : "—"}</strong>
      </div>
      <div style={{ color, fontSize: 12 }}>
        {delta === null ? "—"
          : `${delta > 0 ? "▲" : delta < 0 ? "▼" : "·"} ${format(Math.abs(delta))}${pct !== null ? ` (${pct.toFixed(0)}%)` : ""}`}
      </div>
    </div>
  );
}
