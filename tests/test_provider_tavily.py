import respx
import httpx
from app.providers.tavily import TavilyProvider


@respx.mock
async def test_tavily_provider() -> None:
    respx.post("https://api.tavily.com/search").mock(return_value=httpx.Response(200, json={"results": [{"title": "A", "url": "https://a", "content": "S"}]}))
    provider = TavilyProvider()
    result = await provider.search("query", {})
    assert result[0].title == "A"
