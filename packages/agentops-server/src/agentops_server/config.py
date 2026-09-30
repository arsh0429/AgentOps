from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to the repo root, resolved at import time.
_REPO_ROOT = Path(__file__).parents[4]
_DEFAULT_FIGURES_DIR = str(
    _REPO_ROOT / "apps/agentops-research-agent/src/agentops_research_agent/mock_arxiv/data/figures"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTOPS_", env_file=".env", extra="ignore")
    db_url: str = "sqlite+aiosqlite:///./agentops.db"
    online_eval_sample_rate: float = 1.0
    judge_model_default: str = "claude-haiku-4-5"
    cost_budget_default: float = 0.50
    figures_dir: str = _DEFAULT_FIGURES_DIR

settings = Settings()
