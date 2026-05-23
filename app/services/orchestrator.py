import hashlib
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.deadline_extractor_agent import DeadlineExtractorAgent
from app.agents.dedup_agent import DedupAgent
from app.agents.profile_matching_agent import ProfileMatchingAgent
from app.agents.query_generator_agent import QueryGeneratorAgent
from app.agents.search_agent import SearchAgent
from app.models.db import SearchResult as DBSearchResult
from app.notifications.telegram_bot import TelegramBotNotifier
from app.profile.loader import ProfileLoader
from app.repositories.run_repository import RunRepository

log = structlog.get_logger()


class SearchOrchestrator:
    def __init__(
        self,
        search_agent: SearchAgent,
        profile_matching_agent: ProfileMatchingAgent,
        query_generator_agent: QueryGeneratorAgent,
        dedup_agent: DedupAgent,
        profile_loader: ProfileLoader,
        deadline_extractor_agent: DeadlineExtractorAgent | None = None,
        notifier: TelegramBotNotifier | None = None,
        notification_top_n: int = 5,
    ) -> None:
        self.search_agent = search_agent
        self.profile_matching_agent = profile_matching_agent
        self.query_generator_agent = query_generator_agent
        self.dedup_agent = dedup_agent
        self.profile_loader = profile_loader
        self.deadline_extractor_agent = deadline_extractor_agent
        self.notifier = notifier
        self.notification_top_n = notification_top_n

    async def execute(self, session: AsyncSession, search_id: int, config: dict[str, object]) -> None:
        repo = RunRepository(session)
        run = await repo.create_run(search_id)
        try:
            profile = await self.profile_loader.load(session)
            queries = await self.query_generator_agent.execute(profile)
            log.info("orchestrator.queries_generated", count=len(queries))

            raw = await self.search_agent.execute(queries, {})
            deduped = await self.dedup_agent.execute(raw)
            log.info("orchestrator.deduped", count=len(deduped))

            if self.deadline_extractor_agent:
                deduped = await self.deadline_extractor_agent.execute(deduped)

            ranked = await self.profile_matching_agent.execute(deduped, profile)
            log.info("orchestrator.ranked", count=len(ranked))

            db_results: list[DBSearchResult] = []
            for r in ranked:
                content_hash = hashlib.sha256((r.title + r.snippet).encode()).hexdigest()
                db_result = DBSearchResult(
                    run_id=run.id,
                    title=r.title,
                    url=r.url,
                    snippet=r.snippet,
                    content=None,
                    source=r.source,
                    published_at=r.published_at,
                    score=r.match_score,
                    summary=r.rationale,
                    content_hash=content_hash,
                    role_category=r.role_category,
                    deadline=r.deadline,
                    rationale=r.rationale,
                    red_flags=r.red_flags,
                )
                db_results.append(db_result)

            await repo.save_results(run.id, db_results)
            # flush so SQLAlchemy populates .id on each db_result before passing to notifier
            await session.flush()

            if self.notifier:
                top = ranked[: self.notification_top_n]
                for i, listing in enumerate(top):
                    db_id = db_results[i].id or 0
                    await self.notifier.send_listing(db_id, listing)

            await repo.finalize_run(run, "success")
        except Exception as exc:
            log.error("orchestrator.failed", error=str(exc))
            await repo.finalize_run(run, "failed", str(exc))
            raise
