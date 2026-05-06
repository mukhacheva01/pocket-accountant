"""Tests for backend.integrations.law_sources."""

from datetime import datetime, timezone

from backend.integrations.law_sources import EmptyLawFetcher, FetchedLawUpdate


def test_fetched_law_update_defaults():
    u = FetchedLawUpdate(
        source="ФНС",
        source_url="https://example.com",
        title="Update",
        summary="Summary",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert u.effective_date is None
    assert u.tags == []
    assert u.full_text == ""


async def test_empty_law_fetcher():
    fetcher = EmptyLawFetcher()
    result = await fetcher.fetch()
    assert result == []
