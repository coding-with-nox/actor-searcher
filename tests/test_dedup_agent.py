from app.agents.dedup_agent import DedupAgent
from app.models.schemas import SearchResult


async def test_dedup_agent_removes_duplicate_urls() -> None:
    agent = DedupAgent()
    items = [
        SearchResult(title="a", url="https://x", snippet="1", source="t"),
        SearchResult(title="b", url="https://x", snippet="2", source="t"),
    ]
    out = await agent.execute(items)
    assert len(out) == 1
