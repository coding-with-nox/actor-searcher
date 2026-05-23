import json
import pytest
import respx
import httpx
from app.agents.query_generator_agent import QueryGeneratorAgent
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


@respx.mock
async def test_query_generator_returns_list() -> None:
    queries = ["casting call thriller Roma", "audizioni spot pubblicitario"]
    respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"output_text": json.dumps(queries)})
    )
    agent = QueryGeneratorAgent(llm=LLMService(), num_queries=2)
    result = await agent.execute(_make_profile())
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(q, str) for q in result)


@respx.mock
async def test_query_generator_calls_llm_once() -> None:
    queries = ["casting call Roma"]
    captured: list[dict] = []

    def capture(request: httpx.Request, *_: object) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"output_text": json.dumps(queries)})

    respx.post("https://api.openai.com/v1/responses").mock(side_effect=capture)
    agent = QueryGeneratorAgent(llm=LLMService(), num_queries=1)
    await agent.execute(_make_profile())
    assert len(captured) == 1
    assert "Roma" in captured[0]["input"]
