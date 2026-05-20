from app.models.schemas import SearchResult
from app.services.llm_service import LLMService


class SummarizerAgent:
    def __init__(self, llm: LLMService) -> None:
        self.llm = llm

    async def execute(self, results: list[SearchResult]) -> list[SearchResult]:
        for item in results:
            item.summary = await self.llm.summarize(item.title, item.snippet)
        return results
