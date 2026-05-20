from app.models.schemas import SearchResult
from app.services.llm_service import LLMService


class RankingAgent:
    def __init__(self, llm: LLMService) -> None:
        self.llm = llm

    async def execute(self, results: list[SearchResult], keywords: list[str], minimum_score: float) -> list[SearchResult]:
        ranked: list[SearchResult] = []
        for item in results:
            score = await self.llm.score_relevance(item.title, item.snippet, keywords)
            item.score = score.score
            if item.score >= minimum_score:
                ranked.append(item)
        return ranked
