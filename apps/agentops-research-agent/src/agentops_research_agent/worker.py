from __future__ import annotations

from importlib.resources import files
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel

from . import tools

DEFAULT_MODEL = "claude-sonnet-4-6"


class WorkerInput(BaseModel):
    paper_id: str = Field(min_length=1)
    research_interest: str = Field(min_length=1)
    follow_up_question: str | None = None


class FigureDescription(BaseModel):
    caption: str
    description: str
    filename: str | None = None


class WorkerResult(BaseModel):
    paper_id: str
    summary: str
    figure_descriptions: list[FigureDescription]
    follow_up_answer: str | None = None


def _prompt() -> str:
    return (files("agentops_research_agent.prompts") / "worker.md").read_text(encoding="utf-8")


def build_worker_agent(model_name: str = DEFAULT_MODEL) -> Agent[WorkerInput, WorkerResult]:
    model = AnthropicModel(model_name)
    agent: Agent[WorkerInput, WorkerResult] = Agent(
        model=model,
        deps_type=WorkerInput,
        output_type=WorkerResult,
        system_prompt=_prompt(),
    )

    @agent.tool
    async def fetch_paper(ctx: RunContext[WorkerInput], paper_id: str) -> str:
        p = await tools.fetch_paper(paper_id)
        return p.body

    @agent.tool
    async def extract_figures(ctx: RunContext[WorkerInput], paper_id: str) -> list[dict[str, Any]]:
        descs = await tools.extract_figures(paper_id)
        return [
            {"caption": d.caption, "description": d.description, "filename": d.filename}
            for d in descs
        ]

    @agent.tool
    async def summarize(ctx: RunContext[WorkerInput], paper_id: str, focus: str) -> str:
        s = await tools.summarize(paper_id, focus)
        return s.text

    @agent.tool
    async def query_paper(ctx: RunContext[WorkerInput], paper_id: str, question: str) -> str:
        return await tools.query_paper(paper_id, question)

    return agent
