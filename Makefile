.PHONY: install dev test lint typecheck clean server web agent digest

install:
	uv sync
	pnpm install

dev:
	@echo "Run \`make server\` and \`make web\` in separate terminals."

server:
	uv run uvicorn agentops_server.main:app --reload --port $${AGENTOPS_API_PORT:-8000}

web:
	pnpm --filter agentops-console dev

agent:
	uv run python -m agentops_research_agent

digest:
	AGENTOPS_API_PORT=$${AGENTOPS_API_PORT:-8000} pnpm --filter agentops-research-web dev

test:
	uv run pytest
	pnpm -r test

lint:
	uv run ruff check .
	pnpm -r lint

typecheck:
	uv run mypy packages/agentops-py/src packages/agentops-server/src apps/agentops-research-agent/src
	pnpm -r typecheck

clean:
	rm -rf .venv node_modules packages/*/node_modules packages/*/dist packages/*/.venv
