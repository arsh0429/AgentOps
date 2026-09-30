"""Capture two screenshots of the consumer digest UI.

Outputs:
    docs/screenshots/07-digest-list.png
    docs/screenshots/08-digest-view.png

The digest UI must be running on http://localhost:5174 with the AgentOps
server up on the configured port and at least one digestable run present.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "docs" / "screenshots"
WEB = "http://localhost:5174"
RUN_ID = "seed-0099"
VIEWPORT = {"width": 1280, "height": 900}


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=1,
        )
        page = await context.new_page()
        page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))

        await page.goto(f"{WEB}/", wait_until="networkidle")
        await page.wait_for_timeout(800)
        list_path = OUT / "07-digest-list.png"
        await page.screenshot(path=str(list_path), full_page=True)
        print(f"wrote {list_path}")

        await page.goto(f"{WEB}/digests/{RUN_ID}", wait_until="networkidle")
        await page.wait_for_timeout(800)
        view_path = OUT / "08-digest-view.png"
        await page.screenshot(path=str(view_path), full_page=False)
        print(f"wrote {view_path}")

        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
