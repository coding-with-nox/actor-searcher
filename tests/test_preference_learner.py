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
        ("approved", "thriller"), ("approved", "thriller"),
        ("approved", "thriller"), ("ignored", "thriller"),
    ])  # 3/4 = 0.75
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
    added = [call[0][0] for call in session.add.call_args_list]
    prefs = [o for o in added if isinstance(o, ActorRolePreference)]
    assert len(prefs) == 1
    assert prefs[0].role_category == "thriller"
    assert abs(prefs[0].preference_score - 0.75) < 0.01


async def test_learner_creates_suggestion_above_threshold() -> None:
    feedback = _make_feedback_rows([
        ("approved", "musical"), ("approved", "musical"),
        ("approved", "musical"), ("approved", "musical"),
    ])  # 4/4 = 1.0 → suggest add_skill
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
    added = [call[0][0] for call in session.add.call_args_list]
    suggestions = [o for o in added if isinstance(o, ProfileSuggestion)]
    assert len(suggestions) == 1
    assert suggestions[0].suggestion_type == "add_skill"
    assert suggestions[0].field_value == "musical"


async def test_learner_skips_below_min_samples() -> None:
    feedback = _make_feedback_rows([("approved", "drama")])  # only 1, below min_samples=3
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
    added = [call[0][0] for call in session.add.call_args_list]
    assert not any(isinstance(o, ActorRolePreference) for o in added)
