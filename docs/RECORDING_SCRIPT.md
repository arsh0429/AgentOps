# AgentOps walkthrough

The walkthrough presents the running system using deterministic mock data.

## Capture sequence

1. Open the AgentOps drift dashboard and show the current input, tool-call, quality, and attribution signals.
2. Open a recent run and inspect planner, worker, tool, and model spans in the trace timeline.
3. Compare two runs and highlight cost, token, evaluation, and tool-distribution differences.
4. Open evaluation trends and a drift signal series.
5. Open the research application, submit or select a digest, and review its citations and figures.
6. Close on the architecture summary and framework-neutral SDK contract.

## Regeneration

With the API on port 8000, the console on 5173, and the research UI on 5174:

```bash
uv run python scripts/run_demo.py
uv run python scripts/record_walkthrough.py
uv run python scripts/add_captions.py
uv run python scripts/make_gif.py
```

Captions are embedded during browser capture. The resulting `docs/walkthrough.mp4` and `docs/walkthrough.gif` are repository-local presentation assets.
