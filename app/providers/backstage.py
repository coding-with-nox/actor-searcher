import asyncio
import structlog
from playwright.async_api import async_playwright
from app.models.schemas import SearchResult
from app.providers.base import SearchProvider

log = structlog.get_logger()

BACKSTAGE_LOGIN_URL = "https://www.backstage.com/login"
BACKSTAGE_SEARCH_URL = "https://www.backstage.com/casting-calls"
CRAWL_DELAY_SECONDS = 3.0


class BackstageProvider(SearchProvider):
    name = "backstage"

    def __init__(self, email: str, password: str, max_listings: int = 50) -> None:
        self._email = email
        self._password = password
        self._max_listings = max_listings

    async def search(self, query: str, options: dict[str, object]) -> list[SearchResult]:
        try:
            raw = await self._scrape_listings(query)
            return [
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    source=self.name,
                )
                for item in raw
                if item.get("url")
            ]
        except Exception as exc:
            log.error("backstage.scrape_failed", error=str(exc))
            return []

    async def _scrape_listings(self, query: str) -> list[dict[str, str]]:
        listings: list[dict[str, str]] = []
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (compatible; actor-searcher)"
            )
            page = await context.new_page()
            try:
                await self._login(page)
                await asyncio.sleep(CRAWL_DELAY_SECONDS)
                await page.goto(
                    f"{BACKSTAGE_SEARCH_URL}?q={query}", wait_until="networkidle"
                )
                await asyncio.sleep(CRAWL_DELAY_SECONDS)
                listings = await self._extract_listings(page)
            finally:
                await browser.close()
        return listings[: self._max_listings]

    async def _login(self, page: object) -> None:
        from playwright.async_api import Page
        assert isinstance(page, Page)
        await page.goto(BACKSTAGE_LOGIN_URL, wait_until="networkidle")
        await page.fill('input[type="email"]', self._email)
        await page.fill('input[type="password"]', self._password)
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard**", timeout=15000)

    async def _extract_listings(self, page: object) -> list[dict[str, str]]:
        from playwright.async_api import Page
        assert isinstance(page, Page)
        # Selectors are illustrative — update after inspecting real Backstage DOM
        cards = await page.query_selector_all('[data-testid="casting-card"]')
        results: list[dict[str, str]] = []
        for card in cards:
            title_el = await card.query_selector("h2, h3, .title")
            link_el = await card.query_selector("a[href]")
            desc_el = await card.query_selector("p, .description")
            title = (await title_el.inner_text()).strip() if title_el else ""
            href = await link_el.get_attribute("href") if link_el else ""
            url = f"https://www.backstage.com{href}" if href and href.startswith("/") else (href or "")
            snippet = (await desc_el.inner_text()).strip() if desc_el else ""
            if title and url:
                results.append({"title": title, "url": url, "snippet": snippet})
        return results
