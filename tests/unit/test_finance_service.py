"""Tests for backend.services.finance."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from backend.services.finance import FinanceService
from backend.services.finance_parser import FinanceTextParser


@pytest.fixture()
def svc():
    repo = AsyncMock()
    parser = FinanceTextParser()
    return FinanceService(repo, parser)


class TestAddFromText:
    async def test_income(self, svc):
        svc.repository.add_record.return_value = "record"
        result = await svc.add_from_text("u1", "получил 5000 от клиента за услуги")
        svc.repository.add_record.assert_awaited_once()
        assert result == "record"

    async def test_invalid_text_raises(self, svc):
        with pytest.raises(ValueError, match="Unable to classify"):
            await svc.add_from_text("u1", "привет")


class TestReport:
    async def test_report(self, svc):
        svc.repository.summarize_period.return_value = {"income": Decimal("100"), "expense": Decimal("40")}
        svc.repository.top_expense_categories.return_value = [("marketing", Decimal("20"))]
        result = await svc.report("u1", date(2026, 1, 1), date(2026, 1, 31))
        assert result["profit"] == Decimal("60")
        assert result["top_expenses"] == [("marketing", Decimal("20"))]


class TestBalance:
    async def test_balance(self, svc):
        svc.repository.summarize_period.return_value = {"income": Decimal("200"), "expense": Decimal("50")}
        svc.repository.top_expense_categories.return_value = []
        result = await svc.balance("u1")
        assert result["balance"] == Decimal("150")
        assert result["income"] == Decimal("200")


class TestListRecords:
    async def test_delegates(self, svc):
        svc.repository.list_records.return_value = []
        result = await svc.list_records("u1", limit=5)
        svc.repository.list_records.assert_awaited_once()
        assert result == []
