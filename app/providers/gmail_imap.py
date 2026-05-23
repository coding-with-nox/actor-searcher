import asyncio
import email
import email.header
import imaplib
import structlog
import time
from app.models.schemas import SearchResult
from app.providers.base import SearchProvider

log = structlog.get_logger()


def _decode_header(value: str) -> str:
    parts = email.header.decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


class GmailIMAPProvider(SearchProvider):
    name = "gmail"

    def __init__(
        self,
        address: str,
        app_password: str,
        casting_senders: list[str],
        imap_host: str = "imap.gmail.com",
        imap_port: int = 993,
        cache_ttl_seconds: float = 300.0,
    ) -> None:
        self._address = address
        self._app_password = app_password
        self._casting_senders = casting_senders
        self._imap_host = imap_host
        self._imap_port = imap_port
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache_ts: float | None = None

    def _is_cache_valid(self) -> bool:
        return self._cache_ts is not None and (time.monotonic() - self._cache_ts) < self._cache_ttl_seconds

    async def search(self, query: str, options: dict[str, object]) -> list[SearchResult]:
        if self._is_cache_valid():
            return []
        try:
            results = await asyncio.get_event_loop().run_in_executor(None, self._fetch_emails)
            self._cache_ts = time.monotonic()
            return results
        except Exception as exc:
            log.error("gmail.fetch_failed", error=str(exc))
            return []

    def _fetch_emails(self) -> list[SearchResult]:
        results: list[SearchResult] = []
        with imaplib.IMAP4_SSL(self._imap_host, self._imap_port) as conn:
            conn.login(self._address, self._app_password)
            conn.select("INBOX")
            for sender in self._casting_senders:
                _, msg_ids_raw = conn.search(None, f'(FROM "{sender}" UNSEEN)')
                msg_ids = msg_ids_raw[0].split() if msg_ids_raw and msg_ids_raw[0] else []
                for msg_id in msg_ids:
                    result = self._fetch_single(conn, msg_id)
                    if result:
                        results.append(result)
        return results

    def _fetch_single(self, conn: imaplib.IMAP4_SSL, msg_id: bytes) -> SearchResult | None:
        _, msg_data = conn.fetch(msg_id, "(RFC822)")
        if not msg_data or not msg_data[0]:
            return None
        raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
        if not isinstance(raw, bytes):
            return None
        msg = email.message_from_bytes(raw)
        subject = _decode_header(msg.get("Subject", ""))
        body = self._extract_body(msg)
        return SearchResult(
            title=subject,
            url="",
            snippet=body[:500],
            content=body,
            source=self.name,
        )

    def _extract_body(self, msg: email.message.Message) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        return payload.decode("utf-8", errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if isinstance(payload, bytes):
                return payload.decode("utf-8", errors="replace")
        return ""
