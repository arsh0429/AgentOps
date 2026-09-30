"""Record a scripted UI tour of AgentOps via Playwright.

Two surfaces in one tour:
    - Consumer UI (researcher reading) on http://localhost:5174
    - Platform UI (engineer monitoring) on http://localhost:5173

The recording lands at docs/walkthrough.mp4. Product captions are rendered
inside the browser during capture so they stay aligned with each UI section.

Prereqs (one-time):
    uv add --dev playwright
    uv run playwright install chromium

All three servers must be running with seeded data + at least one digest:
    AGENTOPS_API_PORT=8001 make server   (port 8001)
    AGENTOPS_API_PORT=8001 make web      (port 5173)
    AGENTOPS_API_PORT=8001 make digest   (port 5174)
    uv run python scripts/load_golden.py
    uv run python scripts/seed_drift.py

Usage:
    uv run python scripts/record_walkthrough.py
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg
from playwright.async_api import async_playwright

REPO = Path(__file__).resolve().parent.parent
PLATFORM_WEB = "http://localhost:5173"
CONSUMER_WEB = "http://localhost:5174"
OUT_DIR = REPO / "tmp_recording"
WALKTHROUGH_MP4 = REPO / "docs" / "walkthrough.mp4"
VIEWPORT = {"width": 1280, "height": 720}

# Concrete IDs we know exist in the seeded DB / live runs.
DIGEST_RUN_ID = "seed-0099"          # deterministic mock digest
TRACE_ID = "seed-0080"              # late-epoch run with drift contribution
COMPARE_A = "seed-0001"             # high-quality epoch
COMPARE_B = "seed-0080"             # low-quality epoch (post-shift)


def _ffmpeg_executable() -> str:
    installed = shutil.which("ffmpeg")
    if installed:
        return installed
    portable = imageio_ffmpeg.get_ffmpeg_exe()
    if portable:
        return portable
    playwright_root = Path.home() / "AppData" / "Local" / "ms-playwright"
    candidates = sorted(playwright_root.glob("ffmpeg-*/ffmpeg-*.exe"), reverse=True)
    if candidates:
        return str(candidates[0])
    raise SystemExit("ffmpeg is unavailable; run: uv run playwright install chromium")


async def _caption(page, text: str) -> None:
    await page.evaluate(
        """text => {
          let node = document.getElementById('agentops-walkthrough-caption');
          if (!node) {
            node = document.createElement('div');
            node.id = 'agentops-walkthrough-caption';
            Object.assign(node.style, {
              position: 'fixed', left: '50%', bottom: '24px', transform: 'translateX(-50%)',
              zIndex: '2147483647', maxWidth: '1100px', padding: '12px 18px',
              color: 'white', background: 'rgba(0,0,0,0.78)', borderRadius: '5px',
              font: '600 22px Arial, sans-serif', textAlign: 'center', lineHeight: '1.25',
              boxShadow: '0 2px 12px rgba(0,0,0,0.25)', pointerEvents: 'none'
            });
            document.body.appendChild(node);
          }
          node.textContent = text;
        }""",
        text,
    )


async def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(OUT_DIR),
            record_video_size=VIEWPORT,
            device_scale_factor=1,
        )
        page = await context.new_page()
        page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))

        # ── Consumer surface (researcher) ─────────────────────────

        # 0–6 s — Search form: researcher types a research interest. We don't
        # submit (that would cost ~$0.30 in real Anthropic spend on every
        # recording). Just focus + type a plausible interest to show the seam.
        await page.goto(f"{CONSUMER_WEB}/", wait_until="networkidle")
        await _caption(page, "Search a subject to generate an instrumented research digest")
        await page.wait_for_timeout(800)
        try:
            interest_input = page.locator("#research-interest")
            await interest_input.click(timeout=2000)
            await page.keyboard.type(
                "concept drift detection in streaming ML",
                delay=70,
            )
            await page.wait_for_timeout(1200)
        except Exception:
            await page.wait_for_timeout(2000)

        # 6–11 s — Digest list (the cards below the form)
        try:
            # scroll past the form so the cards are the focal area
            await _caption(page, "Saved research runs remain available as browsable digests")
            await page.evaluate("window.scrollTo({ top: 320, behavior: 'smooth' })")
            await page.wait_for_timeout(4000)
            await page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
            await page.wait_for_timeout(500)
        except Exception:
            await page.wait_for_timeout(4500)

        # 11–17 s — Digest detail: rendered Markdown of the agent's output
        await page.goto(
            f"{CONSUMER_WEB}/digests/{DIGEST_RUN_ID}", wait_until="networkidle"
        )
        await _caption(page, "Agent output is rendered with its run identity and provenance")
        await page.wait_for_timeout(4000)
        try:
            await page.evaluate("window.scrollTo({ top: 220, behavior: 'smooth' })")
            await page.wait_for_timeout(1500)
        except Exception:
            pass

        # ── Platform surface (engineer) ────────────────────────────

        # 11–20 s — Drift home: four signals firing (input, tool-call,
        # quality, attribution). Attribution is the new card; we hover it
        # last so the surrounding caption can call it out as the
        # FADMON-style fourth signal without the eye fighting earlier
        # hovers.
        await page.goto(f"{PLATFORM_WEB}/", wait_until="networkidle")
        await _caption(page, "Input, tool-call, quality, and attribution drift update continuously")
        await page.wait_for_timeout(2000)
        for sel in [
            "a:has-text('Lexical input drift')",
            "a:has-text('Tool-call drift')",
            "a:has-text('Quality drift')",
            "a:has-text('Attribution drift')",
        ]:
            try:
                await page.locator(sel).hover(timeout=1500)
                await page.wait_for_timeout(1100)
            except Exception:
                pass
        await page.wait_for_timeout(600)

        # 18–28 s — Trace detail (Gantt) with a click on a worker span
        await page.goto(f"{PLATFORM_WEB}/runs/{TRACE_ID}", wait_until="networkidle")
        await _caption(page, "OpenTelemetry reconstructs planner, worker, and tool spans")
        await page.wait_for_timeout(2500)
        try:
            bars = page.locator("[data-test='gantt-bar']")
            count = await bars.count()
            if count >= 2:
                await bars.nth(min(2, count - 1)).click(timeout=2000)
                await page.wait_for_timeout(2500)
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        # 28–34 s — Drift detail (quality) — chart with threshold
        await page.goto(f"{PLATFORM_WEB}/drift/quality", wait_until="networkidle")
        await _caption(page, "ADWIN detects changes in streaming evaluation quality")
        await page.wait_for_timeout(5500)

        # 34–40 s — Drift detail (attribution) — the new fourth signal,
        # PSI on the per-paper citation-weight distribution.
        await page.goto(f"{PLATFORM_WEB}/drift/attribution", wait_until="networkidle")
        await _caption(page, "PSI surfaces shifts in citation attribution")
        await page.wait_for_timeout(5500)

        # 34–43 s — Run comparison — scorecard + tool-call distribution shift
        await page.goto(
            f"{PLATFORM_WEB}/compare?a={COMPARE_A}&b={COMPARE_B}",
            wait_until="networkidle",
        )
        await _caption(page, "Compare runs by score, cost, tokens, and tool distribution")
        await page.wait_for_timeout(4500)
        try:
            await page.evaluate("window.scrollTo({ top: 200, behavior: 'smooth' })")
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
            await page.wait_for_timeout(1500)
        except Exception:
            pass

        # 43–47 s — Eval results — four sparklines
        await page.goto(f"{PLATFORM_WEB}/evals", wait_until="networkidle")
        await _caption(page, "Judges and invariants provide evaluation trends for every run")
        await page.wait_for_timeout(3500)

        # Close to finalise the video file.
        await context.close()
        await browser.close()

    # Find the captured webm and transcode it to a broadly playable MP4.
    webms = list(OUT_DIR.glob("*.webm"))
    if not webms:
        raise SystemExit("no recording produced")
    webm = max(webms, key=lambda p: p.stat().st_mtime)
    print(f"recorded {webm} ({webm.stat().st_size // 1024} KB)")

    WALKTHROUGH_MP4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _ffmpeg_executable(), "-y", "-loglevel", "error",
        "-i", str(webm),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", "30", "-crf", "23", "-preset", "medium",
        "-movflags", "+faststart",
        str(WALKTHROUGH_MP4),
    ]
    subprocess.run(cmd, check=True)
    print(f"wrote {WALKTHROUGH_MP4} ({WALKTHROUGH_MP4.stat().st_size // 1024} KB)")

    shutil.rmtree(OUT_DIR, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
