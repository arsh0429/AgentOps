import pytest
from agentops_research_agent import tools


@pytest.mark.asyncio
async def test_search_arxiv_returns_summaries() -> None:
    results = await tools.search_arxiv(query="drift", limit=3)
    assert 1 <= len(results) <= 3
    assert results[0].id


@pytest.mark.asyncio
async def test_fetch_metadata() -> None:
    meta = await tools.fetch_metadata("2401.00001")
    assert meta.title


@pytest.mark.asyncio
async def test_fetch_paper_returns_body() -> None:
    paper = await tools.fetch_paper("2401.00001")
    assert len(paper.body) > 100


@pytest.mark.asyncio
@pytest.mark.live
async def test_extract_figures_returns_descriptions() -> None:
    descriptions = await tools.extract_figures("2401.00001")
    assert len(descriptions) >= 1
    assert descriptions[0].description


@pytest.mark.asyncio
async def test_score_candidate_returns_float_in_unit_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_score(prompt: str) -> str:
        return '{"score": 0.78, "rationale": "highly on-topic"}'
    monkeypatch.setattr("agentops_research_agent.tools._llm_json", fake_score)
    s = await tools.score_candidate(metadata_id="2401.00001",
                                    research_interest="concept drift in streaming ML")
    assert 0.0 <= s.score <= 1.0
    assert s.rationale
