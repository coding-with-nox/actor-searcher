from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import Search
from app.models.schemas import SearchCreate


class SearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_searches(self) -> list[Search]:
        return list((await self.session.execute(select(Search).order_by(Search.id))).scalars().all())

    async def create_search(self, payload: SearchCreate) -> Search:
        item = Search(name=payload.name, interval_minutes=payload.interval_minutes, config=payload.config)
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item
