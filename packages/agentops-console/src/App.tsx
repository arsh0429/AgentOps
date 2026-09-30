import { Link, NavLink, Route, Routes } from "react-router-dom";
import DriftHome from "./routes/DriftHome";
import TraceDetail from "./routes/TraceDetail";
import RunComparison from "./routes/RunComparison";
import DriftDetail from "./routes/DriftDetail";
import EvalResults from "./routes/EvalResults";
import Datasets from "./routes/Datasets";
import RunList from "./routes/RunList";

const navItem = "px-3 py-2 hover:underline";

export default function App() {
  return (
    <div>
      <header className="border-b">
        <nav className="flex gap-1 px-4 py-2 items-center">
          <Link to="/" className="font-bold mr-4">AgentOps</Link>
          <NavLink to="/" className={navItem} end>Monitoring</NavLink>
          <NavLink to="/runs" className={navItem}>Traces</NavLink>
          <NavLink to="/evals" className={navItem}>Evals</NavLink>
          <NavLink to="/datasets" className={navItem}>Datasets</NavLink>
        </nav>
      </header>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<DriftHome />} />
          <Route path="/runs" element={<RunList />} />
          <Route path="/runs/:id" element={<TraceDetail />} />
          <Route path="/compare" element={<RunComparison />} />
          <Route path="/drift/:signal" element={<DriftDetail />} />
          <Route path="/evals" element={<EvalResults />} />
          <Route path="/datasets" element={<Datasets />} />
        </Routes>
      </main>
    </div>
  );
}
