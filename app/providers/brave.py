from app.models.schemas import SearchResult
from app.providers.base import SearchProvider


class BraveProvider(SearchProvider):
    name = "brave"

    async def search(self, query: str, options: dict[str, object]) -> list[SearchResult]:
        return [SearchResult(title=f"Brave placeholder for {query}", url="https://search.brave.com", snippet="Implement Brave API wiring", source=self.name)]
