from app.models.schemas import RankedListing, SearchResult
from app.profile.models import ActorProfile
from app.services.llm_service import LLMService


class ProfileMatchingAgent:
    def __init__(self, llm: LLMService, minimum_score: float = 0.3, batch_size: int = 20) -> None:
        self.llm = llm
        self.minimum_score = minimum_score
        self.batch_size = batch_size

    async def execute(self, results: list[SearchResult], profile: ActorProfile) -> list[RankedListing]:
        profile_summary = profile.to_summary()
        ranked: list[RankedListing] = []

        for i in range(0, len(results), self.batch_size):
            batch = results[i : i + self.batch_size]
            listings_input = [
                {"url": r.url, "title": r.title, "snippet": r.snippet, "content": r.content or ""}
                for r in batch
            ]
            match_results = await self.llm.batch_match_profile(listings_input, profile_summary)

            score_by_url = {m["url"]: m for m in match_results}
            for result in batch:
                match = score_by_url.get(result.url)
                if not match:
                    continue
                score = float(match.get("match_score", 0.0))
                if score < self.minimum_score:
                    continue
                ranked.append(
                    RankedListing(
                        title=result.title,
                        url=result.url,
                        snippet=result.snippet,
                        source=result.source,
                        published_at=result.published_at,
                        content_hash=None,
                        match_score=score,
                        rationale=str(match.get("rationale", "")),
                        red_flags=list(match.get("red_flags", [])),
                        role_category=str(match.get("role_category", "other")),
                    )
                )

        return sorted(ranked, key=lambda x: x.match_score, reverse=True)
