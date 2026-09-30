from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db.engine import init_db
from .orchestrator.drift_workers import drift_loop


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    task = None
    if os.getenv("AGENTOPS_DRIFT_LOOP", "1") != "0":
        task = asyncio.create_task(drift_loop())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

app = FastAPI(title="AgentOps", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Router imports are deferred below app construction to avoid circular imports.
from .api import compare as compare_api  # noqa: E402
from .api import datasets as datasets_api  # noqa: E402
from .api import digests as digests_api  # noqa: E402
from .api import drift as drift_api  # noqa: E402
from .api import evals as evals_api  # noqa: E402
from .api import figures as figures_api  # noqa: E402
from .api import ingest as ingest_api  # noqa: E402
from .api import regression as regression_api  # noqa: E402
from .api import runs as runs_api  # noqa: E402

app.include_router(ingest_api.router)
app.include_router(runs_api.router)
app.include_router(digests_api.router)
app.include_router(drift_api.router)
app.include_router(evals_api.router)
app.include_router(datasets_api.router)
app.include_router(regression_api.router)
app.include_router(compare_api.router)
app.include_router(figures_api.router)

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
