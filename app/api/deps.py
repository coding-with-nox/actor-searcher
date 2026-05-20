from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.storage.database import get_db_session


async def db_session_dep() -> AsyncGenerator[AsyncSession, None]:
    async for s in get_db_session():
        yield s
