import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.notifications.telegram_bot import TelegramBotNotifier
from app.models.schemas import RankedListing


def _make_listing(rank: int = 1) -> RankedListing:
    return RankedListing(
        title=f"Role {rank}",
        url=f"https://backstage.com/role/{rank}",
        snippet="Great casting call",
        source="backstage",
        match_score=0.85,
        rationale="Perfect fit for this actor.",
        red_flags=["requires driving license"],
        role_category="thriller",
    )


async def test_notifier_formats_message() -> None:
    notifier = TelegramBotNotifier(bot_token="fake", chat_id="123")
    listing = _make_listing()
    msg = notifier._format_message(listing)
    assert "Role 1" in msg
    assert "0.85" in msg
    assert "thriller" in msg.lower()
    assert "driving license" in msg


async def test_notifier_sends_with_inline_keyboard() -> None:
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=99))
    mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
    mock_bot.__aexit__ = AsyncMock(return_value=False)

    with patch("app.notifications.telegram_bot.Bot", return_value=mock_bot):
        notifier = TelegramBotNotifier(bot_token="fake", chat_id="123")
        await notifier.send_listing(1, _make_listing())

    mock_bot.send_message.assert_called_once()
    call_kwargs = mock_bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == "123"
    assert "reply_markup" in call_kwargs
