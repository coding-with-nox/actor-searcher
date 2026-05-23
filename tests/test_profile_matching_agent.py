import json
import pytest
import respx
import httpx
from app.agents.profile_matching_agent import ProfileMatchingAgent
from app.models.schemas import RankedListing, SearchResult
from app.profile.models import ActorProfile, PhysicalTraits
from app.services.llm_service import LLMService


def _make_profile() -> ActorProfile:
    return ActorProfile(
        name="Test",
        age=28,
        gender="male",
        languages=["Italian (native)"],
        physical=PhysicalTraits(height_cm=180, build="athletic", hair_color="brown", eye_color="green"),
        skills=["singing"],
        experience_level="emerging",
        union_status="non-union",
        location="Roma",
        max_travel_km=200,
        availability_from="2026-06-01",
    )


def _make_results(n: int = 3) -> list[SearchResult]:
    return [
        SearchResult(
            title=f"Role {i}",
            url=f"https://example.com/{i}",
            snippet=f"Casting call snippet {i}",
            source="tavily",
        )
        for i in range(n)
    ]


@respx.mock
async def test_profile_matching_returns_ranked_listings() -> None:
    llm_response = [
        {"url": "https://example.com/0", "match_score": 0.9, "rationale": "Great fit.", "red_flags": [], "role_category": "thriller"},
        {"url": "https://example.com/1", "match_score": 0.5, "rationale": "Partial fit.", "red_flags": ["requires driving license"], "role_category": "commercial"},
        {"url": "https://example.com/2", "match_score": 0.2, "rationale": "Poor fit.", "red_flags": ["wrong age range"], "role_category": "other"},
    ]
    respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"output_text": json.dumps(llm_response)})
    )
    agent = ProfileMatchingAgent(llm=LLMService(), minimum_score=0.3, batch_size=20)
    results = await agent.execute(_make_results(), _make_profile())
    assert len(results) == 2  # only score >= 0.3
    assert results[0].match_score == 0.9
    assert results[0].role_category == "thriller"
    assert isinstance(results[0], RankedListing)


@respx.mock
async def test_profile_matching_filters_below_minimum() -> None:
    llm_response = [
        {"url": "https://example.com/0", "match_score": 0.1, "rationale": "Bad fit.", "red_flags": [], "role_category": "other"},
    ]
    respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"output_text": json.dumps(llm_response)})
    )
    agent = ProfileMatchingAgent(llm=LLMService(), minimum_score=0.3, batch_size=20)
    results = await agent.execute(_make_results(1), _make_profile())
    assert results == []
