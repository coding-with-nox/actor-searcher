import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from app.feedback.learner import PreferenceLearner
from app.models.db import Search
from app.services.orchestrator import SearchOrchestrator
from app.storage.database import SessionLocal

log = structlog.get_logger()


class SchedulerService:
    def __init__(
        self, orchestrator: SearchOrchestrator, learner: PreferenceLearner | None = None
    ) -> None:
        self.scheduler = AsyncIOScheduler()
        self.orchestrator = orchestrator
        self.learner = learner or PreferenceLearner()

    async def register_jobs(self) -> None:
        async with SessionLocal() as session:
            searches = (
                await session.execute(select(Search).where(Search.enabled.is_(True)))
            ).scalars().all()
        for search in searches:
            self.scheduler.add_job(
                self._run_job,
                "interval",
                minutes=search.interval_minutes,
                id=f"search-{search.id}",
                args=[search.id, search.config],
                replace_existing=True,
            )
        self.scheduler.add_job(
            self._run_learner,
            "interval",
            weeks=1,
            id="preference-learner",
            replace_existing=True,
        )
        log.info("scheduler.jobs_registered", search_count=len(searches))

    async def _run_job(self, search_id: int, config: dict[str, object]) -> None:
        async with SessionLocal() as session:
            async with session.begin():
                await self.orchestrator.execute(session, search_id, config)

    async def _run_learner(self) -> None:
        async with SessionLocal() as session:
            async with session.begin():
                await self.learner.run(session)
        log.info("scheduler.learner_run_complete")

    async def start(self) -> None:
        await self.register_jobs()
        self.scheduler.start()

    async def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
