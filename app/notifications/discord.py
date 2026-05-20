import httpx
from app.notifications.base import NotificationChannel


class DiscordNotifier(NotificationChannel):
    name = "discord"

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    async def send(self, payload: dict[str, object]) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(self.webhook_url, json={"content": f"{payload['search']}: {payload['count']} findings"})
