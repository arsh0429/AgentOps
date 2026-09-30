import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { format, parseISO } from "date-fns";
import { getDigest } from "../api/client";
import ScoreChip from "../components/ScoreChip";
import type { Candidate, DigestFigure, PaperSection } from "../api/types";

function absDate(iso: string | null): string {
  if (!iso) return "";
  try {
    return format(parseISO(iso), "d MMM yyyy, HH:mm");
  } catch {
    return iso;
  }
}

function dateWindow(from: string | null, to: string | null): string {
  if (from && to) return `${from} – ${to}`;
  if (from) return `from ${from}`;
  if (to) return `to ${to}`;
  return "";
}

function CandidatesSection({ candidates }: { candidates: Candidate[] }) {
  if (candidates.length === 0) return null;
  return (
    <section className="candidates-section">
      <h2>Candidates</h2>
      <table className="candidates-table">
        <thead>
          <tr>
            <th>Paper</th>
            <th>Title</th>
            <th>Score</th>
            <th>Rationale</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => (
            <tr key={c.paper_id}>
              <td className="paper-id-cell">{c.paper_id}</td>
              <td>{c.title}</td>
              <td><ScoreChip score={c.score} /></td>
              <td className="rationale-cell">{c.rationale}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function SectionsSection({ sections }: { sections: PaperSection[] }) {
  if (sections.length === 0) return null;
  return (
    <section className="papers-section">
      <h2>Per-paper summaries</h2>
      {sections.map((s) => (
        <div key={s.paper_id} className="paper-block">
          <p className="paper-block-id">{s.paper_id}</p>
          <p className="paper-block-summary">{s.summary}</p>
        </div>
      ))}
    </section>
  );
}

function FiguresSection({ figures }: { figures: Record<string, DigestFigure[]> }) {
  const entries = Object.entries(figures).filter(([, figs]) => figs.length > 0);
  if (entries.length === 0) return null;
  return (
    <section className="figures-section">
      <h2>Figures</h2>
      {entries.map(([paperId, figs]) => (
        <div key={paperId} className="figures-paper-group">
          <p className="figures-paper-id">{paperId}</p>
          <div className="figures-grid">
            {figs.map((fig, i) => (
              <div key={i} className="figure-item">
                {fig.filename && (
                  <img
                    src={`/api/papers/${encodeURIComponent(paperId)}/figures/${encodeURIComponent(fig.filename)}`}
                    alt={fig.caption}
                    className="figure-img"
                    loading="lazy"
                  />
                )}
                {fig.caption && (
                  <p className="figure-caption">{fig.caption}</p>
                )}
                {fig.description && (
                  <p className="figure-description">{fig.description}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

export default function DigestView() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useQuery({
    queryKey: ["digest", id],
    queryFn: () => getDigest(id!),
    enabled: id !== undefined,
  });

  if (isLoading) return <p className="status-msg">Loading digest…</p>;
  if (error) return <p className="error-msg">Failed to load digest: {String(error)}</p>;
  if (!data) return null;

  const dw = dateWindow(data.date_from, data.date_to);

  return (
    <article>
      <header className="digest-header">
        <h1 className="digest-header-interest">{data.research_interest ?? "Digest"}</h1>
        {data.data_source === "synthetic-mock" && (
          <p className="digest-header-date">Synthetic sample papers; IDs and findings are demo data.</p>
        )}
        {data.data_source === "arxiv-abstracts" && (
          <p className="digest-header-date">arXiv metadata and abstracts only; full papers were not read.</p>
        )}
        {dw && <p className="digest-header-date">{dw}</p>}
      </header>

      <div className="digest-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {data.digest}
        </ReactMarkdown>
      </div>

      {(data.candidates.length > 0 || data.sections.length > 0) && (
        <hr className="section-divider" />
      )}

      <CandidatesSection candidates={data.candidates} />

      {data.candidates.length > 0 && data.sections.length > 0 && (
        <hr className="section-divider" />
      )}

      <SectionsSection sections={data.sections} />

      {Object.keys(data.figures ?? {}).length > 0 && (
        <hr className="section-divider" />
      )}

      <FiguresSection figures={data.figures ?? {}} />

      <footer className="digest-footer">
        Run id: {data.run_id}
        {data.generated_at && <> · Generated {absDate(data.generated_at)}</>}
      </footer>
    </article>
  );
}
