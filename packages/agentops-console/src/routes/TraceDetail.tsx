import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import GanttChart, { type GanttSpan } from "../components/GanttChart";
import type { Span } from "../api/types";

// Matches the server-side _PRICING table in parser.py ($ per million tokens)
const PRICING: Array<[string, number, number]> = [
  ["claude-haiku-4-5",  0.80,  4.00],
  ["claude-haiku-4",    0.80,  4.00],
  ["claude-3-5-haiku",  0.80,  4.00],
  ["claude-sonnet-4-6", 3.00, 15.00],
  ["claude-sonnet-4",   3.00, 15.00],
  ["claude-3-5-sonnet", 3.00, 15.00],
  ["claude-opus-4-7",  15.00, 75.00],
  ["claude-opus-4",    15.00, 75.00],
  ["claude-3-opus",    15.00, 75.00],
];

function callCostUsd(model: string, inp: number, out: number): number {
  const m = model.toLowerCase();
  for (const [key, inRate, outRate] of PRICING) {
    if (m.includes(key)) return (inp * inRate + out * outRate) / 1_000_000;
  }
  return 0;
}

function trunc(s: unknown, n = 120): string {
  if (!s) return "—";
  const str = String(s);
  return str.length > n ? str.slice(0, n) + "…" : str;
}

interface LLMRow {
  spanId: string;
  name: string;
  model: string;
  inp: number;
  out: number;
  cost: number;
  prompt: string;
  completion: string;
}

function llmRows(spans: Span[]): LLMRow[] {
  return spans
    .filter(s => Number(s.attributes["gen_ai.usage.input_tokens"] ?? 0) > 0 ||
                 Number(s.attributes["gen_ai.usage.output_tokens"] ?? 0) > 0)
    .map(s => {
      const model = String(s.attributes["gen_ai.request.model"] ?? s.attributes["gen_ai.response.model"] ?? "");
      const inp = Number(s.attributes["gen_ai.usage.input_tokens"] ?? 0);
      const out = Number(s.attributes["gen_ai.usage.output_tokens"] ?? 0);
      return {
        spanId: s.id,
        name: s.name,
        model,
        inp,
        out,
        cost: callCostUsd(model, inp, out),
        prompt: trunc(s.attributes["gen_ai.prompt"]),
        completion: trunc(s.attributes["gen_ai.completion"]),
      };
    });
}

const TH: React.CSSProperties = { textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #ddd", fontWeight: 600, fontSize: 11, whiteSpace: "nowrap" };
const TD: React.CSSProperties = { padding: "4px 8px", fontSize: 11, verticalAlign: "top" };
const TD_MONO: React.CSSProperties = { ...TD, fontFamily: "monospace", whiteSpace: "pre-wrap", maxWidth: 280, wordBreak: "break-word" };

function LLMCallsTable({ spans, onSelect }: { spans: Span[]; onSelect: (id: string) => void }) {
  const rows = llmRows(spans);
  if (rows.length === 0) return null;
  const totalCost = rows.reduce((s, r) => s + r.cost, 0);
  const totalTok = rows.reduce((s, r) => s + r.inp + r.out, 0);
  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 6, opacity: 0.7, letterSpacing: 1 }}>LLM CALLS</div>
      <table style={{ borderCollapse: "collapse", width: "100%", tableLayout: "auto" }}>
        <thead>
          <tr style={{ background: "#f7f7f7" }}>
            <th style={TH}>Span</th>
            <th style={TH}>Model</th>
            <th style={{ ...TH, textAlign: "right" }}>In tok</th>
            <th style={{ ...TH, textAlign: "right" }}>Out tok</th>
            <th style={{ ...TH, textAlign: "right" }}>Cost</th>
            <th style={TH}>Prompt</th>
            <th style={TH}>Completion</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.spanId} onClick={() => onSelect(r.spanId)}
                style={{ cursor: "pointer", borderBottom: "1px solid #f0f0f0" }}
                onMouseEnter={e => (e.currentTarget.style.background = "#fafafa")}
                onMouseLeave={e => (e.currentTarget.style.background = "")}>
              <td style={{ ...TD, fontFamily: "monospace" }}>{r.name}</td>
              <td style={{ ...TD, fontFamily: "monospace", whiteSpace: "nowrap" }}>{r.model || "—"}</td>
              <td style={{ ...TD, textAlign: "right" }}>{r.inp.toLocaleString()}</td>
              <td style={{ ...TD, textAlign: "right" }}>{r.out.toLocaleString()}</td>
              <td style={{ ...TD, textAlign: "right", fontFamily: "monospace" }}>${r.cost.toFixed(4)}</td>
              <td style={TD_MONO}>{r.prompt}</td>
              <td style={TD_MONO}>{r.completion}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr style={{ background: "#f7f7f7", fontWeight: 600 }}>
            <td style={TD} colSpan={2}>Total</td>
            <td style={{ ...TD, textAlign: "right" }}>{totalTok.toLocaleString()}</td>
            <td style={TD} />
            <td style={{ ...TD, textAlign: "right", fontFamily: "monospace" }}>${totalCost.toFixed(4)}</td>
            <td style={TD} colSpan={2} />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function toGanttSpans(spans: Span[]): GanttSpan[] {
  if (spans.length === 0) return [];
  const t0 = Math.min(...spans.map(s => Date.parse(s.started_at)));
  return spans.map(s => {
    const start = Date.parse(s.started_at) - t0;
    const end = s.ended_at ? Date.parse(s.ended_at) - t0 : start;
    return {
      id: s.id, parentId: s.parent_span_id, name: s.name, role: s.role,
      start, end,
      durationLabel: `${((end - start) / 1000).toFixed(2)}s`,
    };
  });
}

export default function TraceDetail() {
  const { id = "" } = useParams();
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useQuery({ queryKey: ["run", id], queryFn: () => api.getRun(id), enabled: Boolean(id) });

  if (detail.isLoading) return <div>Loading…</div>;
  if (detail.isError || !detail.data) return <div>Run not found.</div>;

  const { run, spans } = detail.data;
  const gantt = toGanttSpans(spans);
  const sel = spans.find(s => s.id === selected);

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <strong>{run.id}</strong> · {run.agent_name} · {run.status} · {run.total_tokens} tok · ${run.total_cost.toFixed(4)}
      </div>
      <div style={{ background: "#f7f7f7", padding: 8, marginBottom: 12, fontSize: 11, opacity: 0.85 }}>
        TRACE TELEMETRY · spans contribute to input, tool-call, quality, and attribution signals
      </div>
      <GanttChart spans={gantt} onSpanClick={setSelected} highlightId={selected ?? undefined} />
      <LLMCallsTable spans={spans} onSelect={setSelected} />
      {sel && (
        <div style={{ marginTop: 16, padding: 12, border: "1px solid #ddd" }}>
          <div style={{ fontSize: 10, opacity: 0.7 }}>SELECTED · {sel.role ?? "—"} / {sel.name}</div>
          <pre style={{ background: "#f5f5f5", padding: 8, fontSize: 11, overflow: "auto" }}>
            {JSON.stringify(sel.attributes, null, 2)}
          </pre>
          {Boolean(sel.attributes["agentops.figure_data_url"]) && (
            <img src={String(sel.attributes["agentops.figure_data_url"])} alt="figure"
                 style={{ maxWidth: 600, marginTop: 8 }} />
          )}
        </div>
      )}
    </div>
  );
}
