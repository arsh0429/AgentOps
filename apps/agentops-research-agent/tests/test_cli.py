from agentops_research_agent.__main__ import _parse_args
from agentops_research_agent.worker import DEFAULT_MODEL


def test_cli_accepts_model_option() -> None:
    args = _parse_args([
        "streaming ML",
        "2024-01-01",
        "2024-12-31",
        "--model",
        "claude-haiku-4-5",
    ])

    assert args.model == "claude-haiku-4-5"


def test_cli_has_model_default() -> None:
    assert _parse_args([]).model == DEFAULT_MODEL
