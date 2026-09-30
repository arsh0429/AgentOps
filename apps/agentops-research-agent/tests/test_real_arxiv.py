import pytest


def test_real_mode_never_uses_mock_paper_content(monkeypatch) -> None:
    from agentops_research_agent.mock_arxiv.real import RealArxivClient

    client = RealArxivClient(min_delay_s=0)
    monkeypatch.setattr(client, "_query", lambda _: "<feed></feed>")
    with pytest.raises(ValueError, match="not found in arXiv"):
        client.fetch_metadata("2401.00001")
    assert client.extract_figures("2401.00001") == []


def test_real_search_sends_date_window_to_arxiv(monkeypatch) -> None:
    from agentops_research_agent.mock_arxiv.real import RealArxivClient

    client = RealArxivClient(min_delay_s=0)
    seen = []

    def query(params):
        seen.append(dict(params))
        return "<feed></feed>"

    monkeypatch.setattr(client, "_query", query)
    assert client.search("concept drift", date_from="2024-01-01", date_to="2024-12-31") == []
    assert "all:concept AND all:drift" in seen[0]["search_query"]
    assert "submittedDate:[202401010000 TO 202412312359]" in seen[0]["search_query"]


@pytest.mark.live
def test_real_arxiv_search_returns_at_least_one_result() -> None:
    from agentops_research_agent.mock_arxiv.real import RealArxivClient
    c = RealArxivClient()
    results = c.search("concept drift", limit=2)
    assert results
    assert results[0].title

def test_get_arxiv_client_returns_real_when_flag_set(monkeypatch) -> None:
    monkeypatch.setenv("AGENTOPS_USE_REAL_ARXIV", "1")
    # Reload `client` so the env-var gate is rechecked.
    import importlib

    import agentops_research_agent.mock_arxiv.client as cli
    importlib.reload(cli)
    from agentops_research_agent.mock_arxiv.real import RealArxivClient
    assert isinstance(cli.get_arxiv_client(), RealArxivClient)
    assert cli.get_arxiv_client() is cli.get_arxiv_client()

def test_get_arxiv_client_returns_mock_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AGENTOPS_USE_REAL_ARXIV", raising=False)
    import importlib

    import agentops_research_agent.mock_arxiv.client as cli
    importlib.reload(cli)
    from agentops_research_agent.mock_arxiv.client import MockArxivClient
    assert isinstance(cli.get_arxiv_client(), MockArxivClient)
