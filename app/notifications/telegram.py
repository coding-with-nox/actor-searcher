import httpx
from app.notifications.base import NotificationChannel


class TelegramNotifier(NotificationChannel):
    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send(self, payload: dict[str, object]) -> None:
        text = f"{payload['search']}: {payload['count']} findings"
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json={"chat_id": self.chat_id, "text": text})
