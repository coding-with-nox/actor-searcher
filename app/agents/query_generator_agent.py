from app.profile.models import ActorProfile
from app.services.llm_service import LLMService


class QueryGeneratorAgent:
    def __init__(self, llm: LLMService, num_queries: int = 10) -> None:
        self.llm = llm
        self.num_queries = num_queries

    async def execute(self, profile: ActorProfile) -> list[str]:
        return await self.llm.generate_queries(profile.to_summary(), self.num_queries)
