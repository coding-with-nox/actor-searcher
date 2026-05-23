from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.agents.deadline_extractor_agent import DeadlineExtractorAgent
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
from app.providers.backstage import BackstageProvider
from app.providers.base import SearchProvider
from app.providers.gmail_imap import GmailIMAPProvider
from app.providers.multi import MultiProvider
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

# Build provider list based on enabled flags
providers: list[SearchProvider] = [TavilyProvider()]

if settings.backstage_enabled and settings.backstage_email:
    providers.append(
        BackstageProvider(
            email=settings.backstage_email,
            password=settings.backstage_password,
            max_listings=settings.backstage_max_listings,
        )
    )

if settings.gmail_enabled and settings.gmail_address:
    senders = [s.strip() for s in settings.gmail_casting_senders.split(",") if s.strip()]
    providers.append(
        GmailIMAPProvider(
            address=settings.gmail_address,
            app_password=settings.gmail_app_password,
            casting_senders=senders,
            imap_host=settings.gmail_imap_host,
            imap_port=settings.gmail_imap_port,
        )
    )

search_orchestrator = SearchOrchestrator(
    search_agent=SearchAgent(MultiProvider(providers)),
    profile_matching_agent=ProfileMatchingAgent(
        llm=llm,
        minimum_score=settings.minimum_match_score,
        batch_size=settings.matching_batch_size,
    ),
    query_generator_agent=QueryGeneratorAgent(llm=llm),
    dedup_agent=DedupAgent(),
    profile_loader=ProfileLoader(yaml_path=settings.actor_profile_path),
    deadline_extractor_agent=DeadlineExtractorAgent(llm=llm),
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
