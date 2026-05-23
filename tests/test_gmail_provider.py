import pytest
from unittest.mock import MagicMock, patch
from app.providers.gmail_imap import GmailIMAPProvider
from app.models.schemas import SearchResult


def _mock_imap(messages: list[tuple[bytes, bytes]]) -> MagicMock:
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.login = MagicMock()
    mock_conn.select = MagicMock(return_value=("OK", [b"1"]))
    ids = b" ".join(str(i + 1).encode() for i in range(len(messages)))
    mock_conn.search = MagicMock(return_value=("OK", [ids]))

    def fetch_side(msg_id: bytes, fmt: str):
        idx = int(msg_id) - 1
        if idx >= len(messages):
            return ("OK", [])
        subj, body = messages[idx]
        raw = (
            f"Subject: {subj.decode()}\r\nFrom: agency@casting.com\r\n\r\n{body.decode()}"
        ).encode()
        return ("OK", [(b"", raw)])

    mock_conn.fetch = MagicMock(side_effect=fetch_side)
    return mock_conn


async def test_gmail_returns_search_results() -> None:
    messages = [
        (b"Casting Call: Lead Role Thriller", b"Looking for male actor 25-35 in Rome. Apply by June 30."),
        (b"Audition: Commercial Spot Milano", b"Athletic build needed. Deadline: 2026-07-01."),
    ]
    mock_imap = _mock_imap(messages)
    with patch("app.providers.gmail_imap.imaplib.IMAP4_SSL", return_value=mock_imap):
        provider = GmailIMAPProvider(
            address="actor@gmail.com",
            app_password="pw",
            casting_senders=["agency@casting.com"],
        )
        results = await provider.search("", {})
    assert len(results) == 2
    assert all(isinstance(r, SearchResult) for r in results)
    assert results[0].source == "gmail"
    assert "Thriller" in results[0].title


async def test_gmail_ttl_cache_prevents_second_fetch() -> None:
    """Second call within TTL returns [] without IMAP connection."""
    messages = [(b"Role", b"body")]
    mock_imap = _mock_imap(messages)
    with patch("app.providers.gmail_imap.imaplib.IMAP4_SSL", return_value=mock_imap) as mock_cls:
        provider = GmailIMAPProvider(
            address="actor@gmail.com",
            app_password="pw",
            casting_senders=["agency@casting.com"],
            cache_ttl_seconds=300.0,
        )
        first = await provider.search("", {})
        second = await provider.search("", {})
    assert len(first) == 1
    assert second == []
    assert mock_cls.call_count == 1  # IMAP only connected once


async def test_gmail_returns_empty_on_connection_error() -> None:
    with patch("app.providers.gmail_imap.imaplib.IMAP4_SSL", side_effect=ConnectionError("refused")):
        provider = GmailIMAPProvider(
            address="actor@gmail.com",
            app_password="pw",
            casting_senders=["agency@casting.com"],
        )
        results = await provider.search("", {})
    assert results == []
