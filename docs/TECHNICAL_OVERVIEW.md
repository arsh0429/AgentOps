# AgentOps technical overview

## Workspace and build system

The repository combines a uv Python workspace and a pnpm TypeScript workspace. Python packages use `src/` layouts and hatchling builds. TypeScript packages use strict compiler settings; the SDK emits JavaScript and declarations, while both React applications build with Vite.

Python workspace members:

- `agentops`
- `agentops-server`
- `agentops-research-agent`
- `agentops-sdk-example`

pnpm workspace members:

- `@agentops/sdk`
- `agentops-console`
- `agentops-research-web`

## Python SDK

The `agentops` package contains shared Pydantic models for runs, spans, evaluation results, golden examples, and drift state. Its `otel` package provides semantic conventions, a configurable HTTP span exporter, tracer setup, and redaction policies.

`AgentOpsSpanExporter` serializes OpenTelemetry spans into the server payload, retries transient failures with backoff, accepts a custom HTTP client for testing, and exposes normal exporter shutdown/flush behavior. `install()` configures a tracer provider with a simple processor by default or a batch processor when requested.

The evaluation package supplies a registry, decorator, LLM judge helper, and four templates: relevance, faithfulness, structural completeness, and cost within budget. Drift implementations include ADWIN, maximum mean discrepancy, and population stability index.

## TypeScript SDK

`@agentops/sdk` exports `AgentOps` and `GenAI` conventions, `AgentOpsSpanExporter`, evaluation-definition helpers, and invariant execution. The exporter accepts either an endpoint string or `AgentOpsSpanExporterOptions`, validates retry and timeout settings, supports injected fetch and logging implementations, and reads `AGENTOPS_ENDPOINT` when no explicit endpoint is supplied.

## Server

`agentops_server.main:app` initializes the database, optionally starts the drift loop, and mounts nine API groups. The ingestion endpoint accepts serialized spans, normalizes JSON-encoded boundary attributes, maintains trace-to-run correlation, calculates usage/cost aggregates, and schedules evaluation only when a run reaches its terminal state.

The query layer exposes:

- run lists and trace details;
- run comparison;
- current drift state and signal series;
- per-run and recent evaluation results;
- golden datasets;
- asynchronous regression jobs;
- digest creation and retrieval;
- controlled access to bundled paper figures.

SQLite access is asynchronous through SQLModel and aiosqlite. Configuration is loaded through pydantic-settings with the `AGENTOPS_` prefix.

## Research workflow

The research agent accepts an interest and date range, creates a planner span, searches mock or real arXiv data, assigns papers to worker tasks, extracts metadata and figures, calls text or vision models when live model access is available, and emits a synthesized digest plus citation attribution. All planner, worker, tool, and model spans share an AgentOps run ID.

Mock arXiv is deterministic and backed by bundled JSON and figure assets. Setting `AGENTOPS_USE_REAL_ARXIV` switches search and metadata retrieval to the public arXiv API. Real-mode paper bodies currently contain abstracts only, and real-mode figure extraction returns no figures; bundled mock figures are never attributed to real papers.

## Web applications

The AgentOps console presents drift cards and series, recent runs, trace Gantt views, span attributes, run comparison, evaluation trends, and datasets. The research web application submits digest jobs, polls status, renders Markdown results and figures, and stores saved-search metadata under an `agentops-*` browser key.

Both applications are thin API clients. They keep server payloads unchanged and use React Query for request state.

## Evaluation and drift lifecycle

1. The server receives and persists a span.
2. Run identity is taken from `agentops.run_id` or resolved through trace correlation.
3. Root input/output and terminal status update the run record.
4. A terminal transition schedules registered online evaluations once.
5. Evaluation scores are persisted and become quality-drift inputs.
6. Drift workers create feature windows for inputs, tool distributions, quality, and attribution.
7. Detector output is stored for dashboards and time-series queries.

Regression jobs run the planner on each golden dataset row, compare candidate paper IDs and expected themes, and persist a summary. The optional `prompt_sha` is a metadata label; the job does not load a historical prompt by hash. Invariant evaluations run deterministically; judge evaluations use the configured Anthropic model when credentials are available.

## Privacy and security

The exporter applies the configured redactor before sending spans. The default `NoOpRedactor` preserves prompts and outputs so local evaluation and trace views work. For sensitive data, configure `AllowlistRedactor` or a custom `SpanRedactor` before exporting; the current default is suitable only for a trusted local environment.

The server validates figure paths against the configured figure root and validates input encodings used by drift processing. Authentication, authorization, tenant isolation, rate limiting, secret management, and a hardened deployment profile are not part of the current local runtime.

## Verification

The main verification commands are:

```bash
uv run pytest -m "not live"
uv run ruff check .
uv run mypy packages/agentops-py/src packages/agentops-server/src apps/agentops-research-agent/src
pnpm -r test
pnpm -r lint
pnpm -r typecheck
pnpm -r build
```

CI runs the same non-live Python and TypeScript checks on pushes and pull requests.
