from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.admin.auth import require_admin
from app.api.deps import db_session_dep
from app.config.settings import get_settings
from app.models.db import ActorFeedback, ActorProfileDelta, ActorRolePreference, ProfileSuggestion
from app.profile.loader import ProfileLoader
from app.repositories.feedback_repository import FeedbackRepository

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("/profile", response_class=HTMLResponse)
async def get_profile(
    request: Request, session: AsyncSession = Depends(db_session_dep)
) -> HTMLResponse:
    settings = get_settings()
    loader = ProfileLoader(yaml_path=settings.actor_profile_path)
    profile = await loader.load(session)
    delta_rows = (
        await session.execute(
            select(ActorProfileDelta).where(ActorProfileDelta.active.is_(True))
        )
    ).scalars().all()
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "profile": profile, "delta_rows": delta_rows},
    )


@router.post("/profile/delta/add-skill")
async def add_skill(
    skill: str = Form(...), session: AsyncSession = Depends(db_session_dep)
) -> RedirectResponse:
    async with session.begin():
        delta = ActorProfileDelta(
            field_name="skill", field_value=skill.strip(), source="user_confirmed"
        )
        session.add(delta)
    return RedirectResponse(url="/admin/profile", status_code=303)


@router.post("/profile/delta/{delta_id}/remove")
async def remove_delta(
    delta_id: int, session: AsyncSession = Depends(db_session_dep)
) -> RedirectResponse:
    async with session.begin():
        result = await session.execute(
            select(ActorProfileDelta).where(ActorProfileDelta.id == delta_id)
        )
        row = result.scalars().first()
        if row:
            row.active = False
    return RedirectResponse(url="/admin/profile", status_code=303)


@router.get("/suggestions", response_class=HTMLResponse)
async def get_suggestions(
    request: Request, session: AsyncSession = Depends(db_session_dep)
) -> HTMLResponse:
    suggestions = (
        await session.execute(
            select(ProfileSuggestion)
            .where(ProfileSuggestion.status == "pending")
            .order_by(ProfileSuggestion.created_at.desc())
        )
    ).scalars().all()
    return templates.TemplateResponse(
        "suggestions.html", {"request": request, "suggestions": suggestions}
    )


@router.post("/suggestions/{suggestion_id}/apply")
async def apply_suggestion(
    suggestion_id: int, session: AsyncSession = Depends(db_session_dep)
) -> RedirectResponse:
    async with session.begin():
        repo = FeedbackRepository(session)
        await repo.apply_suggestion(suggestion_id)
    return RedirectResponse(url="/admin/suggestions", status_code=303)


@router.post("/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(
    suggestion_id: int, session: AsyncSession = Depends(db_session_dep)
) -> RedirectResponse:
    async with session.begin():
        repo = FeedbackRepository(session)
        await repo.dismiss_suggestion(suggestion_id)
    return RedirectResponse(url="/admin/suggestions", status_code=303)


@router.get("/stats", response_class=HTMLResponse)
async def get_stats(
    request: Request, session: AsyncSession = Depends(db_session_dep)
) -> HTMLResponse:
    prefs = (
        await session.execute(
            select(ActorRolePreference).order_by(ActorRolePreference.preference_score.desc())
        )
    ).scalars().all()
    total_feedback = (await session.execute(select(ActorFeedback))).scalars().all()
    counts: dict[str, int] = {"approved": 0, "saved": 0, "ignored": 0}
    for f in total_feedback:
        if f.action in counts:
            counts[f.action] += 1
    return templates.TemplateResponse(
        "stats.html", {"request": request, "prefs": prefs, "counts": counts}
    )


@router.post("/learner/run")
async def trigger_learner(
    session: AsyncSession = Depends(db_session_dep),
) -> RedirectResponse:
    from app.feedback.learner import PreferenceLearner
    async with session.begin():
        learner = PreferenceLearner()
        await learner.run(session)
    return RedirectResponse(url="/admin/suggestions", status_code=303)
