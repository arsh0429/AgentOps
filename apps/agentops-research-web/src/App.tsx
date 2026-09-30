import { Link, Route, Routes, useLocation } from "react-router-dom";
import DigestList from "./routes/DigestList";
import DigestView from "./routes/DigestView";

function Header() {
  const { pathname } = useLocation();
  const onDetail = pathname.startsWith("/digests/");
  return (
    <header className="site-header">
      <div className="page-shell" style={{ paddingTop: 0, paddingBottom: 0 }}>
        {onDetail ? (
          <Link to="/" className="back-link">← All digests</Link>
        ) : (
          <Link to="/" className="site-title">AgentOps Research</Link>
        )}
      </div>
    </header>
  );
}

export default function App() {
  return (
    <>
      <Header />
      <main className="page-shell">
        <Routes>
          <Route path="/" element={<DigestList />} />
          <Route path="/digests/:id" element={<DigestView />} />
        </Routes>
      </main>
    </>
  );
}
