import pytest
import yaml
from unittest.mock import AsyncMock, MagicMock
from app.profile.models import ActorProfile, PhysicalTraits
from app.profile.loader import ProfileLoader


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
    mock_session.execute = AsyncMock(side_effect=[
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[delta_row])))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
    ])

    loader = ProfileLoader(yaml_path=str(yaml_file))
    profile = await loader.load(mock_session)

    assert "base_skill" in profile.skills
    assert "canto lirico" in profile.skills
