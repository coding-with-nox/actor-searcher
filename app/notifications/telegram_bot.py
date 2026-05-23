import structlog
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from app.models.schemas import RankedListing
from app.notifications.base import NotificationChannel

log = structlog.get_logger()


class TelegramBotNotifier(NotificationChannel):
    name = "telegram_bot"

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id

    def _format_message(self, listing: RankedListing) -> str:
        deadline_str = listing.deadline.strftime("%d %b") if listing.deadline else "N/A"
        red_flags_str = ""
        if listing.red_flags:
            red_flags_str = f"\n⚠️ Red flags: {', '.join(listing.red_flags)}"
        return (
            f"🎭 {listing.title}\n"
            f"📍 {listing.source.upper()} | Score: {listing.match_score:.2f} | "
            f"Categoria: {listing.role_category} | Scadenza: {deadline_str}\n\n"
            f'"{listing.rationale}"{red_flags_str}\n\n'
            f"🔗 {listing.url}"
        )

    async def send_listing(self, result_id: int, listing: RankedListing) -> None:
        bot = Bot(token=self._bot_token)
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Invia CV", callback_data=f"approve:{result_id}"),
                    InlineKeyboardButton("⭐ Salva", callback_data=f"save:{result_id}:{listing.role_category}"),
                    InlineKeyboardButton("❌ Ignora", callback_data=f"ignore:{result_id}:{listing.role_category}"),
                ]
            ]
        )
        async with bot:
            await bot.send_message(
                chat_id=self._chat_id,
                text=self._format_message(listing),
                reply_markup=keyboard,
                parse_mode=None,
            )
        log.info("telegram.listing_sent", result_id=result_id, score=listing.match_score)

    async def send(self, payload: dict[str, object]) -> None:
        pass
