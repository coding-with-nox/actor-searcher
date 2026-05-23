import json
import pytest
import respx
import httpx
from datetime import datetime
from app.agents.deadline_extractor_agent import DeadlineExtractorAgent
from app.models.schemas import SearchResult
from app.services.llm_service import LLMService


def _make_result(snippet: str, has_date: bool = False) -> SearchResult:
    return SearchResult(
        title="Some Role",
        url="https://example.com/role",
        snippet=snippet,
        source="test",
        published_at=datetime(2026, 5, 1) if has_date else None,
    )


@respx.mock
async def test_extracts_deadline_from_free_text() -> None:
    respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"output_text": json.dumps({"deadline": "2026-06-15"})})
    )
    agent = DeadlineExtractorAgent(llm=LLMService())
    results = await agent.execute([_make_result("Apply by June 15th 2026")])
    assert results[0].published_at is not None
    assert results[0].published_at.year == 2026
    assert results[0].published_at.month == 6


async def test_skips_result_with_existing_date() -> None:
    """No LLM call when published_at is already set — no mock needed."""
    agent = DeadlineExtractorAgent(llm=LLMService())
    results = await agent.execute([_make_result("some text", has_date=True)])
    assert results[0].published_at is not None


@respx.mock
async def test_handles_no_deadline_found() -> None:
    respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"output_text": json.dumps({"deadline": None})})
    )
    agent = DeadlineExtractorAgent(llm=LLMService())
    results = await agent.execute([_make_result("No deadline mentioned")])
    assert results[0].published_at is None
