"""Capture the deterministic AgentOps console screenshot set.

The API and console must be running on ports 8000 and 5173, with
``scripts/seed_drift.py`` already applied.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "docs" / "screenshots"
WEB = "http://localhost:5173"
VIEWPORT = {"width": 1280, "height": 900}

PAGES = [
    ("01-drift-home.png", "/", True),
    ("02-trace-gantt.png", "/runs/seed-0080", True),
    ("03-run-comparison.png", "/compare?a=seed-0001&b=seed-0080", True),
    ("04-drift-detail.png", "/drift/quality", True),
    ("05-eval-results.png", "/evals", True),
]


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        page = await context.new_page()
        page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))

        for filename, route, full_page in PAGES:
            await page.goto(f"{WEB}{route}", wait_until="networkidle")
            await page.wait_for_timeout(800)
            target = OUT / filename
            await page.screenshot(path=str(target), full_page=full_page)
            print(f"wrote {target}")

        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
