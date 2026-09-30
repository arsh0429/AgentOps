import type { Run } from "../api/types";
import { Link } from "react-router-dom";

export default function RunRow({ run }: { run: Run }) {
  return (
    <Link to={`/runs/${run.id}`}
      style={{ display: "block", padding: 10, border: "1px solid #eee",
               fontFamily: "ui-monospace, monospace", fontSize: 12,
               textDecoration: "none", color: "inherit", marginBottom: 6 }}>
      {run.id} &nbsp;·&nbsp; {run.agent_name} &nbsp;·&nbsp; {run.status}
      &nbsp;·&nbsp; {run.total_tokens} tok &nbsp;·&nbsp; ${run.total_cost.toFixed(4)}
    </Link>
  );
}
