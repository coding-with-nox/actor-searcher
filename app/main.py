from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.agents.dedup_agent import DedupAgent
from app.agents.ranking_agent import RankingAgent
from app.agents.search_agent import SearchAgent
from app.agents.summarizer_agent import SummarizerAgent
from app.api.routes import router
from app.config.settings import get_settings
from app.core.logging import configure_logging
from app.providers.tavily import TavilyProvider
from app.scheduler.scheduler_service import SchedulerService
from app.services.llm_service import LLMService
from app.services.orchestrator import SearchOrchestrator

settings = get_settings()
configure_logging(settings.log_level)

search_orchestrator = SearchOrchestrator(
    search_agent=SearchAgent(TavilyProvider()),
    ranking_agent=RankingAgent(LLMService()),
    summarizer_agent=SummarizerAgent(LLMService()),
    dedup_agent=DedupAgent(),
)
scheduler = SchedulerService(search_orchestrator)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await scheduler.start()
    yield
    await scheduler.shutdown()

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router, prefix="/api/v1")
