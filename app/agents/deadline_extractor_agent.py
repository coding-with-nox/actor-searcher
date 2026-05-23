from datetime import datetime
import structlog
from app.models.schemas import SearchResult
from app.services.llm_service import LLMService

log = structlog.get_logger()


class DeadlineExtractorAgent:
    def __init__(self, llm: LLMService) -> None:
        self.llm = llm

    async def execute(self, results: list[SearchResult]) -> list[SearchResult]:
        for item in results:
            if item.published_at is not None:
                continue
            text = f"{item.title} {item.snippet} {item.content or ''}"
            try:
                date_str = await self.llm.extract_deadline(text)
                if date_str:
                    item.published_at = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception as exc:
                log.warning("deadline_extractor.failed", url=item.url, error=str(exc))
        return results
