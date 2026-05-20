import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config.settings import get_settings
from app.core.exceptions import NonRetryableProviderError
from app.models.schemas import SearchResult
from app.providers.base import SearchProvider


class TavilyProvider(SearchProvider):
    name = "tavily"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    async def search(self, query: str, options: dict[str, object]) -> list[SearchResult]:
        settings = get_settings()
        headers = {"Authorization": f"Bearer {settings.tavily_api_key}"}
        payload = {"query": query, "search_depth": "advanced", "max_results": options.get("limit", 10)}
        async with httpx.AsyncClient(timeout=settings.provider.timeout_seconds) as client:
            response = await client.post("https://api.tavily.com/search", json=payload, headers=headers)
        if response.status_code >= 400:
            raise NonRetryableProviderError(f"Tavily failed: {response.text}")
        data = response.json().get("results", [])
        return [SearchResult(title=i.get("title", ""), url=i.get("url", ""), snippet=i.get("content", ""), content=i.get("raw_content"), source=self.name) for i in data]
