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
