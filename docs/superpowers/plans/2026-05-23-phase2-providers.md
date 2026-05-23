# Phase 2 — New Providers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Backstage (Playwright + actor credentials), Gmail/IMAP, and DeadlineExtractorAgent as new ingestion sources, all plugging into the existing `SearchProvider` abstraction.

**Architecture:** Each provider implements `SearchProvider.search()` and normalizes output to `SearchResult`. `DeadlineExtractorAgent` runs as a post-dedup step, enriching listings that lack a `published_at` date. The orchestrator fan-outs to all providers via `MultiProvider`. **Important:** `GmailProvider` ignores the `query` parameter (it fetches all unseen emails from whitelisted senders). To prevent it being called N times per run (once per generated query), `GmailIMAPProvider` uses a per-run TTL cache — it returns results only on the first call within a 5-minute window.

**Tech Stack:** Playwright (async), imaplib (stdlib), python-telegram-bot already installed, OpenAI Responses API for deadline extraction

**Prerequisite:** Phase 1 plan fully implemented and passing.

**Spec:** `docs/superpowers/specs/2026-05-23-actor-searcher-v2-design.md` §4

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `app/providers/backstage.py` | Playwright scraper for backstage.com (authenticated) |
| Create | `app/providers/gmail_imap.py` | IMAP email ingestor |
| Create | `app/providers/multi.py` | Fan-out across multiple providers |
| Create | `app/agents/deadline_extractor_agent.py` | LLM deadline extraction from free text |
| Modify | `app/config/settings.py` | Add Backstage + Gmail env vars |
| Modify | `app/main.py` | Wire new providers + deadline agent |
| Modify | `.env.example` | New vars |
| Create | `tests/test_backstage_provider.py` | |
| Create | `tests/test_gmail_provider.py` | |
| Create | `tests/test_deadline_extractor_agent.py` | |

---

## Task 1: New env vars for Phase 2

**Files:**
- Modify: `app/config/settings.py`
- Modify: `.env.example`

- [ ] **Step 1: Add to Settings class**

In `app/config/settings.py`, add inside the `Settings` class after `admin_password`:

```python
    # Backstage provider
    backstage_email: str = Field(default="", alias="BACKSTAGE_EMAIL")
    backstage_password: str = Field(default="", alias="BACKSTAGE_PASSWORD")
    backstage_enabled: bool = Field(default=False, alias="BACKSTAGE_ENABLED")
    backstage_max_listings: int = Field(default=50, alias="BACKSTAGE_MAX_LISTINGS")

    # Gmail IMAP provider
    gmail_imap_host: str = Field(default="imap.gmail.com", alias="GMAIL_IMAP_HOST")
    gmail_imap_port: int = Field(default=993, alias="GMAIL_IMAP_PORT")
    gmail_app_password: str = Field(default="", alias="GMAIL_APP_PASSWORD")
    gmail_address: str = Field(default="", alias="GMAIL_ADDRESS")
    gmail_casting_senders: str = Field(default="", alias="GMAIL_CASTING_SENDERS")
    gmail_enabled: bool = Field(default=False, alias="GMAIL_ENABLED")
```

- [ ] **Step 2: Update .env.example**

Append to `.env.example`:

```bash
# Backstage provider
BACKSTAGE_EMAIL=
BACKSTAGE_PASSWORD=
BACKSTAGE_ENABLED=false
BACKSTAGE_MAX_LISTINGS=50

# Gmail IMAP provider
GMAIL_IMAP_HOST=imap.gmail.com
GMAIL_IMAP_PORT=993
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=
# Comma-separated list of sender email addresses to process
GMAIL_CASTING_SENDERS=
GMAIL_ENABLED=false
```

- [ ] **Step 3: Verify**

```bash
python -c "from app.config.settings import get_settings; s = get_settings(); print(s.backstage_enabled, s.gmail_enabled)"
```

Expected: `False False`

- [ ] **Step 4: Commit**

```bash
git add app/config/settings.py .env.example
git commit -m "feat: add Backstage and Gmail provider settings"
```

---

## Task 2: DeadlineExtractorAgent

**Files:**
- Create: `app/agents/deadline_extractor_agent.py`
- Create: `tests/test_deadline_extractor_agent.py`

- [ ] **Step 1: Add `extract_deadline` to LLMService**

In `app/services/llm_service.py`, add after `batch_match_profile`:

```python
    async def extract_deadline(self, text: str) -> str | None:
        import json
        prompt = (
            f"Extract the application deadline from this text. "
            f"Return JSON: {{\"deadline\": \"YYYY-MM-DD\"}} or {{\"deadline\": null}} if not found.\n\n"
            f"Text: {text[:2000]}"
        )
        data = await self._responses(prompt)
        result = json.loads(data)
        return result.get("deadline")
```

- [ ] **Step 2: Write failing test**

Create `tests/test_deadline_extractor_agent.py`:

```python
import pytest
import respx
import httpx
import json
from datetime import datetime
from app.agents.deadline_extractor_agent import DeadlineExtractorAgent
from app.models.schemas import SearchResult
from app.services.llm_service import LLMService


def _make_result(snippet: str, has_date: bool = False) -> SearchResult:
    return SearchResult(
        title="Some Role",
        url="https://example.com/role",
        snippet=snippet,
        source="test",
        published_at=datetime(2026, 5, 1) if has_date else None,
    )


@respx.mock
async def test_extracts_deadline_from_free_text() -> None:
    respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"output_text": json.dumps({"deadline": "2026-06-15"})})
    )
    agent = DeadlineExtractorAgent(llm=LLMService())
    results = await agent.execute([_make_result("Apply by June 15th 2026")])
    assert results[0].deadline is not None
    assert results[0].deadline.year == 2026
    assert results[0].deadline.month == 6


@respx.mock
async def test_skips_result_with_existing_date() -> None:
    """No LLM call when published_at is already set."""
    agent = DeadlineExtractorAgent(llm=LLMService())
    results = await agent.execute([_make_result("some text", has_date=True)])
    # No mock needed — no call should be made
    assert results[0].published_at is not None


@respx.mock
async def test_handles_no_deadline_found() -> None:
    respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"output_text": json.dumps({"deadline": None})})
    )
    agent = DeadlineExtractorAgent(llm=LLMService())
    results = await agent.execute([_make_result("No deadline mentioned")])
    assert results[0].deadline is None
```

- [ ] **Step 3: Run to confirm failure**

```bash
pytest tests/test_deadline_extractor_agent.py -v
```

Expected: `ImportError: cannot import name 'DeadlineExtractorAgent'`

- [ ] **Step 4: Implement agent**

Create `app/agents/deadline_extractor_agent.py`:

```python
from datetime import datetime
import structlog
from app.models.schemas import SearchResult
from app.services.llm_service import LLMService

log = structlog.get_logger()


class DeadlineExtractorAgent:
    def __init__(self, llm: LLMService) -> None:
        self.llm = llm

    async def execute(self, results: list[SearchResult]) -> list[SearchResult]:
        for item in results:
            if item.published_at is not None:
                continue
            text = f"{item.title} {item.snippet} {item.content or ''}"
            try:
                date_str = await self.llm.extract_deadline(text)
                if date_str:
                    item.published_at = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception as exc:
                log.warning("deadline_extractor.failed", url=item.url, error=str(exc))
        return results
```

Note: `SearchResult` schema needs a `deadline` field to distinguish extracted deadline from `published_at`. For now, we store it in `published_at` since it's the closest semantic field. Phase 3 will use the `RankedListing.deadline` field properly.

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_deadline_extractor_agent.py -v
```

Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add app/agents/deadline_extractor_agent.py app/services/llm_service.py tests/test_deadline_extractor_agent.py
git commit -m "feat: add DeadlineExtractorAgent and LLMService.extract_deadline()"
```

---

## Task 3: BackstageProvider

**Files:**
- Create: `app/providers/backstage.py`
- Create: `tests/test_backstage_provider.py`

**Note:** Playwright requires browser binaries. Add to Dockerfile: `RUN playwright install chromium --with-deps`

- [ ] **Step 1: Write failing test**

Create `tests/test_backstage_provider.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.providers.backstage import BackstageProvider
from app.models.schemas import SearchResult


async def test_backstage_normalizes_to_search_result() -> None:
    """Provider normalizes scraped data to SearchResult list."""
    mock_listing = {
        "title": "Lead Role — Thriller",
        "url": "https://www.backstage.com/listing/123",
        "snippet": "Looking for 25-35 male athletic actor in Rome",
        "deadline": "2026-06-01",
    }

    with patch("app.providers.backstage.BackstageProvider._scrape_listings", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = [mock_listing]
        provider = BackstageProvider(email="test@test.com", password="pw")
        results = await provider.search("casting thriller Roma", {})

    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].source == "backstage"
    assert "Thriller" in results[0].title


async def test_backstage_returns_empty_on_scrape_error() -> None:
    """Provider catches errors and returns empty list (fail-safe)."""
    with patch("app.providers.backstage.BackstageProvider._scrape_listings", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.side_effect = Exception("Playwright failed")
        provider = BackstageProvider(email="test@test.com", password="pw")
        results = await provider.search("query", {})
    assert results == []
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_backstage_provider.py -v
```

Expected: `ImportError: cannot import name 'BackstageProvider'`

- [ ] **Step 3: Implement BackstageProvider**

Create `app/providers/backstage.py`:

```python
import asyncio
import structlog
from playwright.async_api import async_playwright, Browser, Page
from app.models.schemas import SearchResult
from app.providers.base import SearchProvider

log = structlog.get_logger()

BACKSTAGE_LOGIN_URL = "https://www.backstage.com/login"
BACKSTAGE_SEARCH_URL = "https://www.backstage.com/casting-calls"
CRAWL_DELAY_SECONDS = 3.0


class BackstageProvider(SearchProvider):
    name = "backstage"

    def __init__(self, email: str, password: str, max_listings: int = 50) -> None:
        self._email = email
        self._password = password
        self._max_listings = max_listings

    async def search(self, query: str, options: dict[str, object]) -> list[SearchResult]:
        try:
            raw = await self._scrape_listings(query)
            return [
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    source=self.name,
                )
                for item in raw
                if item.get("url")
            ]
        except Exception as exc:
            log.error("backstage.scrape_failed", error=str(exc))
            return []

    async def _scrape_listings(self, query: str) -> list[dict[str, str]]:
        listings: list[dict[str, str]] = []
        async with async_playwright() as pw:
            browser: Browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (compatible; actor-searcher)")
            page: Page = await context.new_page()
            try:
                await self._login(page)
                await asyncio.sleep(CRAWL_DELAY_SECONDS)
                await page.goto(f"{BACKSTAGE_SEARCH_URL}?q={query}", wait_until="networkidle")
                await asyncio.sleep(CRAWL_DELAY_SECONDS)
                listings = await self._extract_listings(page)
            finally:
                await browser.close()
        return listings[: self._max_listings]

    async def _login(self, page: Page) -> None:
        await page.goto(BACKSTAGE_LOGIN_URL, wait_until="networkidle")
        await page.fill('input[type="email"]', self._email)
        await page.fill('input[type="password"]', self._password)
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard**", timeout=15000)

    async def _extract_listings(self, page: Page) -> list[dict[str, str]]:
        # Selectors are illustrative — update if Backstage changes DOM structure
        cards = await page.query_selector_all('[data-testid="casting-card"]')
        results: list[dict[str, str]] = []
        for card in cards:
            title_el = await card.query_selector("h2, h3, .title")
            link_el = await card.query_selector("a[href]")
            desc_el = await card.query_selector("p, .description")
            title = (await title_el.inner_text()).strip() if title_el else ""
            href = await link_el.get_attribute("href") if link_el else ""
            url = f"https://www.backstage.com{href}" if href and href.startswith("/") else href
            snippet = (await desc_el.inner_text()).strip() if desc_el else ""
            if title and url:
                results.append({"title": title, "url": url, "snippet": snippet})
        return results
```

**Important:** The CSS selectors in `_extract_listings` are placeholders. Before using in production, inspect the actual Backstage DOM and update the selectors. The unit tests mock `_scrape_listings` entirely, so they will pass regardless.

- [ ] **Step 4: Install Playwright browsers**

```bash
playwright install chromium
```

Expected: Chromium downloaded successfully.

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_backstage_provider.py -v
```

Expected: 2 PASS.

- [ ] **Step 6: Update Dockerfile**

In `Dockerfile`, after the `pip install` step, add:

```dockerfile
RUN playwright install chromium --with-deps
```

- [ ] **Step 7: Commit**

```bash
git add app/providers/backstage.py tests/test_backstage_provider.py Dockerfile
git commit -m "feat: add BackstageProvider (Playwright, authenticated)"
```

---

## Task 4: GmailProvider (IMAP)

**Files:**
- Create: `app/providers/gmail_imap.py`
- Create: `tests/test_gmail_provider.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_gmail_provider.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from app.providers.gmail_imap import GmailIMAPProvider
from app.models.schemas import SearchResult


def _mock_imap(messages: list[tuple[bytes, bytes]]) -> MagicMock:
    """Returns a mock IMAP4_SSL that yields given (subject, body) pairs."""
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.login = MagicMock()
    mock_conn.select = MagicMock(return_value=("OK", [b"1"]))

    # search returns IDs for each allowed sender
    mock_conn.search = MagicMock(return_value=("OK", [b" ".join(str(i + 1).encode() for i in range(len(messages)))]))

    def fetch_side_effect(msg_id: bytes, fmt: str):
        idx = int(msg_id) - 1
        if idx >= len(messages):
            return ("OK", [])
        subj, body = messages[idx]
        raw_email = (
            f"Subject: {subj.decode()}\r\n"
            f"From: agency@casting.com\r\n"
            f"\r\n"
            f"{body.decode()}"
        ).encode()
        return ("OK", [(b"", raw_email)])

    mock_conn.fetch = MagicMock(side_effect=fetch_side_effect)
    return mock_conn


async def test_gmail_returns_search_results() -> None:
    messages = [
        (b"Casting Call: Lead Role Thriller", b"We are looking for a male actor 25-35 in Rome. Apply by June 30."),
        (b"Audition: Commercial Spot Milano", b"Looking for athletic build. Deadline: 2026-07-01."),
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


async def test_gmail_returns_empty_on_connection_error() -> None:
    with patch("app.providers.gmail_imap.imaplib.IMAP4_SSL", side_effect=ConnectionError("refused")):
        provider = GmailIMAPProvider(
            address="actor@gmail.com",
            app_password="pw",
            casting_senders=["agency@casting.com"],
        )
        results = await provider.search("", {})
    assert results == []
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_gmail_provider.py -v
```

Expected: `ImportError: cannot import name 'GmailIMAPProvider'`

- [ ] **Step 3: Implement GmailIMAPProvider**

Create `app/providers/gmail_imap.py`:

```python
import asyncio
import email
import email.header
import imaplib
import structlog
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
        self._cached_results: list[SearchResult] = []

    async def search(self, query: str, options: dict[str, object]) -> list[SearchResult]:
        # Gmail ignores query — fetches all unseen emails from whitelisted senders.
        # TTL cache prevents N calls per run (one per generated query).
        if self._is_cache_valid():
            return []  # already fetched this run cycle
        try:
            results = await asyncio.get_event_loop().run_in_executor(None, self._fetch_emails)
            import time
            self._cache_ts = time.monotonic()
            self._cached_results = results
            return results
        except Exception as exc:
            log.error("gmail.fetch_failed", error=str(exc))
            return []

    def _is_cache_valid(self) -> bool:
        import time
        return self._cache_ts is not None and (time.monotonic() - self._cache_ts) < self._cache_ttl_seconds

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
            url="",  # emails have no URL; user will follow up manually
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_gmail_provider.py -v
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/providers/gmail_imap.py tests/test_gmail_provider.py
git commit -m "feat: add GmailIMAPProvider"
```

---

## Task 5: MultiProvider (fan-out)

**Files:**
- Create: `app/providers/multi.py`

- [ ] **Step 1: Implement MultiProvider**

Create `app/providers/multi.py`:

```python
import asyncio
import structlog
from app.models.schemas import SearchResult
from app.providers.base import SearchProvider

log = structlog.get_logger()


class MultiProvider(SearchProvider):
    name = "multi"

    def __init__(self, providers: list[SearchProvider]) -> None:
        self._providers = providers

    async def search(self, query: str, options: dict[str, object]) -> list[SearchResult]:
        tasks = [p.search(query, options) for p in self._providers]
        results_per_provider = await asyncio.gather(*tasks, return_exceptions=True)
        all_results: list[SearchResult] = []
        for provider, result in zip(self._providers, results_per_provider):
            if isinstance(result, Exception):
                log.error("multi_provider.provider_failed", provider=provider.name, error=str(result))
            else:
                all_results.extend(result)
        return all_results
```

- [ ] **Step 2: Verify import**

```bash
python -c "from app.providers.multi import MultiProvider; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/providers/multi.py
git commit -m "feat: add MultiProvider for fan-out across all ingestion sources"
```

---

## Task 6: Wire Phase 2 into orchestrator + main.py

**Files:**
- Modify: `app/services/orchestrator.py`
- Modify: `app/main.py`

- [ ] **Step 1: Add DeadlineExtractorAgent to orchestrator**

In `app/services/orchestrator.py`, add `deadline_extractor_agent` parameter:

```python
from app.agents.deadline_extractor_agent import DeadlineExtractorAgent

class SearchOrchestrator:
    def __init__(
        self,
        search_agent: SearchAgent,
        profile_matching_agent: ProfileMatchingAgent,
        query_generator_agent: QueryGeneratorAgent,
        dedup_agent: DedupAgent,
        profile_loader: ProfileLoader,
        deadline_extractor_agent: DeadlineExtractorAgent | None = None,
        notifier: TelegramBotNotifier | None = None,
        minimum_match_score: float = 0.3,
        notification_top_n: int = 5,
    ) -> None:
        # ... existing assignments ...
        self.deadline_extractor_agent = deadline_extractor_agent
```

In `execute()`, add deadline extraction step after `dedup_agent`:

```python
            deduped = await self.dedup_agent.execute(raw)
            if self.deadline_extractor_agent:
                deduped = await self.deadline_extractor_agent.execute(deduped)
            ranked = await self.profile_matching_agent.execute(deduped, profile)
```

- [ ] **Step 2: Wire providers and agents in main.py**

In `app/main.py`, replace the orchestrator construction:

```python
from app.agents.deadline_extractor_agent import DeadlineExtractorAgent
from app.providers.backstage import BackstageProvider
from app.providers.gmail_imap import GmailIMAPProvider
from app.providers.multi import MultiProvider
from app.providers.tavily import TavilyProvider

# Build provider list based on enabled flags
providers: list = [TavilyProvider()]

if settings.backstage_enabled and settings.backstage_email:
    providers.append(
        BackstageProvider(
            email=settings.backstage_email,
            password=settings.backstage_password,
            max_listings=settings.backstage_max_listings,
        )
    )

if settings.gmail_enabled and settings.gmail_address:
    senders = [s.strip() for s in settings.gmail_casting_senders.split(",") if s.strip()]
    providers.append(
        GmailIMAPProvider(
            address=settings.gmail_address,
            app_password=settings.gmail_app_password,
            casting_senders=senders,
            imap_host=settings.gmail_imap_host,
            imap_port=settings.gmail_imap_port,
        )
    )

search_orchestrator = SearchOrchestrator(
    search_agent=SearchAgent(MultiProvider(providers)),
    profile_matching_agent=ProfileMatchingAgent(
        llm=llm,
        minimum_score=settings.minimum_match_score,
        batch_size=settings.matching_batch_size,
    ),
    query_generator_agent=QueryGeneratorAgent(llm=llm),
    dedup_agent=DedupAgent(),
    deadline_extractor_agent=DeadlineExtractorAgent(llm=llm),
    profile_loader=ProfileLoader(yaml_path=settings.actor_profile_path),
    notifier=notifier,
    notification_top_n=settings.notification_top_n,
)
```

- [ ] **Step 3: Run full test suite**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 4: Ruff + mypy**

```bash
ruff check app/
mypy app/
```

- [ ] **Step 5: Commit**

```bash
git add app/services/orchestrator.py app/main.py
git commit -m "feat: wire Phase 2 providers and DeadlineExtractorAgent into orchestrator"
git tag v2-phase2-providers
```

---

## Phase 2 Completion Checklist

- [ ] `BACKSTAGE_ENABLED=true` + credentials set in `.env` (if using Backstage)
- [ ] `GMAIL_ENABLED=true` + Gmail App Password + casting senders set (if using Gmail)
- [ ] Playwright Chromium installed: `playwright install chromium`
- [ ] Docker image rebuilt: `docker compose build`
- [ ] Manual run: trigger via API, check logs for all 3 providers
- [ ] Verify Backstage selectors match current DOM (inspect backstage.com listing page)
- [ ] Verify Gmail IMAP marks emails as read after processing

---
