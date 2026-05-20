from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.dedup_agent import DedupAgent
from app.agents.ranking_agent import RankingAgent
from app.agents.search_agent import SearchAgent
from app.agents.summarizer_agent import SummarizerAgent
from app.models.db import SearchResult as DBSearchResult
from app.repositories.run_repository import RunRepository


class SearchOrchestrator:
    def __init__(self, search_agent: SearchAgent, ranking_agent: RankingAgent, summarizer_agent: SummarizerAgent, dedup_agent: DedupAgent) -> None:
        self.search_agent = search_agent
        self.ranking_agent = ranking_agent
        self.summarizer_agent = summarizer_agent
        self.dedup_agent = dedup_agent

    async def execute(self, session: AsyncSession, search_id: int, config: dict[str, object]) -> None:
        repo = RunRepository(session)
        run = await repo.create_run(search_id)
        try:
            queries = list(config.get("queries", []))
            raw = await self.search_agent.execute(queries, {})
            ranked = await self.ranking_agent.execute(raw, list(config.get("scoring", {}).get("keywords", [])), float(config.get("scoring", {}).get("minimum_score", 0.0)))
            summarized = await self.summarizer_agent.execute(ranked)
            deduped = await self.dedup_agent.execute(summarized)
            db_results = [DBSearchResult(run_id=run.id, title=r.title, url=r.url, snippet=r.snippet, content=r.content, source=r.source, published_at=r.published_at, score=r.score, summary=r.summary, content_hash=None) for r in deduped]
            await repo.save_results(run.id, db_results)
            await repo.finalize_run(run, "success")
        except Exception as exc:
            await repo.finalize_run(run, "failed", str(exc))
            raise
