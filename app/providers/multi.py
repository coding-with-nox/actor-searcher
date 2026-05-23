import asyncio
import structlog
from app.models.schemas import SearchResult
from app.providers.base import SearchProvider

log = structlog.get_logger()


class MultiProvider(SearchProvider):
    name = "multi"

    def __init__(self, providers: list[SearchProvider]) -> None:
        self._providers = providers

    async def search(self, query: str, options: dict[str, object]) -> list[SearchResult]:
        tasks = [p.search(query, options) for p in self._providers]
        results_per_provider = await asyncio.gather(*tasks, return_exceptions=True)
        all_results: list[SearchResult] = []
        for provider, result in zip(self._providers, results_per_provider):
            if isinstance(result, Exception):
                log.error("multi_provider.provider_failed", provider=provider.name, error=str(result))
            else:
                all_results.extend(result)
        return all_results
