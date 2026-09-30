"""Drive a clean, scripted demo of AgentOps for the recorded walkthrough.

Steps:
1. Load the golden dataset.
2. Seed synthetic drift.
3. Run two live agent invocations (different research interests).
4. Trigger a Mode 2 regression run.

Designed so you can record the screen while this runs in the background and
the UI updates live. Requires the server (port 8000) and web (port 5173) to
be running already.
"""
from __future__ import annotations

import asyncio
import os
import subprocess

import httpx


async def _agent_run(interest: str) -> None:
    env = os.environ.copy()
    env["AGENTOPS_ENDPOINT"] = env.get("AGENTOPS_ENDPOINT", "http://localhost:8000/ingest")
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "python", "-m", "agentops_research_agent", interest,
        env=env, stdout=subprocess.DEVNULL,
    )
    returncode = await proc.wait()
    if returncode:
        raise RuntimeError(f"research agent exited with code {returncode}")


async def main() -> None:
    print("loading golden dataset…")
    subprocess.run(["uv", "run", "python", "scripts/load_golden.py"], check=True)
    print("seeding synthetic drift…")
    subprocess.run(["uv", "run", "python", "scripts/seed_drift.py"], check=True)
    print("running 2 live agent invocations (this calls the real Anthropic API)…")
    await asyncio.gather(
        _agent_run("concept drift detection in streaming ML"),
        _agent_run("multi-agent orchestration with tool use"),
    )
    print("triggering Mode 2 regression…")
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/regressions", json={
            "dataset_id": "golden-arxiv-v1",
            "model": "claude-sonnet-4-6",
        })
        response.raise_for_status()
    print("done. record the UI now.")


if __name__ == "__main__":
    asyncio.run(main())
