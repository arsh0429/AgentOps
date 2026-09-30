# AgentOps screenshots

These screenshots are generated from the local mock dataset and show the current AgentOps console and research application.

| File | View |
|---|---|
| `01-drift-home.png` | Drift status and recent runs |
| `02-trace-gantt.png` | Trace timeline and span inspection |
| `03-run-comparison.png` | Side-by-side run comparison |
| `04-drift-detail.png` | Drift signal time series |
| `05-eval-results.png` | Evaluation score trends |
| `07-digest-list.png` | Research digest history and saved searches |
| `08-digest-view.png` | Rendered research digest and figures |

To refresh the assets, start the API and both frontends, seed the mock data, and run the capture scripts:

```bash
make server
make web
make digest
uv run python scripts/load_golden.py
uv run python scripts/seed_drift.py
uv run python scripts/capture_console_screens.py
uv run python scripts/record_walkthrough.py
uv run python scripts/capture_digest_screens.py
```

Screenshots are captured at a consistent desktop viewport and checked for current navigation labels, readable charts, and complete page content.
