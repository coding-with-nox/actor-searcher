from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import db_session_dep
from app.models.schemas import SearchCreate, SearchRead
from app.repositories.run_repository import RunRepository
from app.repositories.search_repository import SearchRepository

router = APIRouter()

@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/searches", response_model=list[SearchRead])
async def list_searches(session: AsyncSession = Depends(db_session_dep)) -> list[SearchRead]:
    repo = SearchRepository(session)
    return [SearchRead.model_validate(i) for i in await repo.list_searches()]

@router.post("/searches", response_model=SearchRead)
async def create_search(payload: SearchCreate, session: AsyncSession = Depends(db_session_dep)) -> SearchRead:
    repo = SearchRepository(session)
    item = await repo.create_search(payload)
    return SearchRead.model_validate(item)

@router.get("/runs")
async def list_runs(session: AsyncSession = Depends(db_session_dep)) -> list[dict[str, object]]:
    repo = RunRepository(session)
    return [{"id": r.id, "search_id": r.search_id, "status": r.status} for r in await repo.list_runs()]

@router.get("/results")
async def list_results(session: AsyncSession = Depends(db_session_dep)) -> list[dict[str, object]]:
    repo = RunRepository(session)
    return [{"id": r.id, "title": r.title, "url": r.url, "score": r.score} for r in await repo.list_results()]
