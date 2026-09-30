export interface GanttSpan {
  id: string;
  parentId: string | null;
  name: string;
  role: string | null;
  start: number;
  end: number;
  durationLabel: string;
}

interface Props {
  spans: GanttSpan[];
  onSpanClick?: (id: string) => void;
  highlightId?: string;
}

const ROLE_COLORS: Record<string, string> = {
  planner: "#4a90e2",
  worker: "#7bb86b",
  tool: "#c8b04a",
};

export default function GanttChart({ spans, onSpanClick, highlightId }: Props) {
  if (spans.length === 0) return <div style={{ opacity: 0.6 }}>No spans.</div>;
  const min = Math.min(...spans.map(s => s.start));
  const max = Math.max(...spans.map(s => s.end));
  const total = Math.max(1, max - min);

  return (
    <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 11 }}>
      {spans.map((s) => {
        const left = ((s.start - min) / total) * 100;
        const width = Math.max(0.5, ((s.end - s.start) / total) * 100);
        const color = ROLE_COLORS[s.role ?? ""] ?? "#888";
        const indent = s.parentId ? 16 : 0;
        return (
          <div key={s.id}
            style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <div style={{ width: 140, paddingLeft: indent, textAlign: "right" }}>
              {s.role ? `${s.role} · ${s.name}` : s.name}
            </div>
            <div style={{ flex: 1, height: 18, background: "#eee", position: "relative" }}>
              <div data-test="gantt-bar"
                onClick={() => onSpanClick?.(s.id)}
                style={{
                  position: "absolute",
                  left: `${left}%`,
                  width: `${width}%`,
                  height: "100%",
                  background: color,
                  outline: highlightId === s.id ? "2px solid #c0392b" : "none",
                  cursor: "pointer",
                }} />
            </div>
            <div style={{ width: 60, textAlign: "right", opacity: 0.7 }}>{s.durationLabel}</div>
          </div>
        );
      })}
    </div>
  );
}
