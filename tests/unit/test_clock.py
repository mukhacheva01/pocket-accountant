"""Tests for shared.clock."""

from datetime import timezone

from shared.clock import utcnow


def test_utcnow_returns_aware_utc():
    now = utcnow()
    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc
