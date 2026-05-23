import pytest
from unittest.mock import AsyncMock, patch
from app.providers.backstage import BackstageProvider
from app.models.schemas import SearchResult


async def test_backstage_normalizes_to_search_result() -> None:
    mock_listing = {
        "title": "Lead Role — Thriller",
        "url": "https://www.backstage.com/listing/123",
        "snippet": "Looking for 25-35 male athletic actor in Rome",
    }
    with patch("app.providers.backstage.BackstageProvider._scrape_listings", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = [mock_listing]
        provider = BackstageProvider(email="test@test.com", password="pw")
        results = await provider.search("casting thriller Roma", {})
    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].source == "backstage"
    assert "Thriller" in results[0].title


async def test_backstage_returns_empty_on_scrape_error() -> None:
    with patch("app.providers.backstage.BackstageProvider._scrape_listings", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.side_effect = Exception("Playwright failed")
        provider = BackstageProvider(email="test@test.com", password="pw")
        results = await provider.search("query", {})
    assert results == []
