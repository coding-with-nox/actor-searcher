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
