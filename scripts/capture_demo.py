#!/usr/bin/env python3
"""Capture Streamlit demo screenshots + a short GIF for portfolio media."""

from __future__ import annotations

import asyncio
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
STORE = Path(
    "/Users/akshaybhatkhande/Library/Application Support/Cursor/AgentStores/"
    "cursor_agent_stores/bc-46b21435-39e5-4da4-8fbf-b96928b46cae/files/media/"
    "west-coast-freight-control-tower"
)
URL = "http://localhost:8501"


async def main() -> None:
    from playwright.async_api import async_playwright

    ASSETS.mkdir(parents=True, exist_ok=True)
    STORE.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1200})
        await page.goto(URL, wait_until="networkidle", timeout=120_000)
        await page.wait_for_selector("text=West Coast Freight Control Tower", timeout=120_000)
        await page.wait_for_selector("text=Corridor concentration", timeout=120_000)
        await page.wait_for_timeout(5000)

        overview = ASSETS / "control-tower-overview.png"
        await page.screenshot(path=str(overview), full_page=False)
        print(f"Wrote {overview}")

        # Streamlit scrolls inside [data-testid="stAppViewContainer"]
        for text in ("Mode-shift scenario", "Weekly Ops Review"):
            loc = page.get_by_text(text, exact=True).first
            await loc.scroll_into_view_if_needed()
            await page.wait_for_timeout(2000)

        scenario = ASSETS / "scenario-slider.png"
        await page.get_by_text("Mode-shift scenario", exact=True).first.scroll_into_view_if_needed()
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(scenario), full_page=False)
        print(f"Wrote {scenario}")

        brief = ASSETS / "ops-brief.png"
        await page.get_by_text("Weekly Ops Review", exact=True).first.scroll_into_view_if_needed()
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(brief), full_page=False)
        print(f"Wrote {brief}")

        full = ASSETS / "control-tower-fullpage.png"
        await page.screenshot(path=str(full), full_page=True)
        print(f"Wrote {full}")

        frames = []
        for path in (overview, scenario, brief):
            im = Image.open(path).convert("RGB").resize((960, 720))
            frames.append(im)
        gif_path = ASSETS / "control-tower-demo.gif"
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=1600,
            loop=0,
        )
        print(f"Wrote {gif_path}")

        for src in (overview, scenario, brief, full, gif_path):
            dest = STORE / src.name
            dest.write_bytes(src.read_bytes())
            print(f"Copied {dest}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
