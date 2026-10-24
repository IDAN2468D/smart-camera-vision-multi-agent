import asyncio
import base64
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class BrowserAgentService:
    """Autonomous Playwright Browser Agent for Live Israeli E-Commerce Price Capture."""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._playwright_available = True
        try:
            import playwright
        except ImportError:
            self._playwright_available = False
            logger.warning("[BrowserAgent] Playwright not installed. Live price screenshots disabled.")

    async def _async_capture_screenshot(self, query: str) -> Optional[Dict[str, Any]]:
        """Launch headless Chromium, search Israeli commerce portals, and capture live screenshot."""
        if not self._playwright_available:
            return None

        from playwright.async_api import async_playwright

        encoded_query = quote_plus(f"site:zap.co.il {query} מחיר")
        target_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context(
                    viewport={"width": 800, "height": 600},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                # Navigate with 6s timeout
                await page.goto(target_url, timeout=6000, wait_until="domcontentloaded")

                # Capture compact JPEG screenshot of the top results
                screenshot_bytes = await page.screenshot(
                    type="jpeg",
                    quality=70,
                    clip={"x": 0, "y": 0, "width": 800, "height": 450}
                )
                await browser.close()

                b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                return {
                    "screenshot_base64": f"data:image/jpeg;base64,{b64}",
                    "store_name": "Zap.co.il / KSP",
                    "url": target_url
                }
        except Exception as e:
            logger.warning(f"[BrowserAgent] Playwright screenshot capture failed ({e}). Continuing with DDG fallback.")
            return None

    def capture_retail_price(self, product_name: str) -> Optional[Dict[str, Any]]:
        """Synchronously trigger browser capture (cached, non-blocking fallback)."""
        clean_name = product_name.strip().lower()
        if not clean_name:
            return None

        if clean_name in self._cache:
            return self._cache[clean_name]

        try:
            # Run in event loop or thread
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    asyncio.wait_for(self._async_capture_screenshot(clean_name), timeout=8.0)
                )
                if result:
                    self._cache[clean_name] = result
                return result
            finally:
                loop.close()
        except Exception as e:
            logger.debug(f"[BrowserAgent] Capture error: {e}")
            return None

# Singleton service instance
browser_agent_service = BrowserAgentService()
