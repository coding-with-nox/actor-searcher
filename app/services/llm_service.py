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

    async def generate_queries(self, profile_summary: str, num_queries: int = 10) -> list[str]:
        prompt = (
            f"You are a casting agent assistant. Generate {num_queries} specific web search queries "
            f"to find casting calls and auditions for this actor.\n\n"
            f"Actor Profile:\n{profile_summary}\n\n"
            f"Target job types: film, TV series, commercials, theatre, voiceover, gaming, YouTube productions.\n"
            f"Rules:\n"
            f"- Queries must target Italian productions primarily (but include international)\n"
            f"- Each query must be specific enough to return casting call results\n"
            f"- Include actor's age range, location, and relevant skills in different queries\n"
            f"- Vary by job type and platform (use 'site:backstage.com', 'casting call', 'audizioni', etc.)\n"
            f"- Return ONLY a JSON array of strings, no other text\n\n"
            f'Example: ["casting call thriller Roma 25-30 anni non-union", "audizioni spot pubblicitario Milano maschio atletico"]'
        )
        data = await self._responses(prompt)
        result = json.loads(data)
        if isinstance(result, list):
            return [str(q) for q in result[:num_queries]]
        return []

    async def batch_match_profile(
        self,
        listings: list[dict[str, str]],
        profile_summary: str,
    ) -> list[dict[str, object]]:
        listings_json = json.dumps(listings, ensure_ascii=False, indent=2)
        prompt = (
            f"You are a senior casting agent. Evaluate each job listing against this actor's profile.\n\n"
            f"ACTOR PROFILE:\n{profile_summary}\n\n"
            f"JOB LISTINGS (JSON array):\n{listings_json}\n\n"
            f"For EACH listing return a JSON object with these exact fields:\n"
            f"- url: same url as input\n"
            f"- match_score: float 0.0-1.0 (0=complete mismatch, 1=perfect fit)\n"
            f"- rationale: 2-3 sentences plain language explaining the score\n"
            f"- red_flags: list of strings (requirements actor may not meet; empty list if none)\n"
            f"- role_category: one word genre/type (thriller/commercial/musical/voiceover/gaming/theatre/other)\n\n"
            f"Return ONLY a JSON array with one object per listing, no other text.\n"
            f"If a listing is clearly irrelevant (not a casting call), set match_score to 0.0."
        )
        data = await self._responses(prompt)
        result = json.loads(data)
        if isinstance(result, list):
            return result  # type: ignore[return-value]
        return []

    async def extract_deadline(self, text: str) -> str | None:
        prompt = (
            f"Extract the application deadline from this text. "
            f"Return JSON: {{\"deadline\": \"YYYY-MM-DD\"}} or {{\"deadline\": null}} if not found.\n\n"
            f"Text: {text[:2000]}"
        )
        data = await self._responses(prompt)
        result = json.loads(data)
        return result.get("deadline")

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
