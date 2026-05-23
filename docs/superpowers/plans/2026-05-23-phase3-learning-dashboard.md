# Phase 3 — Learning + Admin Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `PreferenceLearner` (aggregates HITL feedback into profile suggestions) and an admin dashboard (FastAPI + Jinja2) where the actor can view/edit their profile, review AI suggestions, and see feedback statistics.

**Architecture:** `PreferenceLearner` runs as a weekly APScheduler job. It reads `actor_feedback`, computes per-category preference scores, updates `actor_role_preference`, and generates `ProfileSuggestion` entries when thresholds are crossed. The admin dashboard is a FastAPI router with Jinja2 templates, protected by HTTP Basic auth.

**Tech Stack:** FastAPI, Jinja2 (already in deps), SQLAlchemy async, APScheduler (existing), HTTP Basic auth via `fastapi.security`

**Prerequisite:** Phase 1 and Phase 2 plans fully implemented and passing.

**Spec:** `docs/superpowers/specs/2026-05-23-actor-searcher-v2-design.md` §5, §6, §7

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `app/feedback/learner.py` | `PreferenceLearner` — aggregates feedback, creates suggestions |
| Create | `app/feedback/__init__.py` | Package marker |
| Create | `app/admin/__init__.py` | Package marker |
| Create | `app/admin/routes.py` | FastAPI admin routes (profile, suggestions, stats, runs) |
| Create | `app/admin/auth.py` | HTTP Basic auth dependency |
| Create | `app/admin/templates/base.html` | Jinja2 base layout |
| Create | `app/admin/templates/profile.html` | Profile editor |
| Create | `app/admin/templates/suggestions.html` | Suggestions list |
| Create | `app/admin/templates/stats.html` | Feedback statistics |
| Modify | `app/scheduler/scheduler_service.py` | Add weekly PreferenceLearner job |
| Modify | `app/main.py` | Mount admin router + Jinja2 templates |
| Create | `tests/test_preference_learner.py` | |

---

## Task 1: PreferenceLearner

**Files:**
- Create: `app/feedback/__init__.py`
- Create: `app/feedback/learner.py`
- Create: `tests/test_preference_learner.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_preference_learner.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.feedback.learner import PreferenceLearner
from app.models.db import ActorFeedback, ActorRolePreference, ProfileSuggestion


def _make_feedback_rows(rows: list[tuple[str, str]]) -> list[ActorFeedback]:
    result = []
    for action, category in rows:
        row = MagicMock(spec=ActorFeedback)
        row.action = action
        row.role_category = category
        result.append(row)
    return result


async def test_learner_updates_preference_scores() -> None:
    feedback = _make_feedback_rows([
        ("approved", "thriller"),
        ("approved", "thriller"),
        ("approved", "thriller"),
        ("ignored", "thriller"),
    ])  # thriller: 3 approved, 1 ignored → score 0.75

    existing_prefs: list[ActorRolePreference] = []

    session = AsyncMock()
    session.execute = AsyncMock()
    session.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=feedback)))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=existing_prefs)))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # suggestions
    ]
    session.add = MagicMock()
    session.flush = AsyncMock()

    learner = PreferenceLearner(suggestion_threshold_high=0.75, suggestion_threshold_low=0.2, min_samples=3)
    await learner.run(session)

    added_objects = [call[0][0] for call in session.add.call_args_list]
    pref_objects = [o for o in added_objects if isinstance(o, ActorRolePreference)]
    assert len(pref_objects) == 1
    assert pref_objects[0].role_category == "thriller"
    assert abs(pref_objects[0].preference_score - 0.75) < 0.01


async def test_learner_creates_suggestion_when_above_threshold() -> None:
    feedback = _make_feedback_rows([
        ("approved", "musical"),
        ("approved", "musical"),
        ("approved", "musical"),
        ("approved", "musical"),
    ])  # musical: 4/4 = 1.0 → above threshold → suggest adding skill

    session = AsyncMock()
    session.execute = AsyncMock()
    session.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=feedback)))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # no existing prefs
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # no existing suggestions
    ]
    session.add = MagicMock()
    session.flush = AsyncMock()

    learner = PreferenceLearner(suggestion_threshold_high=0.75, suggestion_threshold_low=0.2, min_samples=3)
    await learner.run(session)

    added_objects = [call[0][0] for call in session.add.call_args_list]
    suggestions = [o for o in added_objects if isinstance(o, ProfileSuggestion)]
    assert len(suggestions) == 1
    assert suggestions[0].suggestion_type == "add_skill"
    assert suggestions[0].field_value == "musical"


async def test_learner_skips_below_min_samples() -> None:
    feedback = _make_feedback_rows([("approved", "drama")])  # only 1 sample, below min_samples=3

    session = AsyncMock()
    session.execute = AsyncMock()
    session.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=feedback)))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
    ]
    session.add = MagicMock()
    session.flush = AsyncMock()

    learner = PreferenceLearner(suggestion_threshold_high=0.75, suggestion_threshold_low=0.2, min_samples=3)
    await learner.run(session)

    added_objects = [call[0][0] for call in session.add.call_args_list]
    prefs = [o for o in added_objects if isinstance(o, ActorRolePreference)]
    assert len(prefs) == 0  # no pref created for drama — not enough samples
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_preference_learner.py -v
```

Expected: `ImportError: cannot import name 'PreferenceLearner'`

- [ ] **Step 3: Implement PreferenceLearner**

Create `app/feedback/__init__.py` (empty).

Create `app/feedback/learner.py`:

```python
from collections import defaultdict
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import ActorFeedback, ActorRolePreference, ProfileSuggestion

log = structlog.get_logger()


class PreferenceLearner:
    def __init__(
        self,
        suggestion_threshold_high: float = 0.75,
        suggestion_threshold_low: float = 0.2,
        min_samples: int = 5,
    ) -> None:
        self._high = suggestion_threshold_high
        self._low = suggestion_threshold_low
        self._min_samples = min_samples

    async def run(self, session: AsyncSession) -> None:
        feedback_rows = (
            await session.execute(select(ActorFeedback))
        ).scalars().all()

        counts: dict[str, dict[str, int]] = defaultdict(lambda: {"approved": 0, "rejected": 0, "total": 0})
        for row in feedback_rows:
            counts[row.role_category]["total"] += 1
            if row.action == "approved":
                counts[row.role_category]["approved"] += 1
            elif row.action in ("ignored", "rejected"):
                counts[row.role_category]["rejected"] += 1

        existing_prefs = {
            r.role_category: r
            for r in (await session.execute(select(ActorRolePreference))).scalars().all()
        }
        existing_suggestion_values = {
            r.field_value
            for r in (await session.execute(
                select(ProfileSuggestion).where(ProfileSuggestion.status == "pending")
            )).scalars().all()
        }

        for category, data in counts.items():
            total = data["total"]
            if total < self._min_samples:
                log.debug("learner.skipping_low_sample", category=category, total=total)
                continue

            approved = data["approved"]
            score = approved / total

            if category in existing_prefs:
                existing_prefs[category].approved_count = approved
                existing_prefs[category].rejected_count = data["rejected"]
                existing_prefs[category].preference_score = score
            else:
                pref = ActorRolePreference(
                    role_category=category,
                    approved_count=approved,
                    rejected_count=data["rejected"],
                    preference_score=score,
                )
                session.add(pref)

            if score >= self._high and category not in existing_suggestion_values:
                suggestion = ProfileSuggestion(
                    suggestion_type="add_skill",
                    field_name="skill",
                    field_value=category,
                    reasoning=(
                        f"Approved {approved}/{total} listings in category '{category}' "
                        f"(score: {score:.0%}). Consider adding this to your skills."
                    ),
                )
                session.add(suggestion)
                log.info("learner.suggestion_created", category=category, score=score)
            elif score <= self._low and category not in existing_suggestion_values:
                suggestion = ProfileSuggestion(
                    suggestion_type="deprioritize_category",
                    field_name="role_category",
                    field_value=category,
                    reasoning=(
                        f"Only {approved}/{total} approvals in category '{category}' "
                        f"(score: {score:.0%}). Consider deprioritizing this category."
                    ),
                )
                session.add(suggestion)
                log.info("learner.deprioritize_suggestion", category=category, score=score)

        await session.flush()
        log.info("learner.run_complete", categories_processed=len(counts))
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_preference_learner.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/feedback/ tests/test_preference_learner.py
git commit -m "feat: add PreferenceLearner — aggregates HITL feedback into profile suggestions"
```

---

## Task 2: Wire PreferenceLearner into scheduler

**Files:**
- Modify: `app/scheduler/scheduler_service.py`

- [ ] **Step 1: Add weekly learner job**

Replace `app/scheduler/scheduler_service.py`:

```python
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from app.feedback.learner import PreferenceLearner
from app.models.db import Search
from app.services.orchestrator import SearchOrchestrator
from app.storage.database import SessionLocal

log = structlog.get_logger()


class SchedulerService:
    def __init__(self, orchestrator: SearchOrchestrator, learner: PreferenceLearner | None = None) -> None:
        self.scheduler = AsyncIOScheduler()
        self.orchestrator = orchestrator
        self.learner = learner or PreferenceLearner()

    async def register_jobs(self) -> None:
        async with SessionLocal() as session:
            searches = (
                await session.execute(select(Search).where(Search.enabled.is_(True)))
            ).scalars().all()
        for search in searches:
            self.scheduler.add_job(
                self._run_job,
                "interval",
                minutes=search.interval_minutes,
                id=f"search-{search.id}",
                args=[search.id, search.config],
                replace_existing=True,
            )
        # Weekly preference learning job
        self.scheduler.add_job(
            self._run_learner,
            "interval",
            weeks=1,
            id="preference-learner",
            replace_existing=True,
        )
        log.info("scheduler.jobs_registered", search_count=len(searches))

    async def _run_job(self, search_id: int, config: dict[str, object]) -> None:
        async with SessionLocal() as session:
            async with session.begin():
                await self.orchestrator.execute(session, search_id, config)

    async def _run_learner(self) -> None:
        async with SessionLocal() as session:
            async with session.begin():
                await self.learner.run(session)
        log.info("scheduler.learner_run_complete")

    async def start(self) -> None:
        await self.register_jobs()
        self.scheduler.start()

    async def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from app.scheduler.scheduler_service import SchedulerService; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/scheduler/scheduler_service.py
git commit -m "feat: add weekly PreferenceLearner job to scheduler"
```

---

## Task 3: Admin auth dependency

**Files:**
- Create: `app/admin/__init__.py`
- Create: `app/admin/auth.py`

- [ ] **Step 1: Implement Basic auth**

Create `app/admin/__init__.py` (empty).

Create `app/admin/auth.py`:

```python
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.config.settings import get_settings

security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    settings = get_settings()
    correct_user = secrets.compare_digest(credentials.username.encode(), settings.admin_username.encode())
    correct_pass = secrets.compare_digest(credentials.password.encode(), settings.admin_password.encode())
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
```

- [ ] **Step 2: Verify import**

```bash
python -c "from app.admin.auth import require_admin; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/admin/
git commit -m "feat: add HTTP Basic auth dependency for admin routes"
```

---

## Task 4: Admin routes

**Files:**
- Create: `app/admin/routes.py`

- [ ] **Step 1: Implement routes**

Create `app/admin/routes.py`:

```python
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.admin.auth import require_admin
from app.api.deps import db_session_dep
from app.config.settings import get_settings
from app.feedback.learner import PreferenceLearner
from app.models.db import ActorFeedback, ActorProfileDelta, ActorRolePreference, ProfileSuggestion
from app.profile.loader import ProfileLoader
from app.repositories.feedback_repository import FeedbackRepository
from app.storage.database import SessionLocal

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("/profile", response_class=HTMLResponse)
async def get_profile(request: Request, session: AsyncSession = Depends(db_session_dep)) -> HTMLResponse:
    settings = get_settings()
    loader = ProfileLoader(yaml_path=settings.actor_profile_path)
    profile = await loader.load(session)
    delta_rows = (
        await session.execute(select(ActorProfileDelta).where(ActorProfileDelta.active.is_(True)))
    ).scalars().all()
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "profile": profile, "delta_rows": delta_rows},
    )


@router.post("/profile/delta/add-skill")
async def add_skill(skill: str = Form(...), session: AsyncSession = Depends(db_session_dep)) -> RedirectResponse:
    async with session.begin():
        delta = ActorProfileDelta(field_name="skill", field_value=skill.strip(), source="user_confirmed")
        session.add(delta)
    return RedirectResponse(url="/admin/profile", status_code=303)


@router.post("/profile/delta/{delta_id}/remove")
async def remove_delta(delta_id: int, session: AsyncSession = Depends(db_session_dep)) -> RedirectResponse:
    async with session.begin():
        result = await session.execute(select(ActorProfileDelta).where(ActorProfileDelta.id == delta_id))
        row = result.scalars().first()
        if row:
            row.active = False
    return RedirectResponse(url="/admin/profile", status_code=303)


@router.get("/suggestions", response_class=HTMLResponse)
async def get_suggestions(request: Request, session: AsyncSession = Depends(db_session_dep)) -> HTMLResponse:
    suggestions = (
        await session.execute(
            select(ProfileSuggestion).where(ProfileSuggestion.status == "pending").order_by(ProfileSuggestion.created_at.desc())
        )
    ).scalars().all()
    return templates.TemplateResponse("suggestions.html", {"request": request, "suggestions": suggestions})


@router.post("/suggestions/{suggestion_id}/apply")
async def apply_suggestion(suggestion_id: int, session: AsyncSession = Depends(db_session_dep)) -> RedirectResponse:
    async with session.begin():
        repo = FeedbackRepository(session)
        await repo.apply_suggestion(suggestion_id)
    return RedirectResponse(url="/admin/suggestions", status_code=303)


@router.post("/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(suggestion_id: int, session: AsyncSession = Depends(db_session_dep)) -> RedirectResponse:
    async with session.begin():
        repo = FeedbackRepository(session)
        await repo.dismiss_suggestion(suggestion_id)
    return RedirectResponse(url="/admin/suggestions", status_code=303)


@router.get("/stats", response_class=HTMLResponse)
async def get_stats(request: Request, session: AsyncSession = Depends(db_session_dep)) -> HTMLResponse:
    prefs = (await session.execute(select(ActorRolePreference).order_by(ActorRolePreference.preference_score.desc()))).scalars().all()
    total_feedback = (await session.execute(select(ActorFeedback))).scalars().all()
    counts = {"approved": 0, "saved": 0, "ignored": 0}
    for f in total_feedback:
        if f.action in counts:
            counts[f.action] += 1
    return templates.TemplateResponse("stats.html", {"request": request, "prefs": prefs, "counts": counts})


@router.post("/learner/run")
async def trigger_learner(session: AsyncSession = Depends(db_session_dep)) -> RedirectResponse:
    async with session.begin():
        learner = PreferenceLearner()
        await learner.run(session)
    return RedirectResponse(url="/admin/suggestions", status_code=303)
```

- [ ] **Step 2: Commit**

```bash
git add app/admin/routes.py
git commit -m "feat: add admin dashboard routes (profile, suggestions, stats)"
```

---

## Task 5: Jinja2 templates

**Files:**
- Create: `app/admin/templates/base.html`
- Create: `app/admin/templates/profile.html`
- Create: `app/admin/templates/suggestions.html`
- Create: `app/admin/templates/stats.html`

- [ ] **Step 1: Create base template**

Create `app/admin/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Actor Searcher — {% block title %}Admin{% endblock %}</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }
    nav a { margin-right: 1.5rem; text-decoration: none; color: #0066cc; font-weight: 500; }
    nav a:hover { text-decoration: underline; }
    h1 { border-bottom: 2px solid #eee; padding-bottom: 0.5rem; }
    .card { border: 1px solid #ddd; border-radius: 6px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
    .score-bar { background: #eee; border-radius: 3px; height: 8px; }
    .score-fill { background: #28a745; border-radius: 3px; height: 8px; }
    .btn { display: inline-block; padding: 0.35rem 0.75rem; border-radius: 4px; border: none; cursor: pointer; font-size: 0.9rem; }
    .btn-primary { background: #0066cc; color: white; }
    .btn-danger { background: #dc3545; color: white; }
    .btn-success { background: #28a745; color: white; }
    form { display: inline; }
    .tag { background: #f0f0f0; border-radius: 12px; padding: 2px 10px; font-size: 0.85rem; margin: 2px; display: inline-block; }
    .red-flag { color: #dc3545; font-size: 0.85rem; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #eee; }
  </style>
</head>
<body>
  <nav>
    <a href="/admin/profile">Profile</a>
    <a href="/admin/suggestions">Suggestions</a>
    <a href="/admin/stats">Stats</a>
  </nav>
  <main>{% block content %}{% endblock %}</main>
</body>
</html>
```

- [ ] **Step 2: Create profile template**

Create `app/admin/templates/profile.html`:

```html
{% extends "base.html" %}
{% block title %}Profile{% endblock %}
{% block content %}
<h1>Actor Profile</h1>

<div class="card">
  <h2>{{ profile.name }}, {{ profile.age }} — {{ profile.gender }}</h2>
  <p><strong>Location:</strong> {{ profile.location }} (max {{ profile.max_travel_km }}km)</p>
  <p><strong>Languages:</strong> {{ profile.languages | join(", ") }}</p>
  <p><strong>Physical:</strong> {{ profile.physical.height_cm }}cm, {{ profile.physical.build }}, {{ profile.physical.hair_color }} hair, {{ profile.physical.eye_color }} eyes</p>
  <p><strong>Union:</strong> {{ profile.union_status }} | <strong>Experience:</strong> {{ profile.experience_level }}</p>
  <p><strong>Available from:</strong> {{ profile.availability_from }}</p>
</div>

<h2>Skills</h2>
<div style="margin-bottom: 1rem;">
  {% for skill in profile.skills %}
    <span class="tag">{{ skill }}</span>
  {% endfor %}
</div>

<h3>Skills added via delta</h3>
{% for row in delta_rows %}
  {% if row.field_name == "skill" %}
  <div style="margin-bottom: 0.5rem;">
    <span class="tag">{{ row.field_value }}</span>
    <form action="/admin/profile/delta/{{ row.id }}/remove" method="post" style="display:inline">
      <button class="btn btn-danger" style="font-size:0.75rem;padding:1px 6px">×</button>
    </form>
  </div>
  {% endif %}
{% endfor %}

<h3>Add skill</h3>
<form action="/admin/profile/delta/add-skill" method="post">
  <input type="text" name="skill" placeholder="e.g. canto lirico" required style="padding:0.4rem;border:1px solid #ccc;border-radius:4px">
  <button type="submit" class="btn btn-primary">Add</button>
</form>

{% if profile.role_preferences %}
<h2>Learned Preferences</h2>
<table>
  <tr><th>Category</th><th>Preference Score</th></tr>
  {% for category, score in profile.role_preferences.items() | sort(attribute="1", reverse=True) %}
  <tr>
    <td>{{ category }}</td>
    <td>
      <div class="score-bar"><div class="score-fill" style="width:{{ (score * 100) | int }}%"></div></div>
      {{ "%.0f" | format(score * 100) }}%
    </td>
  </tr>
  {% endfor %}
</table>
{% endif %}
{% endblock %}
```

- [ ] **Step 3: Create suggestions template**

Create `app/admin/templates/suggestions.html`:

```html
{% extends "base.html" %}
{% block title %}Suggestions{% endblock %}
{% block content %}
<h1>Profile Suggestions</h1>
<p>AI-generated suggestions based on your feedback history.</p>

<form action="/admin/learner/run" method="post" style="margin-bottom: 1.5rem">
  <button type="submit" class="btn btn-primary">Run Learner Now</button>
</form>

{% if not suggestions %}
  <p style="color:#666">No pending suggestions. Keep using the Telegram bot to generate feedback data.</p>
{% endif %}

{% for s in suggestions %}
<div class="card">
  <strong>{{ s.suggestion_type | replace("_", " ") | title }}:</strong>
  <span class="tag">{{ s.field_value }}</span>
  <p style="color:#555;font-size:0.9rem">{{ s.reasoning }}</p>
  <form action="/admin/suggestions/{{ s.id }}/apply" method="post">
    <button type="submit" class="btn btn-success">Apply</button>
  </form>
  <form action="/admin/suggestions/{{ s.id }}/dismiss" method="post">
    <button type="submit" class="btn" style="background:#f0f0f0">Dismiss</button>
  </form>
</div>
{% endfor %}
{% endblock %}
```

- [ ] **Step 4: Create stats template**

Create `app/admin/templates/stats.html`:

```html
{% extends "base.html" %}
{% block title %}Stats{% endblock %}
{% block content %}
<h1>Feedback Statistics</h1>

<div class="card">
  <h2>Overall Actions</h2>
  <table>
    <tr><th>Action</th><th>Count</th></tr>
    <tr><td>✅ Approved (CV sent)</td><td>{{ counts.approved }}</td></tr>
    <tr><td>⭐ Saved</td><td>{{ counts.saved }}</td></tr>
    <tr><td>❌ Ignored</td><td>{{ counts.ignored }}</td></tr>
  </table>
</div>

<h2>By Category</h2>
{% if not prefs %}
  <p style="color:#666">No preference data yet. Needs at least {{ min_samples }} feedbacks per category.</p>
{% endif %}
{% for pref in prefs %}
<div class="card">
  <strong>{{ pref.role_category }}</strong>
  <span style="float:right;color:#555">{{ pref.approved_count }} approved / {{ pref.rejected_count }} rejected</span>
  <div class="score-bar" style="margin-top:0.5rem">
    <div class="score-fill" style="width:{{ (pref.preference_score * 100) | int }}%;background:{% if pref.preference_score >= 0.75 %}#28a745{% elif pref.preference_score >= 0.4 %}#ffc107{% else %}#dc3545{% endif %}"></div>
  </div>
  <small>{{ "%.0f" | format(pref.preference_score * 100) }}% approval rate</small>
</div>
{% endfor %}
{% endblock %}
```

- [ ] **Step 5: Commit**

```bash
git add app/admin/templates/
git commit -m "feat: add Jinja2 admin dashboard templates"
```

---

## Task 6: Wire admin into main.py

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add admin router and static file serving**

In `app/main.py`, add after the existing imports:

```python
from app.admin.routes import router as admin_router
from app.feedback.learner import PreferenceLearner
```

Update the `SchedulerService` instantiation:

```python
scheduler = SchedulerService(search_orchestrator, learner=PreferenceLearner())
```

After `app.include_router(router, prefix="/api/v1")`, add:

```python
app.include_router(admin_router)
```

- [ ] **Step 2: Run the app locally and verify dashboard**

```bash
ADMIN_PASSWORD=test uvicorn app.main:app --reload
```

Open `http://localhost:8000/admin/profile` in browser. Enter credentials (`admin` / `test`). Verify:
- Profile page renders with actor data
- Skills are shown
- Add skill form works

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

Fix any issues.

- [ ] **Step 5: Final commit**

```bash
git add app/main.py app/scheduler/scheduler_service.py
git commit -m "feat: wire admin dashboard and PreferenceLearner into app"
git tag v2-phase3-complete
```

---

## Phase 3 Completion Checklist

- [ ] `ADMIN_USERNAME` and `ADMIN_PASSWORD` set in `.env` (not default "changeme")
- [ ] Dashboard accessible at `http://localhost:8000/admin/profile`
- [ ] Profile skills correctly reflect YAML base + DB delta
- [ ] Add a test skill via dashboard → verify it appears in next run's profile
- [ ] Trigger PreferenceLearner via "Run Learner Now" button → check suggestions appear (requires existing feedback data)
- [ ] Apply a suggestion → verify `actor_profile_delta` row created in DB
- [ ] Stats page shows correct feedback counts

---

## End-to-End Test: Full System Smoke Test

After all 3 phases are complete, run this manual E2E test:

1. **Start services:** `docker compose up`
2. **Apply migrations:** `alembic upgrade head`
3. **Create a search:** `POST /api/v1/searches` with `{"name":"daily","interval_minutes":60,"config":{}}`
4. **Trigger run:** Wait for scheduler or create a 1-minute search for testing
5. **Verify Telegram:** Bot sends listing cards with inline keyboard
6. **Tap ❌ Ignora** on 2 listings → verify `actor_feedback` rows in DB
7. **Tap ✅ Invia CV** on 1 listing → verify feedback saved + URL shows
8. **Run learner:** `POST /admin/learner/run` → check `/admin/suggestions`
9. **Apply suggestion** if present → check `/admin/profile` shows new skill
10. **Verify next run** uses updated profile (check logs for new query including new skill)

---
