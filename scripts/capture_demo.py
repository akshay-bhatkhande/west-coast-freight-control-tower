#!/usr/bin/env python3
"""Capture Streamlit demo screenshots + a short GIF for portfolio media."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
STORE = Path(
    "/Users/akshaybhatkhande/Library/Application Support/Cursor/AgentStores/"
    "cursor_agent_stores/bc-46b21435-39e5-4da4-8fbf-b96928b46cae/files/media/"
    "west-coast-freight-control-tower"
)
URL = os.environ.get("STREAMLIT_URL", "http://localhost:8501")


async def _scroll_main(page, y: int) -> None:
    """Streamlit scrolls inside the app view container, not the window."""
    await page.evaluate(
        """(y) => {
          const el = document.querySelector('[data-testid="stAppViewContainer"]')
            || document.querySelector('.main')
            || document.scrollingElement;
          if (el) el.scrollTo(0, y);
        }""",
        y,
    )
    await page.wait_for_timeout(700)


def _letterbox(im: Image.Image, size=(960, 720)) -> Image.Image:
    im = im.convert("RGB")
    im.thumbnail(size)
    canvas = Image.new("RGB", size, (242, 245, 248))
    canvas.paste(im, ((size[0] - im.size[0]) // 2, (size[1] - im.size[1]) // 2))
    return canvas


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
        await page.wait_for_timeout(4000)

        await _scroll_main(page, 0)
        overview = ASSETS / "control-tower-overview.png"
        await page.screenshot(path=str(overview), full_page=False)
        print(f"Wrote {overview}")

        await page.get_by_text("Mode-shift scenario", exact=True).first.scroll_into_view_if_needed()
        await page.wait_for_timeout(1500)
        scenario = ASSETS / "scenario-slider.png"
        await page.screenshot(path=str(scenario), full_page=False)
        print(f"Wrote {scenario}")

        brief_heading = page.get_by_text("Weekly Ops Review", exact=True).first
        await brief_heading.scroll_into_view_if_needed()
        await page.wait_for_timeout(1500)
        brief = ASSETS / "ops-brief.png"
        box = await brief_heading.bounding_box()
        if box:
            await page.screenshot(
                path=str(brief),
                clip={
                    "x": max(0, box["x"] - 16),
                    "y": max(0, box["y"] - 8),
                    "width": min(1100, 1440 - max(0, box["x"] - 16)),
                    "height": min(980, 1200 - max(0, box["y"] - 8)),
                },
            )
        else:
            await page.screenshot(path=str(brief), full_page=False)
        print(f"Wrote {brief}")

        # Stitch a tall fullpage from scrolled container tiles
        await _scroll_main(page, 0)
        tiles: list[Image.Image] = []
        scroll_stops = (0, 850, 1700, 2550, 3400)
        for y in scroll_stops:
            await _scroll_main(page, y)
            tmp = ASSETS / f"_tile_{y}.png"
            await page.screenshot(path=str(tmp), full_page=False)
            tiles.append(Image.open(tmp).convert("RGB"))
            tmp.unlink(missing_ok=True)

        overlap = 200
        w, h = tiles[0].size
        band_h = h - overlap
        total_h = h + band_h * (len(tiles) - 1)
        canvas = Image.new("RGB", (w, total_h), (242, 245, 248))
        canvas.paste(tiles[0], (0, 0))
        for i, im in enumerate(tiles[1:], start=1):
            canvas.paste(im.crop((0, overlap, w, h)), (0, i * band_h))
        full = ASSETS / "control-tower-fullpage.png"
        canvas.save(full)
        print(f"Wrote {full}")

        frames = [_letterbox(Image.open(p)) for p in (overview, scenario, brief)]
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
