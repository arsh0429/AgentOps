import { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { formatDistanceToNow, parseISO } from "date-fns";
import { listDigests, createDigest, getDigest } from "../api/client";
import type { DigestSummary, SavedSearch } from "../api/types";

const STORAGE_KEY = "agentops-digest:saved-searches";
const MAX_SAVED = 20;
const MAX_CHIPS = 5;

// The mock arXiv corpus this dev build runs against contains papers published
// during 2024 only. Default the form to that range so submitting from-the-box
// has content to find. The real arXiv API (behind AGENTOPS_USE_REAL_ARXIV)
// would obviously cover more.
const DEFAULT_DATE_FROM = "2024-01-01";
const DEFAULT_DATE_TO = "2024-12-31";

function relativeTime(iso: string | null): string {
  if (!iso) return "";
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true });
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

// ---------- Saved searches helpers ----------

function loadSaved(): SavedSearch[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SavedSearch[]) : [];
  } catch {
    return [];
  }
}

function saveSavedSearches(searches: SavedSearch[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(searches));
}

function addSaved(searches: SavedSearch[], entry: SavedSearch): SavedSearch[] {
  // Deduplicate by exact research_interest; keep most recent.
  const filtered = searches.filter(
    (s) => s.research_interest !== entry.research_interest
  );
  const updated = [entry, ...filtered].slice(0, MAX_SAVED);
  return updated;
}

function removeSaved(searches: SavedSearch[], interest: string): SavedSearch[] {
  return searches.filter((s) => s.research_interest !== interest);
}

// ---------- Sub-components ----------

function DigestCard({ d }: { d: DigestSummary }) {
  return (
    <Link to={`/digests/${d.run_id}`} className="digest-card">
      <p className="digest-card-interest">{d.research_interest ?? "Digest"}</p>
      {d.data_source === "synthetic-mock" && (
        <p className="digest-card-meta">Synthetic demo data</p>
      )}
      {d.data_source === "arxiv-abstracts" && (
        <p className="digest-card-meta">arXiv abstracts</p>
      )}
      {dateWindow(d.date_from, d.date_to) && (
        <p className="digest-card-date">{dateWindow(d.date_from, d.date_to)}</p>
      )}
      {d.top_paper_title && (
        <p className="digest-card-top-paper">{d.top_paper_title}</p>
      )}
      {d.generated_at && (
        <p className="digest-card-meta">Generated {relativeTime(d.generated_at)}</p>
      )}
    </Link>
  );
}

function SavedSearchChips({
  searches,
  onSelect,
  onRemove,
}: {
  searches: SavedSearch[];
  onSelect: (s: SavedSearch) => void;
  onRemove: (interest: string) => void;
}) {
  const visible = searches.slice(0, MAX_CHIPS);
  if (visible.length === 0) return null;
  return (
    <div className="saved-searches">
      <span className="saved-searches-label">Saved searches:</span>
      <div className="saved-searches-chips">
        {visible.map((s) => (
          <span key={s.research_interest} className="saved-search-chip">
            <button
              type="button"
              className="saved-search-btn"
              onClick={() => onSelect(s)}
              title={s.research_interest}
            >
              {s.research_interest.length > 32
                ? s.research_interest.slice(0, 30) + "…"
                : s.research_interest}
            </button>
            <button
              type="button"
              className="saved-search-remove"
              onClick={() => onRemove(s.research_interest)}
              aria-label={`Remove saved search: ${s.research_interest}`}
            >
              ×
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}

// ---------- Running indicator with polling ----------

function RunningIndicator({
  runId,
  onReady,
  onDismiss,
}: {
  runId: string;
  onReady: (id: string) => void;
  onDismiss: () => void;
}) {
  const { data } = useQuery({
    queryKey: ["digest-poll", runId],
    queryFn: () => getDigest(runId),
    refetchInterval: (query) => {
      const d = query.state.data;
      if (!d) return 3000;
      // Stop on any terminal state. A run with status=succeeded but an empty
      // digest is a silent failure (the agent crashed before writing output)
      // — treat it as terminal too, otherwise the spinner spins forever.
      if (d.digest) return false;
      if (d.status === "failed") return false;
      if (d.status === "succeeded") return false;
      return 3000;
    },
  });

  useEffect(() => {
    if (data?.digest) onReady(runId);
  }, [data, runId, onReady]);

  // Three terminal states surfaced to the user:
  //   1. ready  — digest non-empty, will be navigated to.
  //   2. error  — explicit error from the agent (output.error is set).
  //   3. silent — status=succeeded but digest empty (agent crashed early).
  const error = data?.error;
  const silentFail = data?.status === "succeeded" && !data?.digest;
  const explicitFail = data?.status === "failed";
  const isFailed = explicitFail || silentFail;

  return (
    <div className="running-indicator">
      {isFailed ? (
        <>
          <p className="running-indicator-failed">
            Run <code>{runId}</code> failed.
            {error ? <> {error}</> : silentFail
              ? <> The agent finished without producing a digest. Common cause: the date range has no papers (the mock corpus only covers 2024).</>
              : <> Check server logs.</>}
          </p>
          <button
            type="button"
            className="running-indicator-dismiss"
            onClick={onDismiss}
          >
            Dismiss
          </button>
        </>
      ) : (
        <>
          <p className="running-indicator-msg">
            <span className="running-spinner" aria-hidden="true">⟳</span>{" "}
            Generating digest… <code>{runId}</code>
          </p>
          <button
            type="button"
            className="running-indicator-dismiss"
            onClick={onDismiss}
          >
            Hide status
          </button>
        </>
      )}
    </div>
  );
}

// ---------- Search form ----------

function SearchForm({
  onSubmit,
}: {
  onSubmit: (interest: string, dateFrom: string, dateTo: string) => void;
}) {
  const [interest, setInterest] = useState("");
  const [dateFrom, setDateFrom] = useState(DEFAULT_DATE_FROM);
  const [dateTo, setDateTo] = useState(DEFAULT_DATE_TO);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>(loadSaved);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: () =>
      createDigest({
        research_interest: interest.trim(),
        date_from: dateFrom,
        date_to: dateTo,
      }),
    onSuccess: (data) => {
      // Save the search
      const entry: SavedSearch = {
        research_interest: interest.trim(),
        date_from: dateFrom,
        date_to: dateTo,
        savedAt: new Date().toISOString(),
      };
      const updated = addSaved(savedSearches, entry);
      setSavedSearches(updated);
      saveSavedSearches(updated);
      setRunningId(data.run_id);
      setSubmitError(null);
    },
    onError: (err) => {
      setSubmitError(String(err));
    },
  });

  const handleReady = useCallback(
    (id: string) => {
      navigate(`/digests/${id}`);
    },
    [navigate]
  );

  const handleSelectSaved = useCallback((s: SavedSearch) => {
    setInterest(s.research_interest);
    setDateFrom(s.date_from);
    setDateTo(s.date_to);
  }, []);

  const handleRemoveSaved = useCallback(
    (interestToRemove: string) => {
      const updated = removeSaved(savedSearches, interestToRemove);
      setSavedSearches(updated);
      saveSavedSearches(updated);
    },
    [savedSearches]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!interest.trim()) return;
    onSubmit(interest.trim(), dateFrom, dateTo);
    mutation.mutate();
  };

  return (
    <div className="search-form-container">
      <SavedSearchChips
        searches={savedSearches}
        onSelect={handleSelectSaved}
        onRemove={handleRemoveSaved}
      />
      <form className="search-form" onSubmit={handleSubmit}>
        <label className="search-label" htmlFor="research-interest">
          Research interest
        </label>
        <input
          id="research-interest"
          type="text"
          className="search-input"
          value={interest}
          onChange={(e) => setInterest(e.target.value)}
          placeholder="e.g. concept drift in streaming ML"
          required
        />
        <div className="search-date-row">
          <div className="search-date-field">
            <label className="search-label" htmlFor="date-from">
              From
            </label>
            <input
              id="date-from"
              type="date"
              className="search-input search-input-date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>
          <div className="search-date-field">
            <label className="search-label" htmlFor="date-to">
              To
            </label>
            <input
              id="date-to"
              type="date"
              className="search-input search-input-date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
        </div>
        <button
          type="submit"
          className="search-submit"
          disabled={mutation.isPending || !!runningId}
        >
          {mutation.isPending ? "Submitting…" : "Generate digest"}
        </button>
        {submitError && (
          <p className="error-msg search-error">{submitError}</p>
        )}
      </form>
      {runningId && (
        <RunningIndicator
          runId={runningId}
          onReady={handleReady}
          onDismiss={() => setRunningId(null)}
        />
      )}
      <p className="search-hint">
        Searches use the bundled 2024 mock corpus by default. Set
        AGENTOPS_USE_REAL_ARXIV=1 on the server to use the arXiv API.
      </p>
    </div>
  );
}

// ---------- Page ----------

export default function DigestList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["digests"],
    queryFn: () => listDigests(),
  });

  const digests = data?.digests ?? [];

  return (
    <div>
      <SearchForm onSubmit={() => {}} />

      {isLoading && <p className="status-msg">Loading digests…</p>}
      {error && (
        <p className="error-msg">Failed to load digests: {String(error)}</p>
      )}

      {!isLoading && !error && digests.length === 0 && (
        <p className="status-msg">No digests yet.</p>
      )}

      {digests.length > 0 && (
        <ul className="digest-list">
          {digests.map((d) => (
            <li key={d.run_id}>
              <DigestCard d={d} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
