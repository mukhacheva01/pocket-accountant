"""Tests for backend.services.container."""

from unittest.mock import AsyncMock

from backend.services.container import build_services


def test_build_services_creates_all():
    session = AsyncMock()
    svc = build_services(session)
    assert svc.onboarding is not None
    assert svc.calendar is not None
    assert svc.reminders is not None
    assert svc.subscription is not None
    assert svc.finance is not None
    assert svc.documents is not None
    assert svc.laws is not None
    assert svc.ai is not None
    assert svc.tax is not None
    assert svc.templates is not None
