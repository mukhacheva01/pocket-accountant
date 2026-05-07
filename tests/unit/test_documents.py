"""Tests for backend.services.documents."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from shared.db.enums import EventCategory, EventStatus
from backend.services.documents import DocumentsService


@pytest.fixture()
def svc():
    calendar = AsyncMock()
    return DocumentsService(calendar)


class TestUpcomingDocuments:
    async def test_filters_document_related(self, svc):
        e1 = SimpleNamespace(
            calendar_event=SimpleNamespace(
                category=EventCategory.DECLARATION,
                title="Декларация",
                priority=1,
                legal_basis="НК",
            ),
            due_date=date(2026, 7, 1),
            status=EventStatus.PENDING,
        )
        e2 = SimpleNamespace(
            calendar_event=SimpleNamespace(
                category=EventCategory.TAX,
                title="Налог",
                priority=2,
                legal_basis="НК",
            ),
            due_date=date(2026, 7, 15),
            status=EventStatus.PENDING,
        )
        e3 = SimpleNamespace(calendar_event=None, due_date=date(2026, 7, 20), status=EventStatus.PENDING)
        svc.calendar.upcoming.return_value = [e1, e2, e3]
        docs = await svc.upcoming_documents("u1")
        assert len(docs) == 1
        assert docs[0]["title"] == "Декларация"
        assert "action_required" in docs[0]
        assert "risk_hint" in docs[0]

    async def test_empty(self, svc):
        svc.calendar.upcoming.return_value = []
        docs = await svc.upcoming_documents("u1")
        assert docs == []
