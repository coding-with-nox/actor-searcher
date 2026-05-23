from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.agents.dedup_agent import DedupAgent
from app.agents.profile_matching_agent import ProfileMatchingAgent
from app.agents.query_generator_agent import QueryGeneratorAgent
from app.agents.search_agent import SearchAgent
from app.api.routes import router
from app.config.settings import get_settings
from app.core.logging import configure_logging
from app.notifications.telegram_bot import TelegramBotNotifier
from app.notifications.telegram_handler import build_application
from app.profile.loader import ProfileLoader
from app.providers.tavily import TavilyProvider
from app.scheduler.scheduler_service import SchedulerService
from app.services.llm_service import LLMService
from app.services.orchestrator import SearchOrchestrator

settings = get_settings()
configure_logging(settings.log_level)

llm = LLMService()

notifier: TelegramBotNotifier | None = None
telegram_app = None
if settings.telegram_enabled and settings.telegram_bot_token:
    notifier = TelegramBotNotifier(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )
    telegram_app = build_application(settings.telegram_bot_token)

search_orchestrator = SearchOrchestrator(
    search_agent=SearchAgent(TavilyProvider()),
    profile_matching_agent=ProfileMatchingAgent(
        llm=llm,
        minimum_score=settings.minimum_match_score,
        batch_size=settings.matching_batch_size,
    ),
    query_generator_agent=QueryGeneratorAgent(llm=llm),
    dedup_agent=DedupAgent(),
    profile_loader=ProfileLoader(yaml_path=settings.actor_profile_path),
    notifier=notifier,
    notification_top_n=settings.notification_top_n,
)
scheduler = SchedulerService(search_orchestrator)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await scheduler.start()
    if telegram_app:
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling()
    yield
    if telegram_app:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
    await scheduler.shutdown()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router, prefix="/api/v1")
