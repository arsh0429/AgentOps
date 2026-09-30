from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class PaperSummary:
    id: str
    title: str
    authors: tuple[str, ...]
    abstract: str
    published: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class Paper(PaperSummary):
    body: str


@dataclass(frozen=True)
class Figure:
    paper_id: str
    caption: str
    content_type: str
    data: bytes
    filename: str | None = None


def _load_corpus() -> list[dict[str, Any]]:
    pkg = files("agentops_research_agent.mock_arxiv.data")
    raw = (pkg / "papers.json").read_text(encoding="utf-8")
    return cast(list[dict[str, Any]], json.loads(raw))


def _figures_dir() -> Path:
    return Path(str(files("agentops_research_agent.mock_arxiv.data") / "figures"))


class MockArxivCore:
    def __init__(self) -> None:
        self._corpus = _load_corpus()
        self._by_id = {p["id"]: p for p in self._corpus}

    def search(
        self,
        query: str,
        limit: int = 10,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[PaperSummary]:
        q = query.lower()
        results: list[PaperSummary] = []
        for p in self._corpus:
            if date_from and p["published"] < date_from:
                continue
            if date_to and p["published"] > date_to:
                continue
            blob = (p["title"] + " " + p["abstract"]).lower()
            if any(tok in blob for tok in q.split() if tok):
                results.append(
                    PaperSummary(
                        id=p["id"],
                        title=p["title"],
                        authors=tuple(p["authors"]),
                        abstract=p["abstract"],
                        published=p["published"],
                        categories=tuple(p["categories"]),
                    )
                )
        return results[:limit]

    def fetch_metadata(self, paper_id: str) -> PaperSummary:
        p = self._by_id.get(paper_id)
        if p is None:
            raise ValueError(
                f"paper_id {paper_id!r} is not in the mock corpus. "
                f"Use search_arxiv first to find a real paper id; do not invent one."
            )
        return PaperSummary(
            id=p["id"],
            title=p["title"],
            authors=tuple(p["authors"]),
            abstract=p["abstract"],
            published=p["published"],
            categories=tuple(p["categories"]),
        )

    def fetch_paper(self, paper_id: str) -> Paper:
        p = self._by_id.get(paper_id)
        if p is None:
            raise ValueError(
                f"paper_id {paper_id!r} is not in the mock corpus. "
                f"Use search_arxiv first to find a real paper id; do not invent one."
            )
        return Paper(
            id=p["id"],
            title=p["title"],
            authors=tuple(p["authors"]),
            abstract=p["abstract"],
            published=p["published"],
            categories=tuple(p["categories"]),
            body=p["body"],
        )

    def extract_figures(self, paper_id: str) -> list[Figure]:
        p = self._by_id.get(paper_id)
        if p is None:
            raise ValueError(
                f"paper_id {paper_id!r} is not in the mock corpus."
            )
        out: list[Figure] = []
        for f in p.get("figures", []):
            data = (_figures_dir() / f["filename"]).read_bytes()
            out.append(
                Figure(
                    paper_id=paper_id,
                    caption=f["caption"],
                    content_type="image/jpeg",
                    data=data,
                    filename=f["filename"],
                )
            )
        return out
