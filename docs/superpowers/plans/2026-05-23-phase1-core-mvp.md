# Phase 1 — Core MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic keyword-ranking pipeline with an actor-profile-aware matching pipeline, add Telegram inline-keyboard HITL, and persist feedback — producing a fully working casting agent for a single actor.

**Architecture:** `ActorProfile` (YAML base + Postgres delta) is the central entity. `QueryGeneratorAgent` builds search queries from the profile. `ProfileMatchingAgent` batch-evaluates listings with the full profile in LLM context. `TelegramBotNotifier` sends inline-keyboard messages; callback handler persists HITL feedback.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Alembic, OpenAI Responses API (`/v1/responses`), python-telegram-bot v21+, PyYAML, APScheduler, pytest-asyncio, respx

**Spec:** `docs/superpowers/specs/2026-05-23-actor-searcher-v2-design.md`

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `actor_profile.yaml` | Base static profile (root of repo) |
| Create | `app/profile/__init__.py` | Package marker |
| Create | `app/profile/models.py` | `ActorProfile`, `PhysicalTraits` Pydantic models |
| Create | `app/profile/loader.py` | `ProfileLoader` — merges YAML + DB delta |
| Modify | `app/models/db.py` | Add `ActorProfileDelta`, `ActorRolePreference`, `ActorFeedback`, `ProfileSuggestion`; extend `SearchResult` |
| Create | `alembic/versions/0002_actor_profile_tables.py` | Migration for new tables + columns |
| Modify | `app/models/schemas.py` | Add `RankedListing` schema |
| Modify | `app/services/llm_service.py` | Add `batch_match_profile()`, `generate_queries()` |
| Create | `app/agents/query_generator_agent.py` | Generates queries from `ActorProfile` |
| Create | `app/agents/profile_matching_agent.py` | Batch-scores listings against profile |
| Create | `app/repositories/feedback_repository.py` | CRUD for `ActorFeedback`, `ActorProfileDelta` |
| Create | `app/notifications/telegram_bot.py` | `TelegramBotNotifier` with inline keyboard |
| Modify | `app/services/orchestrator.py` | Rewrite to use new agents |
| Modify | `app/scheduler/scheduler_service.py` | Load `ActorProfile` before each run |
| Modify | `app/config/settings.py` | New env vars |
| Modify | `app/main.py` | Wire new agents, start Telegram bot polling |
| Modify | `pyproject.toml` | Add `python-telegram-bot`, `pyyaml` |
| Modify | `.env.example` | New env vars |
| Create | `tests/test_profile_loader.py` | |
| Create | `tests/test_query_generator_agent.py` | |
| Create | `tests/test_profile_matching_agent.py` | |
| Create | `tests/test_feedback_repository.py` | |
| Create | `tests/test_telegram_bot_notifier.py` | |

---

## Task 1: New dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dependencies**

In `pyproject.toml`, replace the `dependencies` list:

```toml
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "sqlalchemy[asyncio]>=2.0.30",
  "asyncpg>=0.29.0",
  "alembic>=1.13.0",
  "redis>=5.0.0",
  "apscheduler>=3.10.4",
  "httpx>=0.27.0",
  "pydantic>=2.7.0",
  "pydantic-settings>=2.3.0",
  "structlog>=24.2.0",
  "tenacity>=8.3.0",
  "python-dotenv>=1.0.1",
  "python-telegram-bot>=21.0",
  "pyyaml>=6.0.2",
  "jinja2>=3.1.4",
]
```

In `[project.optional-dependencies]` dev section, add `"pytest-mock>=3.14"`:

```toml
[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
  "pytest-asyncio>=0.23.7",
  "respx>=0.21.1",
  "ruff>=0.5.0",
  "mypy>=1.10.0",
  "pytest-mock>=3.14",
]
```

- [ ] **Step 2: Install**

```bash
pip install -e .[dev]
```

Expected: successful install, no conflicts.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add python-telegram-bot, pyyaml, jinja2, pytest-mock deps"
```

---

## Task 2: Settings + env vars

**Files:**
- Modify: `app/config/settings.py`
- Modify: `.env.example`

- [ ] **Step 1: Extend Settings**

Replace `app/config/settings.py` content:

```python
from functools import lru_cache
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderSettings(BaseModel):
    timeout_seconds: float = 15.0
    max_retries: int = 3


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "actor-searcher"
    environment: str = "dev"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/actor_searcher"
    redis_url: str = "redis://redis:6379/0"

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4.1-mini"
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    brave_api_key: str = Field(default="", alias="BRAVE_API_KEY")

    # Actor profile
    actor_profile_path: str = Field(default="actor_profile.yaml", alias="ACTOR_PROFILE_PATH")

    # Telegram bot (HITL)
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    telegram_enabled: bool = Field(default=False, alias="TELEGRAM_ENABLED")

    # Pipeline
    notification_top_n: int = Field(default=5, alias="NOTIFICATION_TOP_N")
    matching_batch_size: int = Field(default=20, alias="MATCHING_BATCH_SIZE")
    minimum_match_score: float = Field(default=0.3, alias="MINIMUM_MATCH_SCORE")

    # Admin
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="", alias="ADMIN_PASSWORD")

    provider: ProviderSettings = ProviderSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: Update .env.example**

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/actor_searcher
REDIS_URL=redis://redis:6379/0

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini

TAVILY_API_KEY=
BRAVE_API_KEY=

ACTOR_PROFILE_PATH=./actor_profile.yaml

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_ENABLED=false

NOTIFICATION_TOP_N=5
MATCHING_BATCH_SIZE=20
MINIMUM_MATCH_SCORE=0.3

ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme
```

- [ ] **Step 3: Verify settings load**

```bash
python -c "from app.config.settings import get_settings; s = get_settings(); print(s.actor_profile_path)"
```

Expected output: `actor_profile.yaml`

- [ ] **Step 4: Commit**

```bash
git add app/config/settings.py .env.example
git commit -m "feat: add actor profile, telegram, and admin settings"
```

---

## Task 3: ActorProfile Pydantic model

**Files:**
- Create: `app/profile/__init__.py`
- Create: `app/profile/models.py`
- Create: `tests/test_profile_loader.py` (partial — test model validation)

- [ ] **Step 1: Write failing test**

Create `tests/test_profile_loader.py`:

```python
import pytest
from app.profile.models import ActorProfile, PhysicalTraits


def test_actor_profile_from_dict() -> None:
    data = {
        "name": "Mario Rossi",
        "age": 28,
        "gender": "male",
        "languages": ["Italian (native)", "English (C1)"],
        "physical": {
            "height_cm": 180,
            "build": "athletic",
            "hair_color": "brown",
            "eye_color": "green",
        },
        "skills": ["singing", "dancing"],
        "experience_level": "emerging",
        "union_status": "non-union",
        "location": "Roma",
        "max_travel_km": 200,
        "availability_from": "2026-06-01",
    }
    profile = ActorProfile.model_validate(data)
    assert profile.name == "Mario Rossi"
    assert profile.physical.height_cm == 180
    assert "singing" in profile.skills


def test_actor_profile_summary_contains_key_fields() -> None:
    data = {
        "name": "Maria Bianchi",
        "age": 32,
        "gender": "female",
        "languages": ["Italian (native)"],
        "physical": {"height_cm": 165, "build": "slim", "hair_color": "black", "eye_color": "brown"},
        "skills": ["voiceover", "theatre"],
        "experience_level": "mid",
        "union_status": "non-union",
        "location": "Milano",
        "max_travel_km": 100,
        "availability_from": "2026-07-01",
    }
    profile = ActorProfile.model_validate(data)
    summary = profile.to_summary()
    assert "32" in summary
    assert "voiceover" in summary
    assert "Milano" in summary
```

- [ ] **Step 2: Run test to confirm failure**

```bash
pytest tests/test_profile_loader.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.profile'`

- [ ] **Step 3: Create package and model**

Create `app/profile/__init__.py` (empty).

Create `app/profile/models.py`:

```python
from pydantic import BaseModel, Field


class PhysicalTraits(BaseModel):
    height_cm: int
    build: str
    hair_color: str
    eye_color: str


class ActorProfile(BaseModel):
    name: str
    age: int
    gender: str
    languages: list[str] = Field(default_factory=list)
    physical: PhysicalTraits
    skills: list[str] = Field(default_factory=list)
    experience_level: str
    union_status: str
    location: str
    max_travel_km: int = 100
    availability_from: str
    role_preferences: dict[str, float] = Field(default_factory=dict)

    def to_summary(self) -> str:
        skills_str = ", ".join(self.skills) if self.skills else "none listed"
        langs_str = ", ".join(self.languages)
        prefs = ""
        if self.role_preferences:
            top = sorted(self.role_preferences.items(), key=lambda x: x[1], reverse=True)[:5]
            prefs = f"\nRole preferences (learned): {', '.join(f'{k} ({v:+.1f})' for k, v in top)}"
        return (
            f"Name: {self.name}, Age: {self.age}, Gender: {self.gender}\n"
            f"Languages: {langs_str}\n"
            f"Physical: {self.physical.height_cm}cm, {self.physical.build} build, "
            f"{self.physical.hair_color} hair, {self.physical.eye_color} eyes\n"
            f"Skills: {skills_str}\n"
            f"Experience: {self.experience_level}, Union: {self.union_status}\n"
            f"Location: {self.location} (max {self.max_travel_km}km travel)\n"
            f"Available from: {self.availability_from}"
            f"{prefs}"
        )
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
pytest tests/test_profile_loader.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/profile/ tests/test_profile_loader.py
git commit -m "feat: add ActorProfile pydantic model with to_summary()"
```

---

## Task 4: actor_profile.yaml base file

**Files:**
- Create: `actor_profile.yaml` (root of repo)

- [ ] **Step 1: Create base profile**

Create `actor_profile.yaml` at the repository root:

```yaml
# Base actor profile — static traits. Edit directly and commit.
# Dynamic fields (skills added over time, availability updates) are stored in the DB delta.

name: ""
age: 0
gender: ""                        # male / female / non-binary
languages: []                     # e.g. ["Italian (native)", "English (C1)"]
physical:
  height_cm: 0
  build: ""                       # slim / athletic / average / heavy
  hair_color: ""
  eye_color: ""
skills: []                        # e.g. ["singing", "dancing", "horse riding"]
experience_level: "emerging"      # emerging / mid / established
union_status: "non-union"         # non-union / Equity / SAG-AFTRA
location: ""                      # city name
max_travel_km: 150
availability_from: ""             # ISO date: YYYY-MM-DD
```

- [ ] **Step 2: Fill in the actor's real details**

Edit `actor_profile.yaml` with the actual actor's information. This file is committed to git (no secrets here — it's profile data only).

- [ ] **Step 3: Commit**

```bash
git add actor_profile.yaml
git commit -m "feat: add actor_profile.yaml base template"
```

---

## Task 5: DB models — new tables

**Files:**
- Modify: `app/models/db.py`

- [ ] **Step 1: Add new SQLAlchemy models**

At the end of `app/models/db.py`, after the `Notification` class, add:

```python
class ActorProfileDelta(Base):
    __tablename__ = "actor_profile_delta"
    id: Mapped[int] = mapped_column(primary_key=True)
    field_name: Mapped[str] = mapped_column(String(64), index=True)
    field_value: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="user_confirmed")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ActorRolePreference(Base):
    __tablename__ = "actor_role_preference"
    id: Mapped[int] = mapped_column(primary_key=True)
    role_category: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    approved_count: Mapped[int] = mapped_column(default=0)
    rejected_count: Mapped[int] = mapped_column(default=0)
    preference_score: Mapped[float] = mapped_column(Float, default=0.5)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ActorFeedback(Base):
    __tablename__ = "actor_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("search_results.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(16), index=True)  # approved / saved / ignored
    role_category: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProfileSuggestion(Base):
    __tablename__ = "profile_suggestion"
    id: Mapped[int] = mapped_column(primary_key=True)
    suggestion_type: Mapped[str] = mapped_column(String(32))  # add_skill / deprioritize_category
    field_name: Mapped[str] = mapped_column(String(64))
    field_value: Mapped[str] = mapped_column(Text)
    reasoning: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending / applied / dismissed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Also extend `SearchResult` (add 4 new nullable columns after `content_hash`):

```python
    # --- new in v2 ---
    role_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    red_flags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from app.models.db import ActorFeedback, ActorProfileDelta, ActorRolePreference, ProfileSuggestion; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/models/db.py
git commit -m "feat: add actor profile, feedback, and suggestion DB models"
```

---

## Task 6: Alembic migration

**Files:**
- Create: `alembic/versions/0002_actor_profile_tables.py`

- [ ] **Step 1: Create migration**

Create `alembic/versions/0002_actor_profile_tables.py`:

```python
"""actor profile tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actor_profile_delta",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("field_name", sa.String(64), nullable=False, index=True),
        sa.Column("field_value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="user_confirmed"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "actor_role_preference",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_category", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("approved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("preference_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "actor_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("result_id", sa.Integer(), sa.ForeignKey("search_results.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.String(16), nullable=False, index=True),
        sa.Column("role_category", sa.String(64), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "profile_suggestion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("suggestion_type", sa.String(32), nullable=False),
        sa.Column("field_name", sa.String(64), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Extend search_results
    op.add_column("search_results", sa.Column("role_category", sa.String(64), nullable=True))
    op.add_column("search_results", sa.Column("deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column("search_results", sa.Column("rationale", sa.Text(), nullable=True))
    op.add_column("search_results", sa.Column("red_flags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("search_results", "red_flags")
    op.drop_column("search_results", "rationale")
    op.drop_column("search_results", "deadline")
    op.drop_column("search_results", "role_category")
    op.drop_table("profile_suggestion")
    op.drop_table("actor_feedback")
    op.drop_table("actor_role_preference")
    op.drop_table("actor_profile_delta")
```

- [ ] **Step 2: Run migration (requires DB running)**

```bash
docker compose up -d postgres
alembic upgrade head
```

Expected: `Running upgrade 0001 -> 0002, actor profile tables`

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/0002_actor_profile_tables.py
git commit -m "feat: alembic migration 0002 — actor profile and feedback tables"
```

---

## Task 7: ProfileLoader

**Files:**
- Create: `app/profile/loader.py`
- Extend: `tests/test_profile_loader.py`

- [ ] **Step 1: Add ProfileLoader tests**

Add to `tests/test_profile_loader.py`:

```python
import yaml
from unittest.mock import AsyncMock, MagicMock
from app.profile.loader import ProfileLoader
from app.profile.models import ActorProfile


async def test_loader_reads_yaml(tmp_path) -> None:
    yaml_data = {
        "name": "Test Actor",
        "age": 25,
        "gender": "female",
        "languages": ["Italian (native)"],
        "physical": {"height_cm": 170, "build": "slim", "hair_color": "blonde", "eye_color": "blue"},
        "skills": ["acting"],
        "experience_level": "emerging",
        "union_status": "non-union",
        "location": "Roma",
        "max_travel_km": 100,
        "availability_from": "2026-06-01",
    }
    yaml_file = tmp_path / "actor_profile.yaml"
    yaml_file.write_text(yaml.dump(yaml_data))

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))

    loader = ProfileLoader(yaml_path=str(yaml_file))
    profile = await loader.load(mock_session)

    assert isinstance(profile, ActorProfile)
    assert profile.name == "Test Actor"
    assert profile.skills == ["acting"]


async def test_loader_merges_delta_skills(tmp_path) -> None:
    yaml_data = {
        "name": "Test Actor",
        "age": 25,
        "gender": "male",
        "languages": ["Italian (native)"],
        "physical": {"height_cm": 175, "build": "athletic", "hair_color": "brown", "eye_color": "green"},
        "skills": ["base_skill"],
        "experience_level": "mid",
        "union_status": "non-union",
        "location": "Milano",
        "max_travel_km": 50,
        "availability_from": "2026-07-01",
    }
    yaml_file = tmp_path / "actor_profile.yaml"
    yaml_file.write_text(yaml.dump(yaml_data))

    from app.models.db import ActorProfileDelta
    delta_row = MagicMock(spec=ActorProfileDelta)
    delta_row.field_name = "skill"
    delta_row.field_value = "canto lirico"

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[delta_row])))))

    loader = ProfileLoader(yaml_path=str(yaml_file))
    profile = await loader.load(mock_session)

    assert "base_skill" in profile.skills
    assert "canto lirico" in profile.skills
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_profile_loader.py -v
```

Expected: `ImportError: cannot import name 'ProfileLoader' from 'app.profile.loader'`

- [ ] **Step 3: Implement ProfileLoader**

Create `app/profile/loader.py`:

```python
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import ActorProfileDelta, ActorRolePreference
from app.profile.models import ActorProfile


class ProfileLoader:
    def __init__(self, yaml_path: str) -> None:
        self._yaml_path = yaml_path

    async def load(self, session: AsyncSession) -> ActorProfile:
        with open(self._yaml_path, encoding="utf-8") as f:
            base = yaml.safe_load(f)

        delta_rows = (
            await session.execute(
                select(ActorProfileDelta).where(ActorProfileDelta.active.is_(True))
            )
        ).scalars().all()

        pref_rows = (
            await session.execute(select(ActorRolePreference))
        ).scalars().all()

        skills: list[str] = list(base.get("skills", []))
        for row in delta_rows:
            if row.field_name == "skill" and row.field_value not in skills:
                skills.append(row.field_value)
            elif row.field_name == "availability_from":
                base["availability_from"] = row.field_value
            elif row.field_name == "location":
                base["location"] = row.field_value
            elif row.field_name == "max_travel_km":
                base["max_travel_km"] = int(row.field_value)

        base["skills"] = skills
        base["role_preferences"] = {r.role_category: r.preference_score for r in pref_rows}

        return ActorProfile.model_validate(base)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_profile_loader.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/profile/loader.py tests/test_profile_loader.py
git commit -m "feat: add ProfileLoader — merges YAML base with DB delta and preferences"
```

---

## Task 8: LLMService — new methods

**Files:**
- Modify: `app/services/llm_service.py`
- Create: (tested indirectly via agent tests)

- [ ] **Step 1: Add `generate_queries` and `batch_match_profile` to LLMService**

In `app/services/llm_service.py`, add these two methods to the `LLMService` class (after `summarize`):

```python
    async def generate_queries(self, profile_summary: str, num_queries: int = 10) -> list[str]:
        prompt = (
            f"You are a casting agent assistant. Generate {num_queries} specific web search queries "
            f"to find casting calls and auditions for this actor.\n\n"
            f"Actor Profile:\n{profile_summary}\n\n"
            f"Target job types: film, TV series, commercials, theatre, voiceover, gaming, YouTube productions.\n"
            f"Rules:\n"
            f"- Queries must target Italian productions primarily (but include international)\n"
            f"- Each query must be specific enough to return casting call results\n"
            f"- Include actor's age range, location, and relevant skills in different queries\n"
            f"- Vary by job type and platform (use 'site:backstage.com', 'casting call', 'audizioni', etc.)\n"
            f"- Return ONLY a JSON array of strings, no other text\n\n"
            f'Example: ["casting call thriller Roma 25-30 anni non-union", "audizioni spot pubblicitario Milano maschio atletico"]'
        )
        data = await self._responses(prompt)
        import json
        result = json.loads(data)
        if isinstance(result, list):
            return [str(q) for q in result[:num_queries]]
        return []

    async def batch_match_profile(
        self,
        listings: list[dict[str, str]],
        profile_summary: str,
    ) -> list[dict[str, object]]:
        import json
        listings_json = json.dumps(listings, ensure_ascii=False, indent=2)
        prompt = (
            f"You are a senior casting agent. Evaluate each job listing against this actor's profile.\n\n"
            f"ACTOR PROFILE:\n{profile_summary}\n\n"
            f"JOB LISTINGS (JSON array):\n{listings_json}\n\n"
            f"For EACH listing return a JSON object with these exact fields:\n"
            f"- url: same url as input\n"
            f"- match_score: float 0.0-1.0 (0=complete mismatch, 1=perfect fit)\n"
            f"- rationale: 2-3 sentences plain language explaining the score\n"
            f"- red_flags: list of strings (requirements actor may not meet; empty list if none)\n"
            f"- role_category: one word genre/type (thriller/commercial/musical/voiceover/gaming/theatre/other)\n\n"
            f"Return ONLY a JSON array with one object per listing, no other text.\n"
            f"If a listing is clearly irrelevant (not a casting call), set match_score to 0.0."
        )
        data = await self._responses(prompt)
        result = json.loads(data)
        if isinstance(result, list):
            return result  # type: ignore[return-value]
        return []
```

- [ ] **Step 2: Verify import**

```bash
python -c "from app.services.llm_service import LLMService; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/services/llm_service.py
git commit -m "feat: add generate_queries and batch_match_profile to LLMService"
```

---

## Task 9: QueryGeneratorAgent

**Files:**
- Create: `app/agents/query_generator_agent.py`
- Create: `tests/test_query_generator_agent.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_query_generator_agent.py`:

```python
import pytest
import respx
import httpx
import json
from app.agents.query_generator_agent import QueryGeneratorAgent
from app.profile.models import ActorProfile, PhysicalTraits
from app.services.llm_service import LLMService


def _make_profile() -> ActorProfile:
    return ActorProfile(
        name="Test",
        age=28,
        gender="male",
        languages=["Italian (native)"],
        physical=PhysicalTraits(height_cm=180, build="athletic", hair_color="brown", eye_color="green"),
        skills=["singing"],
        experience_level="emerging",
        union_status="non-union",
        location="Roma",
        max_travel_km=200,
        availability_from="2026-06-01",
    )


@respx.mock
async def test_query_generator_returns_list() -> None:
    queries = ["casting call thriller Roma", "audizioni spot pubblicitario"]
    respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"output_text": json.dumps(queries)})
    )
    agent = QueryGeneratorAgent(llm=LLMService(), num_queries=2)
    result = await agent.execute(_make_profile())
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(q, str) for q in result)


@respx.mock
async def test_query_generator_uses_profile_location() -> None:
    """LLM is called once with profile summary in prompt."""
    queries = ["casting call Roma"]
    captured: list[dict] = []

    def capture(request: httpx.Request, *_: object) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"output_text": json.dumps(queries)})

    respx.post("https://api.openai.com/v1/responses").mock(side_effect=capture)
    agent = QueryGeneratorAgent(llm=LLMService(), num_queries=1)
    await agent.execute(_make_profile())
    assert len(captured) == 1
    assert "Roma" in captured[0]["input"]
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_query_generator_agent.py -v
```

Expected: `ImportError: cannot import name 'QueryGeneratorAgent'`

- [ ] **Step 3: Implement agent**

Create `app/agents/query_generator_agent.py`:

```python
from app.profile.models import ActorProfile
from app.services.llm_service import LLMService


class QueryGeneratorAgent:
    def __init__(self, llm: LLMService, num_queries: int = 10) -> None:
        self.llm = llm
        self.num_queries = num_queries

    async def execute(self, profile: ActorProfile) -> list[str]:
        return await self.llm.generate_queries(profile.to_summary(), self.num_queries)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_query_generator_agent.py -v
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/query_generator_agent.py tests/test_query_generator_agent.py
git commit -m "feat: add QueryGeneratorAgent"
```

---

## Task 10: RankedListing schema + ProfileMatchingAgent

**Files:**
- Modify: `app/models/schemas.py`
- Create: `app/agents/profile_matching_agent.py`
- Create: `tests/test_profile_matching_agent.py`

- [ ] **Step 1: Add RankedListing to schemas**

In `app/models/schemas.py`, add after the `SearchResult` class:

```python
class RankedListing(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    published_at: datetime | None = None
    deadline: datetime | None = None
    content_hash: str | None = None
    match_score: float = 0.0
    rationale: str = ""
    red_flags: list[str] = Field(default_factory=list)
    role_category: str = "other"
```

Also add `from datetime import datetime` at the top if not already present.

- [ ] **Step 2: Write failing test**

Create `tests/test_profile_matching_agent.py`:

```python
import pytest
import respx
import httpx
import json
from app.agents.profile_matching_agent import ProfileMatchingAgent
from app.models.schemas import RankedListing, SearchResult
from app.profile.models import ActorProfile, PhysicalTraits
from app.services.llm_service import LLMService


def _make_profile() -> ActorProfile:
    return ActorProfile(
        name="Test",
        age=28,
        gender="male",
        languages=["Italian (native)"],
        physical=PhysicalTraits(height_cm=180, build="athletic", hair_color="brown", eye_color="green"),
        skills=["singing"],
        experience_level="emerging",
        union_status="non-union",
        location="Roma",
        max_travel_km=200,
        availability_from="2026-06-01",
    )


def _make_results(n: int = 3) -> list[SearchResult]:
    return [
        SearchResult(
            title=f"Role {i}",
            url=f"https://example.com/{i}",
            snippet=f"Casting call snippet {i}",
            source="tavily",
        )
        for i in range(n)
    ]


@respx.mock
async def test_profile_matching_returns_ranked_listings() -> None:
    llm_response = [
        {"url": "https://example.com/0", "match_score": 0.9, "rationale": "Great fit.", "red_flags": [], "role_category": "thriller"},
        {"url": "https://example.com/1", "match_score": 0.5, "rationale": "Partial fit.", "red_flags": ["requires driving license"], "role_category": "commercial"},
        {"url": "https://example.com/2", "match_score": 0.2, "rationale": "Poor fit.", "red_flags": ["wrong age range"], "role_category": "other"},
    ]
    respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"output_text": json.dumps(llm_response)})
    )
    agent = ProfileMatchingAgent(llm=LLMService(), minimum_score=0.3, batch_size=20)
    results = await agent.execute(_make_results(), _make_profile())
    assert len(results) == 2  # only score >= 0.3
    assert results[0].match_score == 0.9
    assert results[0].role_category == "thriller"
    assert isinstance(results[0], RankedListing)


@respx.mock
async def test_profile_matching_filters_below_minimum() -> None:
    llm_response = [
        {"url": "https://example.com/0", "match_score": 0.1, "rationale": "Bad fit.", "red_flags": [], "role_category": "other"},
    ]
    respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"output_text": json.dumps(llm_response)})
    )
    agent = ProfileMatchingAgent(llm=LLMService(), minimum_score=0.3, batch_size=20)
    results = await agent.execute(_make_results(1), _make_profile())
    assert results == []


@respx.mock
async def test_profile_matching_batches_large_input() -> None:
    """25 listings with batch_size=10 → 3 LLM calls."""
    call_count = [0]

    def handler(request: httpx.Request, *_: object) -> httpx.Response:
        body = json.loads(request.content)
        # parse how many listings were in this batch
        listings_in_batch = len(json.loads(body["input"].split("JOB LISTINGS")[1].split("For EACH")[0].strip().lstrip("(JSON array):\n")))
        call_count[0] += 1
        response = [
            {"url": f"https://x.com/{i}", "match_score": 0.8, "rationale": "ok", "red_flags": [], "role_category": "film"}
            for i in range(listings_in_batch)
        ]
        return httpx.Response(200, json={"output_text": json.dumps(response)})

    respx.post("https://api.openai.com/v1/responses").mock(side_effect=handler)
    agent = ProfileMatchingAgent(llm=LLMService(), minimum_score=0.0, batch_size=10)
    listings = [
        SearchResult(title=f"R{i}", url=f"https://x.com/{i}", snippet="s", source="t")
        for i in range(25)
    ]
    results = await agent.execute(listings, _make_profile())
    assert call_count[0] == 3
    assert len(results) == 25
```

- [ ] **Step 3: Run to confirm failure**

```bash
pytest tests/test_profile_matching_agent.py -v
```

Expected: `ImportError: cannot import name 'ProfileMatchingAgent'`

- [ ] **Step 4: Implement ProfileMatchingAgent**

Create `app/agents/profile_matching_agent.py`:

```python
from app.models.schemas import RankedListing, SearchResult
from app.profile.models import ActorProfile
from app.services.llm_service import LLMService


class ProfileMatchingAgent:
    def __init__(self, llm: LLMService, minimum_score: float = 0.3, batch_size: int = 20) -> None:
        self.llm = llm
        self.minimum_score = minimum_score
        self.batch_size = batch_size

    async def execute(self, results: list[SearchResult], profile: ActorProfile) -> list[RankedListing]:
        profile_summary = profile.to_summary()
        ranked: list[RankedListing] = []

        for i in range(0, len(results), self.batch_size):
            batch = results[i : i + self.batch_size]
            listings_input = [
                {"url": r.url, "title": r.title, "snippet": r.snippet, "content": r.content or ""}
                for r in batch
            ]
            match_results = await self.llm.batch_match_profile(listings_input, profile_summary)

            score_by_url = {m["url"]: m for m in match_results}
            for result in batch:
                match = score_by_url.get(result.url)
                if not match:
                    continue
                score = float(match.get("match_score", 0.0))
                if score < self.minimum_score:
                    continue
                ranked.append(
                    RankedListing(
                        title=result.title,
                        url=result.url,
                        snippet=result.snippet,
                        source=result.source,
                        published_at=result.published_at,
                        content_hash=None,
                        match_score=score,
                        rationale=str(match.get("rationale", "")),
                        red_flags=list(match.get("red_flags", [])),
                        role_category=str(match.get("role_category", "other")),
                    )
                )

        return sorted(ranked, key=lambda x: x.match_score, reverse=True)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_profile_matching_agent.py -v
```

Expected: first 2 tests PASS. Third test (batching) may need the prompt parsing adjusted — if it fails, simplify by just checking `call_count[0] == 3` without parsing the batch content.

- [ ] **Step 6: Commit**

```bash
git add app/models/schemas.py app/agents/profile_matching_agent.py tests/test_profile_matching_agent.py
git commit -m "feat: add ProfileMatchingAgent and RankedListing schema"
```

---

## Task 11: FeedbackRepository

**Files:**
- Create: `app/repositories/feedback_repository.py`
- Create: `tests/test_feedback_repository.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_feedback_repository.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, call
from app.repositories.feedback_repository import FeedbackRepository
from app.models.db import ActorFeedback


async def test_save_feedback_calls_session_add() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    repo = FeedbackRepository(session)
    await repo.save_feedback(result_id=42, action="approved", role_category="thriller")
    session.add.assert_called_once()
    added: ActorFeedback = session.add.call_args[0][0]
    assert added.result_id == 42
    assert added.action == "approved"
    assert added.role_category == "thriller"


async def test_get_pending_suggestions_returns_list() -> None:
    from app.models.db import ProfileSuggestion
    mock_suggestion = MagicMock(spec=ProfileSuggestion)
    mock_suggestion.id = 1
    mock_suggestion.suggestion_type = "add_skill"
    mock_suggestion.field_value = "canto lirico"
    mock_suggestion.reasoning = "Approved 8 musical roles"
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_suggestion])))
    ))
    repo = FeedbackRepository(session)
    result = await repo.get_pending_suggestions()
    assert len(result) == 1
    assert result[0].field_value == "canto lirico"
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_feedback_repository.py -v
```

Expected: `ImportError: cannot import name 'FeedbackRepository'`

- [ ] **Step 3: Implement FeedbackRepository**

Create `app/repositories/feedback_repository.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import ActorFeedback, ActorProfileDelta, ProfileSuggestion


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_feedback(self, result_id: int, action: str, role_category: str) -> ActorFeedback:
        feedback = ActorFeedback(result_id=result_id, action=action, role_category=role_category)
        self._session.add(feedback)
        await self._session.flush()
        return feedback

    async def get_pending_suggestions(self) -> list[ProfileSuggestion]:
        return (
            await self._session.execute(
                select(ProfileSuggestion).where(ProfileSuggestion.status == "pending")
            )
        ).scalars().all()

    async def apply_suggestion(self, suggestion_id: int) -> None:
        result = await self._session.execute(
            select(ProfileSuggestion).where(ProfileSuggestion.id == suggestion_id)
        )
        suggestion = result.scalars().first()
        if not suggestion:
            return
        suggestion.status = "applied"
        if suggestion.suggestion_type == "add_skill":
            delta = ActorProfileDelta(
                field_name="skill",
                field_value=suggestion.field_value,
                source="user_confirmed",
            )
            self._session.add(delta)
        await self._session.flush()

    async def dismiss_suggestion(self, suggestion_id: int) -> None:
        result = await self._session.execute(
            select(ProfileSuggestion).where(ProfileSuggestion.id == suggestion_id)
        )
        suggestion = result.scalars().first()
        if suggestion:
            suggestion.status = "dismissed"
            await self._session.flush()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_feedback_repository.py -v
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/repositories/feedback_repository.py tests/test_feedback_repository.py
git commit -m "feat: add FeedbackRepository"
```

---

## Task 12: Telegram bot with inline keyboard

**Files:**
- Create: `app/notifications/telegram_bot.py`
- Create: `tests/test_telegram_bot_notifier.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_telegram_bot_notifier.py`:

```python
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

    with patch("app.notifications.telegram_bot.Bot", return_value=mock_bot):
        notifier = TelegramBotNotifier(bot_token="fake", chat_id="123")
        await notifier.send_listing(1, _make_listing())

    mock_bot.send_message.assert_called_once()
    call_kwargs = mock_bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == "123"
    assert "reply_markup" in call_kwargs
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_telegram_bot_notifier.py -v
```

Expected: `ImportError: cannot import name 'TelegramBotNotifier'`

- [ ] **Step 3: Implement TelegramBotNotifier**

Create `app/notifications/telegram_bot.py`:

```python
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
        # Legacy NotificationChannel interface — not used in v2 pipeline
        pass
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_telegram_bot_notifier.py -v
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/notifications/telegram_bot.py tests/test_telegram_bot_notifier.py
git commit -m "feat: add TelegramBotNotifier with inline keyboard HITL"
```

---

## Task 13: Telegram callback handler (webhook/polling)

**Files:**
- Create: `app/notifications/telegram_handler.py`
- Modify: `app/main.py` (in next task — handler is created here, wired in Task 14)

- [ ] **Step 1: Implement callback handler**

Create `app/notifications/telegram_handler.py`:

```python
import structlog
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from app.repositories.feedback_repository import FeedbackRepository
from app.storage.database import SessionLocal

log = structlog.get_logger()


async def _handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":")
    action_key = parts[0]
    result_id = int(parts[1])
    role_category = parts[2] if len(parts) > 2 else "other"

    action_map = {"approve": "approved", "save": "saved", "ignore": "ignored"}
    action = action_map.get(action_key, action_key)

    async with SessionLocal() as session:
        async with session.begin():
            repo = FeedbackRepository(session)
            await repo.save_feedback(result_id=result_id, action=action, role_category=role_category)

    label_map = {"approved": "✅ CV inviato", "saved": "⭐ Salvato", "ignored": "❌ Ignorato"}
    label = label_map.get(action, action)

    original = query.message.text if query.message else ""
    await query.edit_message_text(text=f"{original}\n\n{label}", reply_markup=None)
    log.info("telegram.feedback_saved", result_id=result_id, action=action)


async def _handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Profile management: visit /admin/profile")


async def _handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Stats: visit /admin/stats")


def build_application(bot_token: str) -> Application:  # type: ignore[type-arg]
    app = Application.builder().token(bot_token).build()
    app.add_handler(CallbackQueryHandler(_handle_callback))
    app.add_handler(CommandHandler("profile", _handle_profile))
    app.add_handler(CommandHandler("stats", _handle_stats))
    return app
```

- [ ] **Step 2: Verify import**

```bash
python -c "from app.notifications.telegram_handler import build_application; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/notifications/telegram_handler.py
git commit -m "feat: add Telegram callback handler for HITL feedback"
```

---

## Task 14: Orchestrator rewrite + main.py wiring

**Files:**
- Modify: `app/services/orchestrator.py`
- Modify: `app/main.py`

- [ ] **Step 1: Rewrite orchestrator**

Replace `app/services/orchestrator.py`:

```python
import hashlib
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.dedup_agent import DedupAgent
from app.agents.profile_matching_agent import ProfileMatchingAgent
from app.agents.query_generator_agent import QueryGeneratorAgent
from app.agents.search_agent import SearchAgent
from app.models.db import SearchResult as DBSearchResult
from app.notifications.telegram_bot import TelegramBotNotifier
from app.profile.loader import ProfileLoader
from app.repositories.run_repository import RunRepository

log = structlog.get_logger()


class SearchOrchestrator:
    def __init__(
        self,
        search_agent: SearchAgent,
        profile_matching_agent: ProfileMatchingAgent,
        query_generator_agent: QueryGeneratorAgent,
        dedup_agent: DedupAgent,
        profile_loader: ProfileLoader,
        notifier: TelegramBotNotifier | None = None,
        minimum_match_score: float = 0.3,
        notification_top_n: int = 5,
    ) -> None:
        self.search_agent = search_agent
        self.profile_matching_agent = profile_matching_agent
        self.query_generator_agent = query_generator_agent
        self.dedup_agent = dedup_agent
        self.profile_loader = profile_loader
        self.notifier = notifier
        self.minimum_match_score = minimum_match_score
        self.notification_top_n = notification_top_n

    async def execute(self, session: AsyncSession, search_id: int, config: dict[str, object]) -> None:
        repo = RunRepository(session)
        run = await repo.create_run(search_id)
        try:
            profile = await self.profile_loader.load(session)
            queries = await self.query_generator_agent.execute(profile)
            log.info("orchestrator.queries_generated", count=len(queries))

            raw = await self.search_agent.execute(queries, {})
            deduped = await self.dedup_agent.execute(raw)
            log.info("orchestrator.deduped", count=len(deduped))

            ranked = await self.profile_matching_agent.execute(deduped, profile)
            log.info("orchestrator.ranked", count=len(ranked))

            db_results: list[DBSearchResult] = []
            for r in ranked:
                content_hash = hashlib.sha256((r.title + r.snippet).encode()).hexdigest()
                db_result = DBSearchResult(
                    run_id=run.id,
                    title=r.title,
                    url=r.url,
                    snippet=r.snippet,
                    content=None,
                    source=r.source,
                    published_at=r.published_at,
                    score=r.match_score,
                    summary=r.rationale,
                    content_hash=content_hash,
                    role_category=r.role_category,
                    deadline=r.deadline,
                    rationale=r.rationale,
                    red_flags=r.red_flags,
                )
                db_results.append(db_result)
            await repo.save_results(run.id, db_results)
            # flush so SQLAlchemy populates .id on each db_result before we pass them to the notifier
            await session.flush()

            if self.notifier:
                top = ranked[: self.notification_top_n]
                for i, listing in enumerate(top):
                    db_id = db_results[i].id or 0  # id populated after flush
                    await self.notifier.send_listing(db_id, listing)

            await repo.finalize_run(run, "success")
        except Exception as exc:
            log.error("orchestrator.failed", error=str(exc))
            await repo.finalize_run(run, "failed", str(exc))
            raise
```

- [ ] **Step 2: Rewrite main.py**

Replace `app/main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.agents.dedup_agent import DedupAgent
from app.agents.profile_matching_agent import ProfileMatchingAgent
from app.agents.query_generator_agent import QueryGeneratorAgent
from app.agents.search_agent import SearchAgent
from app.api.routes import router
from app.config.settings import get_settings
from app.core.logging import configure_logging
from app.notifications.telegram_bot import TelegramBotNotifier
from app.notifications.telegram_handler import build_application
from app.profile.loader import ProfileLoader
from app.providers.tavily import TavilyProvider
from app.scheduler.scheduler_service import SchedulerService
from app.services.llm_service import LLMService
from app.services.orchestrator import SearchOrchestrator

settings = get_settings()
configure_logging(settings.log_level)

llm = LLMService()

notifier: TelegramBotNotifier | None = None
telegram_app = None
if settings.telegram_enabled and settings.telegram_bot_token:
    notifier = TelegramBotNotifier(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )
    telegram_app = build_application(settings.telegram_bot_token)

search_orchestrator = SearchOrchestrator(
    search_agent=SearchAgent(TavilyProvider()),
    profile_matching_agent=ProfileMatchingAgent(
        llm=llm,
        minimum_score=settings.minimum_match_score,
        batch_size=settings.matching_batch_size,
    ),
    query_generator_agent=QueryGeneratorAgent(llm=llm),
    dedup_agent=DedupAgent(),
    profile_loader=ProfileLoader(yaml_path=settings.actor_profile_path),
    notifier=notifier,
    notification_top_n=settings.notification_top_n,
)
scheduler = SchedulerService(search_orchestrator)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await scheduler.start()
    if telegram_app:
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling()
    yield
    if telegram_app:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
    await scheduler.shutdown()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router, prefix="/api/v1")
```

- [ ] **Step 3: Run full test suite**

```bash
pytest -v
```

Expected: all existing + new tests PASS. Fix any type errors.

- [ ] **Step 4: Ruff + mypy**

```bash
ruff check app/
mypy app/
```

Fix any issues before committing.

- [ ] **Step 5: Commit**

```bash
git add app/services/orchestrator.py app/main.py
git commit -m "feat: rewrite orchestrator and main.py for actor-profile-centric pipeline"
```

---

## Task 15: Integration smoke test

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Ensure DB fixture exists in conftest**

Check `tests/conftest.py`. If it doesn't already have a test DB fixture, add:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.db import Base

TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/actor_searcher_test"


@pytest.fixture()
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

- [ ] **Step 2: Run full suite**

```bash
pytest -v --tb=short 2>&1 | tail -20
```

Expected: all tests PASS, no import errors.

- [ ] **Step 3: Final commit for Phase 1**

```bash
git add tests/conftest.py
git commit -m "test: ensure DB fixture in conftest"
git tag v2-phase1-mvp
```

---

## Phase 1 Complete Checklist

- [ ] `actor_profile.yaml` populated with real actor data
- [ ] Migration `0002` applied: `alembic upgrade head`
- [ ] `TELEGRAM_ENABLED=true` + `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` set in `.env`
- [ ] `TAVILY_API_KEY` set
- [ ] `OPENAI_API_KEY` set
- [ ] `docker compose up` — all services healthy
- [ ] Create a test `Search` via `POST /api/v1/searches` with `{"name":"test","interval_minutes":60,"config":{}}`
- [ ] Trigger a run manually and verify Telegram message arrives with inline keyboard
- [ ] Tap "Ignora" on one result — verify `actor_feedback` row created in DB

---
