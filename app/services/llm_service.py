import json
import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config.settings import get_settings


class RelevanceOutput(BaseModel):
    score: float
    reason: str


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    async def score_relevance(self, title: str, snippet: str, keywords: list[str]) -> RelevanceOutput:
        prompt = f"Score relevance from 0 to 1 for title/snippet with keywords={keywords}. Return JSON with score and reason. title={title} snippet={snippet}"
        data = await self._responses(prompt)
        return RelevanceOutput.model_validate_json(data)

    async def summarize(self, title: str, snippet: str) -> str:
        prompt = f"Summarize in 2 sentences: {title}\n{snippet}"
        data = await self._responses(prompt)
        payload = json.loads(data)
        return str(payload.get("summary", ""))

    async def _responses(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}
        body = {"model": self.settings.openai_model, "input": prompt}
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post("https://api.openai.com/v1/responses", headers=headers, json=body)
            r.raise_for_status()
        output = r.json().get("output_text")
        if output:
            return output
        return '{"score":0.5,"reason":"fallback","summary":""}'
