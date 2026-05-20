from app.models.schemas import SearchResult
from app.notifications.base import NotificationChannel


class NotificationAgent:
    def __init__(self, channels: list[NotificationChannel]) -> None:
        self.channels = channels

    async def execute(self, search_name: str, results: list[SearchResult]) -> None:
        payload = {"search": search_name, "count": len(results), "items": [r.model_dump() for r in results[:5]]}
        for channel in self.channels:
            await channel.send(payload)
