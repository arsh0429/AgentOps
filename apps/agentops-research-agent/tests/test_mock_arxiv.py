import pytest
from agentops_research_agent.mock_arxiv.client import MockArxivClient


@pytest.fixture
def client() -> MockArxivClient:
    return MockArxivClient()


def test_search_returns_deterministic_results(client: MockArxivClient) -> None:
    a = client.search("concept drift", limit=5)
    b = client.search("concept drift", limit=5)
    assert [p.id for p in a] == [p.id for p in b]
    assert 1 <= len(a) <= 5


def test_search_filters_by_date_range(client: MockArxivClient) -> None:
    results = client.search("streaming", date_from="2024-01-01", date_to="2024-12-31")
    for p in results:
        assert "2024" in p.published


def test_fetch_metadata_returns_known_paper(client: MockArxivClient) -> None:
    meta = client.fetch_metadata("2401.00001")
    assert meta.id == "2401.00001"
    assert meta.title
    assert meta.abstract


def test_fetch_paper_returns_text_excerpt(client: MockArxivClient) -> None:
    paper = client.fetch_paper("2401.00001")
    assert paper.body
    assert len(paper.body) > 200


def test_extract_figures_returns_jpeg_bytes(client: MockArxivClient) -> None:
    figs = client.extract_figures("2401.00001")
    assert len(figs) >= 1
    assert figs[0].content_type == "image/jpeg"
    assert figs[0].data.startswith(b"\xff\xd8\xff")
