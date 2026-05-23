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
