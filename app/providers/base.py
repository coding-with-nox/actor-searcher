from abc import ABC, abstractmethod
from app.models.schemas import SearchResult


class SearchProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, options: dict[str, object]) -> list[SearchResult]:
        raise NotImplementedError
