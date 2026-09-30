"""Execution-scoped state shared by planner, workers, and deterministic tools."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field

FigurePayload = dict[str, str | None]


@dataclass
class AgentRunContext:
    """Mutable state owned by exactly one agent run.

    A fresh instance is bound at the CLI run boundary. Context variables are
    copied into child asyncio tasks, so planner and worker tasks from one run
    share this object while concurrently executing root runs retain different
    objects.
    """

    run_id: str
    figures: dict[str, list[FigurePayload]] = field(default_factory=dict)

    def record_figures(
        self,
        paper_id: str,
        figures: list[FigurePayload],
        *,
        overwrite: bool = True,
    ) -> None:
        if not overwrite and paper_id in self.figures:
            return
        self.figures[paper_id] = [dict(figure) for figure in figures]

    def figure_snapshot(self) -> dict[str, list[FigurePayload]]:
        return {
            paper_id: [dict(figure) for figure in figures]
            for paper_id, figures in self.figures.items()
        }


_current_run: ContextVar[AgentRunContext | None] = ContextVar(
    "agentops_research_agent_run_context",
    default=None,
)


def bind_run_context(run_id: str) -> Token[AgentRunContext | None]:
    """Bind a fresh context for one execution and return its reset token."""
    if not run_id:
        raise ValueError("run_id must not be empty")
    return _current_run.set(AgentRunContext(run_id=run_id))


def reset_run_context(token: Token[AgentRunContext | None]) -> None:
    _current_run.reset(token)


def current_run_context() -> AgentRunContext | None:
    return _current_run.get()


def record_run_figures(
    paper_id: str,
    figures: list[FigurePayload],
    *,
    overwrite: bool = True,
) -> None:
    """Record deterministic figures when called inside an agent execution.

    Tool functions remain usable independently in tests and notebooks. When
    no run is bound they still return their normal result, but there is no
    execution state in which to retain the side-channel copy.
    """
    context = current_run_context()
    if context is not None:
        context.record_figures(paper_id, figures, overwrite=overwrite)


def get_run_figures() -> dict[str, list[FigurePayload]]:
    context = current_run_context()
    return context.figure_snapshot() if context is not None else {}
