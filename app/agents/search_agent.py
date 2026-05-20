from app.models.schemas import SearchResult
from app.providers.base import SearchProvider


class SearchAgent:
    def __init__(self, provider: SearchProvider) -> None:
        self.provider = provider

    async def execute(self, queries: list[str], options: dict[str, object]) -> list[SearchResult]:
        results: list[SearchResult] = []
        for query in queries:
            results.extend(await self.provider.search(query, options))
        return results
