from __future__ import annotations

import os

from .mock import Figure, MockArxivCore, Paper, PaperSummary
from .real import RealArxivClient


class MockArxivClient:
    """Deterministic arXiv client used for local development and tests."""

    def __init__(self) -> None:
        self._core = MockArxivCore()

    def search(
        self,
        query: str,
        limit: int = 10,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[PaperSummary]:
        return self._core.search(query, limit, date_from, date_to)

    def fetch_metadata(self, paper_id: str) -> PaperSummary:
        return self._core.fetch_metadata(paper_id)

    def fetch_paper(self, paper_id: str) -> Paper:
        return self._core.fetch_paper(paper_id)

    def extract_figures(self, paper_id: str) -> list[Figure]:
        return self._core.extract_figures(paper_id)


_mock_client: MockArxivClient | None = None
_real_client: RealArxivClient | None = None


def get_arxiv_client() -> MockArxivClient | RealArxivClient:
    """Return the real client when enabled, otherwise the bundled mock client."""
    global _mock_client, _real_client
    if os.getenv("AGENTOPS_USE_REAL_ARXIV"):
        if _real_client is None:
            _real_client = RealArxivClient()
        return _real_client
    if _mock_client is None:
        _mock_client = MockArxivClient()
    return _mock_client
