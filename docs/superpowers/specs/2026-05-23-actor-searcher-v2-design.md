# actor-searcher v2 — Design Spec

**Date:** 2026-05-23  
**Status:** Draft — awaiting implementation plan  
**Scope:** Full redesign from generic web intelligence tool to AI casting agent for a single actor

---

## 1. Problem Statement

The existing codebase is a solid generic web intelligence pipeline (search → rank → summarize → dedup → notify). It lacks:
- An actor profile model (ranking is keyword-based, not profile-aware)
- Domain-specific casting sources (Backstage, Gmail)
- A real HITL feedback loop
- Profile adaptation over time

The goal is to transform it into a system that operates like a full casting office for a single actor: continuously monitoring all relevant sources, semantically matching listings against the actor's profile, and notifying via Telegram with actionable inline buttons.

---

## 2. Constraints

- Single actor (not multi-tenant)
- Zero new infrastructure dependencies beyond what exists (Postgres, Redis, Docker, OpenAI)
- Qdrant deferred — not needed at current volume (10–50 listings/run)
- Respect robots.txt; Backstage scraping with actor's own credentials flagged as ToS-risk
- Prefer open-source / zero-cost solutions for local deployment
- Python 3.12, async-first, strict typing (existing standards from AGENTS.md)

---

## 3. Actor Profile

### 3.1 YAML Base (`actor_profile.yaml`, versioned in git)

Static traits that rarely change:

```yaml
name: ""
age: 0
gender: ""
languages: []           # e.g. ["Italian (native)", "English (C1)"]
physical:
  height_cm: 0
  build: ""             # slim / athletic / average / heavy
  hair_color: ""
  eye_color: ""
union_status: ""        # e.g. non-union / SAG-AFTRA / Equity
location: ""            # city
max_travel_km: 0
availability_from: ""   # ISO date
```

### 3.2 DB Delta (`actor_profile_delta` table)

Dynamic fields that evolve over time:

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `field_name` | str | e.g. "skill", "availability_from" |
| `field_value` | str | e.g. "musical", "2026-09-01" |
| `source` | str | "user_confirmed" / "system_suggested" |
| `created_at` | datetime | |
| `active` | bool | False = soft-deleted |

### 3.3 ProfileLoader

`ProfileLoader.load()` merges YAML base + active DB delta entries into a single `ActorProfile` Pydantic model at runtime. Skills from delta are appended to base skills. Availability and location from delta override YAML.

### 3.4 Role Preferences (`actor_role_preference` table)

Learned from feedback:

| Column | Type | Notes |
|---|---|---|
| `role_category` | str | e.g. "thriller", "commercial", "musical" |
| `approved_count` | int | |
| `rejected_count` | int | |
| `preference_score` | float | approved / (approved + rejected) |
| `updated_at` | datetime | |

Used by `ProfileMatchingAgent` as score multipliers.

---

## 4. Ingest Layer (Providers)

All providers implement `SearchProvider` (existing interface). Each normalizes output to `SearchResult`.

### 4.1 TavilyProvider (upgraded)

Query generation is now dynamic: `QueryGeneratorAgent` builds queries from the actor profile instead of static config strings.

Example: `"casting call thriller protagonista 25-35 anni Roma non-union"`

### 4.2 BackstageProvider (new, Playwright)

- Credentials: `BACKSTAGE_EMAIL`, `BACKSTAGE_PASSWORD` env vars
- Logs in, navigates to relevant listing pages filtered by actor category
- Rate limiting: min 3s between page loads, max 50 listings per run
- **ToS warning:** Backstage's ToS prohibits automated access. Use at your own risk. Implement polite crawl delays and stop if HTTP 429/403.
- Normalizes listing fields: title, description, deadline, pay, location → `SearchResult`

### 4.3 GmailProvider (new, IMAP)

- Connects via IMAP (`imap.gmail.com:993`) using App Password
- Configurable sender whitelist: `GMAIL_CASTING_SENDERS=agency1@...,agency2@...`
- Fetches unseen emails from whitelist senders
- Parses subject + body → extracts listing data via `DeadlineExtractorAgent`
- Normalizes to `SearchResult`, marks emails as read after processing
- **Alternative:** Gmail API (OAuth2) for users who cannot use IMAP App Passwords — implement as `GmailAPIProvider` with same interface

---

## 5. Agent Pipeline

### 5.1 Agent Overview

```
SearchAgent (fan-out to all providers)
    ↓
DedupAgent (URL + content hash — existing)
    ↓
DeadlineExtractorAgent (LLM: extract deadline from free text if missing)
    ↓
ProfileMatchingAgent (LLM batch: score + rationale + red_flags per listing)
    ↓
NotificationAgent (Telegram inline keyboard per top-N results)
```

### 5.2 QueryGeneratorAgent (new)

Input: `ActorProfile`  
Output: `list[str]` — N queries per provider

Generates queries using a prompt template with profile fields substituted. Uses few-shot examples to avoid overly generic queries. Cached per profile hash (invalidated when profile changes).

### 5.3 ProfileMatchingAgent (replaces RankingAgent)

Input: `list[SearchResult]`, `ActorProfile`  
Output: `list[RankedListing]`

Single LLM call with full profile in system context + all listings in user message (chunked if >20 listings to avoid context overflow). Returns for each listing:

```json
{
  "url": "",
  "match_score": 0.0,
  "rationale": "",
  "red_flags": [],
  "role_category": ""
}
```

`role_category` is used by `PreferenceLearner` when feedback arrives.

### 5.4 DeadlineExtractorAgent (new)

Input: `SearchResult.content`  
Output: `datetime | None`

Lightweight LLM call to extract deadlines from unstructured text ("entro fine maggio", "30/05", etc.). Only called if `SearchResult.published_at` is missing.

### 5.5 NotificationAgent (upgraded)

Sends top-N results (configurable, default 5) as individual Telegram messages with inline keyboard:

```
🎭 [RUOLO] {title}
📍 {location} | 💰 {pay} | ⏰ Scad: {deadline}
Score: {match_score:.2f} | Fonte: {source}

"{rationale}"
⚠️ Red flags: {red_flags}

[✅ Invia CV] [⭐ Salva] [❌ Ignora]
```

### 5.6 PreferenceLearner (new, cron job)

Runs weekly (or on-demand). Reads `actor_feedback` table, aggregates by `role_category`, updates `actor_role_preference` table. Generates `ProfileSuggestion` entries when:
- `preference_score > 0.75` and skill not in profile → suggest adding skill
- `preference_score < 0.2` and category has >5 samples → suggest deprioritizing category

---

## 6. Telegram Bot (HITL)

Upgrade from passive notifier to bidirectional bot using `python-telegram-bot`.

### 6.1 Callback Handler (new endpoint)

`POST /telegram/webhook` receives callback queries from inline keyboard taps. Dispatches to:
- `handle_approve(listing_id)` → saves `actor_feedback(action="approved", ...)`
- `handle_save(listing_id)` → saves `actor_feedback(action="saved", ...)` + returns listing URL
- `handle_ignore(listing_id)` → saves `actor_feedback(action="ignored", ...)`

All callbacks update the message to show the selected action (no dangling keyboards).

### 6.2 Bot Commands

| Command | Description |
|---|---|
| `/profile` | Shows current effective profile (YAML + delta merged) |
| `/stats` | Approval/rejection counts per role category |
| `/suggestions` | Lists pending `ProfileSuggestion` entries |
| `/run` | Triggers a manual pipeline run |

### 6.3 actor_feedback Table

| Column | Type |
|---|---|
| `id` | int PK |
| `listing_id` | int FK → search_results |
| `action` | str: approved / saved / ignored |
| `role_category` | str |
| `timestamp` | datetime |

---

## 7. Admin Dashboard

FastAPI + Jinja2 templates. Single-user, no JS framework.

### Routes

| Route | Function |
|---|---|
| `GET /admin/profile` | View + edit actor profile (YAML fields + delta skills) |
| `POST /admin/profile/delta` | Add/remove skill or update availability |
| `GET /admin/suggestions` | View `ProfileSuggestion` list |
| `POST /admin/suggestions/{id}/apply` | Apply suggestion → inserts into delta |
| `POST /admin/suggestions/{id}/dismiss` | Soft-delete suggestion |
| `GET /admin/stats` | Feedback statistics by category |
| `GET /admin/runs` | Run history (existing API data) |

**Auth:** HTTP Basic (`ADMIN_USERNAME`, `ADMIN_PASSWORD` env vars). Document that HTTPS is required if exposed beyond localhost.

---

## 8. Data Model Changes (Alembic migrations needed)

New tables:
- `actor_profile_delta`
- `actor_role_preference`
- `actor_feedback`
- `profile_suggestion`

Modified tables:
- `search_results` → add `role_category` (str, nullable), `deadline` (datetime, nullable), `rationale` (text, nullable), `red_flags` (jsonb, nullable)

---

## 9. Configuration Changes

New env vars:

```env
# Actor profile
ACTOR_PROFILE_PATH=./actor_profile.yaml

# Backstage
BACKSTAGE_EMAIL=
BACKSTAGE_PASSWORD=
BACKSTAGE_ENABLED=true

# Gmail
GMAIL_IMAP_HOST=imap.gmail.com
GMAIL_APP_PASSWORD=
GMAIL_CASTING_SENDERS=agency1@example.com,agency2@example.com
GMAIL_ENABLED=false

# Telegram bot (upgrade from notifier)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_WEBHOOK_URL=  # for webhook mode; leave empty for polling

# Admin dashboard
ADMIN_USERNAME=admin
ADMIN_PASSWORD=
```

---

## 10. Build Order (MVP → Full)

### Phase 1 — Core profile + matching (MVP)
1. `actor_profile.yaml` schema + `ProfileLoader`
2. Alembic migration: `actor_profile_delta`, `actor_role_preference`, `actor_feedback`
3. `ProfileMatchingAgent` (replaces `RankingAgent`)
4. `QueryGeneratorAgent`
5. Telegram inline keyboard + callback handler
6. `actor_feedback` persistence

### Phase 2 — New providers
7. `BackstageProvider` (Playwright)
8. `GmailProvider` (IMAP)
9. `DeadlineExtractorAgent`

### Phase 3 — Learning + Dashboard
10. `PreferenceLearner` (cron)
11. Admin dashboard (Jinja2 routes)
12. `ProfileSuggestion` flow

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Backstage ToS violation | Rate limit aggressively (3s delay, 50 listings/run max); document risk; easy to disable via env flag |
| LLM cost on batch matching | Chunk batches at 20 listings; compress profile to essential fields in prompt |
| Gmail IMAP deprecation | Implement `GmailAPIProvider` as alternative; both share same interface |
| QueryGenerator produces generic queries | Few-shot examples in prompt + profile-field substitution templates |
| Dashboard exposed on network without HTTPS | Document; add warning log on startup if `ADMIN_PASSWORD` is default |
| Profile drift from PreferenceLearner | Suggestions require explicit user confirmation — system never auto-modifies profile |

---

## 12. Out of Scope (this spec)

- Qdrant / vector embeddings (defer until volume > 500 listings/run)
- Multi-actor support
- Auto-submission of CV (legal and ToS complexity)
- RSS feeds (deprioritized by user)
- Mobile app / native UI
