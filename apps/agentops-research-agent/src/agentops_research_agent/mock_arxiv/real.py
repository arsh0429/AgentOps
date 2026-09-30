from __future__ import annotations

import re
import time
from urllib.parse import urlencode

import feedparser  # type: ignore[import-untyped]
import httpx

from .mock import Figure, Paper, PaperSummary

ARXIV_API = "https://export.arxiv.org/api/query"

class RealArxivClient:
    """Real arXiv client. Polite by default: 3-second delay between requests,
    in-process call cache. PDF full text and figure extraction are not
    implemented; real-mode paper bodies contain abstracts and no figures.
    """
    def __init__(self, min_delay_s: float = 3.0, timeout_s: float = 15.0) -> None:
        self.min_delay = min_delay_s
        self._last_call = 0.0
        self._client = httpx.Client(
            timeout=timeout_s,
            headers={"User-Agent": "AgentOps/0.0 (portfolio project)"},
        )
        self._query_cache: dict[tuple[tuple[str, str], ...], str] = {}

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_call = time.monotonic()

    def _query(self, params_tuple: tuple[tuple[str, str], ...]) -> str:
        if params_tuple in self._query_cache:
            return self._query_cache[params_tuple]
        self._wait()
        url = ARXIV_API + "?" + urlencode(dict(params_tuple))
        r = self._client.get(url)
        r.raise_for_status()
        self._query_cache[params_tuple] = r.text
        return r.text

    def search(self, query: str, limit: int = 10,
               date_from: str | None = None, date_to: str | None = None) -> list[PaperSummary]:
        terms = [term for term in re.findall(r"[A-Za-z0-9_-]+", query)
                 if term.lower() not in {"a", "an", "and", "for", "in", "of", "the", "to"}]
        if not terms:
            raise ValueError("search query must contain at least one searchable term")
        search_query = " AND ".join(f"all:{term}" for term in terms[:3])
        if date_from or date_to:
            start = (date_from or "1900-01-01").replace("-", "") + "0000"
            end = (date_to or "9999-12-31").replace("-", "") + "2359"
            search_query += f" AND submittedDate:[{start} TO {end}]"
        params = (
            ("search_query", search_query),
            ("start", "0"),
            ("max_results", str(limit)),
            ("sortBy", "submittedDate"),
            ("sortOrder", "descending"),
        )
        raw = self._query(params)
        feed = feedparser.parse(raw)
        out: list[PaperSummary] = []
        for entry in feed.entries[:limit]:
            published = entry.get("published", "")[:10]
            if date_from and published < date_from:
                continue
            if date_to and published > date_to:
                continue
            out.append(PaperSummary(
                id=re.sub(r"v\d+$", "", entry.get("id", "").rsplit("/", 1)[-1]),
                title=entry.get("title", "").strip(),
                authors=tuple(a.get("name", "") for a in entry.get("authors", [])),
                abstract=entry.get("summary", "").strip(),
                published=published,
                categories=tuple(t.get("term", "") for t in entry.get("tags", [])),
            ))
        return out

    def fetch_metadata(self, paper_id: str) -> PaperSummary:
        raw = self._query((("id_list", paper_id),))
        feed = feedparser.parse(raw)
        if not feed.entries:
            raise ValueError(f"paper_id {paper_id!r} was not found in arXiv")
        e = feed.entries[0]
        return PaperSummary(
            id=paper_id,
            title=e.get("title", "").strip(),
            authors=tuple(a.get("name", "") for a in e.get("authors", [])),
            abstract=e.get("summary", "").strip(),
            published=e.get("published", "")[:10],
            categories=tuple(t.get("term", "") for t in e.get("tags", [])),
        )

    def fetch_paper(self, paper_id: str) -> Paper:
        # Full text via PDF parsing is out of scope; return abstract as body.
        meta = self.fetch_metadata(paper_id)
        return Paper(
            id=meta.id, title=meta.title, authors=meta.authors,
            abstract=meta.abstract, published=meta.published,
            categories=meta.categories,
            body=meta.abstract,
        )

    def extract_figures(self, paper_id: str) -> list[Figure]:
        # Never attribute bundled mock figures to a real paper.
        return []
