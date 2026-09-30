# agentops-sdk-example

Minimal agent loop using the Anthropic SDK directly + manual OpenTelemetry/GenAI instrumentation. Sends spans to AgentOps via the same ingestion path as the Pydantic-AI reference agent — proof of framework-agnostic ingestion.

The `search_arxiv` tool in this example returns a fixed synthetic result set. It demonstrates tool-call tracing, not live paper search.

Run (with the AgentOps server up at port 8000):

```
AGENTOPS_ENDPOINT=http://localhost:8000/ingest \
  uv run python -m agentops_sdk_example.example
```
