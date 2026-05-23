import pytest
from unittest.mock import AsyncMock, MagicMock
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
