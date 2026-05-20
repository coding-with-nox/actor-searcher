from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import SearchRun, SearchResult


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, search_id: int) -> SearchRun:
        run = SearchRun(search_id=search_id, status="running")
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def finalize_run(self, run: SearchRun, status: str, error_message: str | None = None) -> None:
        run.status = status
        run.error_message = error_message
        from datetime import datetime, timezone
        run.finished_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def save_results(self, run_id: int, results: list[SearchResult]) -> None:
        for r in results:
            self.session.add(r)
        await self.session.commit()

    async def list_runs(self) -> list[SearchRun]:
        return list((await self.session.execute(select(SearchRun).order_by(SearchRun.id.desc()))).scalars().all())

    async def list_results(self) -> list[SearchResult]:
        return list((await self.session.execute(select(SearchResult).order_by(SearchResult.id.desc()))).scalars().all())
