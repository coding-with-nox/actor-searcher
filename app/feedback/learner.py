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

        counts: dict[str, dict[str, int]] = defaultdict(
            lambda: {"approved": 0, "rejected": 0, "total": 0}
        )
        for row in feedback_rows:
            counts[row.role_category]["total"] += 1
            if row.action == "approved":
                counts[row.role_category]["approved"] += 1
            elif row.action in ("ignored", "rejected"):
                counts[row.role_category]["rejected"] += 1

        existing_prefs = {
            r.role_category: r
            for r in (
                await session.execute(select(ActorRolePreference))
            ).scalars().all()
        }
        existing_suggestion_values = {
            r.field_value
            for r in (
                await session.execute(
                    select(ProfileSuggestion).where(ProfileSuggestion.status == "pending")
                )
            ).scalars().all()
        }

        for category, data in counts.items():
            total = data["total"]
            if total < self._min_samples:
                log.debug("learner.skipping", category=category, total=total)
                continue

            approved = data["approved"]
            score = approved / total

            if category in existing_prefs:
                existing_prefs[category].approved_count = approved
                existing_prefs[category].rejected_count = data["rejected"]
                existing_prefs[category].preference_score = score
            else:
                session.add(
                    ActorRolePreference(
                        role_category=category,
                        approved_count=approved,
                        rejected_count=data["rejected"],
                        preference_score=score,
                    )
                )

            if score >= self._high and category not in existing_suggestion_values:
                session.add(
                    ProfileSuggestion(
                        suggestion_type="add_skill",
                        field_name="skill",
                        field_value=category,
                        reasoning=(
                            f"Approved {approved}/{total} listings in '{category}' "
                            f"(score: {score:.0%}). Consider adding to skills."
                        ),
                    )
                )
            elif score <= self._low and category not in existing_suggestion_values:
                session.add(
                    ProfileSuggestion(
                        suggestion_type="deprioritize_category",
                        field_name="role_category",
                        field_value=category,
                        reasoning=(
                            f"Only {approved}/{total} approvals in '{category}' "
                            f"(score: {score:.0%}). Consider deprioritizing."
                        ),
                    )
                )

        await session.flush()
        log.info("learner.complete", categories_processed=len(counts))
