"""Tests for the citation-weight attribution helper used by the agent run
to emit the attribution span attribute consumed by the server-side
attribution drift worker.
"""
from agentops_research_agent.__main__ import _compute_citation_attribution
from agentops_research_agent.planner import PaperSection
from pytest import approx


def test_attribution_proportional_to_section_length() -> None:
    sections = [
        PaperSection(paper_id="paper-A", summary="x" * 100),
        PaperSection(paper_id="paper-B", summary="x" * 300),
    ]
    attr = _compute_citation_attribution(sections)
    assert set(attr) == {"paper-A", "paper-B"}
    assert attr["paper-A"] == approx(0.25)
    assert attr["paper-B"] == approx(0.75)
    assert sum(attr.values()) == approx(1.0)


def test_attribution_aggregates_duplicate_paper_ids() -> None:
    sections = [
        PaperSection(paper_id="paper-A", summary="x" * 50),
        PaperSection(paper_id="paper-A", summary="x" * 150),
        PaperSection(paper_id="paper-B", summary="x" * 200),
    ]
    attr = _compute_citation_attribution(sections)
    assert attr["paper-A"] == approx(0.5)
    assert attr["paper-B"] == approx(0.5)


def test_attribution_returns_empty_when_total_is_zero() -> None:
    assert _compute_citation_attribution([]) == {}
    assert _compute_citation_attribution(
        [PaperSection(paper_id="p", summary="")]
    ) == {}
