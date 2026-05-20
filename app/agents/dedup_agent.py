import hashlib
from app.models.schemas import SearchResult


class DedupAgent:
    async def execute(self, results: list[SearchResult]) -> list[SearchResult]:
        seen_urls: set[str] = set()
        seen_hashes: set[str] = set()
        unique: list[SearchResult] = []
        for item in results:
            content_hash = hashlib.sha256((item.title + item.snippet).encode()).hexdigest()
            if item.url in seen_urls or content_hash in seen_hashes:
                continue
            seen_urls.add(item.url)
            seen_hashes.add(content_hash)
            unique.append(item)
        return unique
