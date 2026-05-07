"""Tests for backend.services.finance_parser."""

from decimal import Decimal

import pytest

from backend.services.finance_parser import FinanceTextParser
from shared.db.enums import FinanceRecordType


@pytest.fixture()
def parser():
    return FinanceTextParser()


class TestParseAmount:
    def test_plain_number(self, parser):
        parsed = parser.parse("получил 50000 от клиента")
        assert parsed is not None
        assert parsed.amount == Decimal("50000")

    def test_k_suffix(self, parser):
        parsed = parser.parse("заплатил 12к за рекламу")
        assert parsed is not None
        assert parsed.amount == Decimal("12000")

    def test_тыс_suffix(self, parser):
        parsed = parser.parse("потратил 5тыс на материалы")
        assert parsed is not None
        assert parsed.amount == Decimal("5000")

    def test_млн_suffix(self, parser):
        parsed = parser.parse("доход 1.5млн за год")
        assert parsed is not None
        assert parsed.amount == Decimal("1500000")

    def test_m_suffix(self, parser):
        parsed = parser.parse("доход 2m за год")
        assert parsed is not None
        assert parsed.amount == Decimal("2000000")

    def test_comma_decimal(self, parser):
        parsed = parser.parse("получил 1 500,50 за услуги")
        assert parsed is not None
        assert parsed.amount == Decimal("1500.50")


class TestRecordType:
    def test_income_hints(self, parser):
        for phrase in ["получил 1000 за проект", "доход 5000 от клиента", "поступление 3000"]:
            parsed = parser.parse(phrase)
            assert parsed is not None, f"Failed for: {phrase}"
            assert parsed.record_type == FinanceRecordType.INCOME

    def test_expense_hints(self, parser):
        for phrase in ["заплатил 500 за интернет", "потратил 3к на такси", "купил 2000 материалов"]:
            parsed = parser.parse(phrase)
            assert parsed is not None, f"Failed for: {phrase}"
            assert parsed.record_type == FinanceRecordType.EXPENSE

    def test_no_hint_returns_none(self, parser):
        assert parser.parse("привет 1000") is None

    def test_no_amount_returns_none(self, parser):
        assert parser.parse("заплатил за рекламу") is None


class TestIncomeCategories:
    def test_services(self, parser):
        parsed = parser.parse("получил 50000 от клиента за услуги")
        assert parsed.category == "services"
        assert parsed.category_label == "услуги"

    def test_goods(self, parser):
        parsed = parser.parse("доход 100000 с ozon за продажу товаров")
        assert parsed.category == "goods"
        assert parsed.category_label == "товары"

    def test_rent(self, parser):
        parsed = parser.parse("получил 30000 от арендатора")
        assert parsed.category == "rent"
        assert parsed.category_label == "аренда"

    def test_other(self, parser):
        parsed = parser.parse("получил 5000 возврат")
        assert parsed.category == "other"
        assert parsed.category_label == "прочее"


class TestExpenseCategories:
    def test_marketing(self, parser):
        parsed = parser.parse("заплатил 12к за рекламу")
        assert parsed.category == "marketing"
        assert parsed.category_label == "реклама"

    def test_salary(self, parser):
        parsed = parser.parse("заплатил 80000 зарплату сотруднику")
        assert parsed.category == "salary"
        assert parsed.category_label == "зарплата"

    def test_rent(self, parser):
        parsed = parser.parse("оплатил 25000 аренду офиса")
        assert parsed.category == "rent"
        assert parsed.category_label == "аренда"

    def test_materials(self, parser):
        parsed = parser.parse("купил 10000 материалов")
        assert parsed.category == "materials"
        assert parsed.category_label == "материалы"

    def test_taxes(self, parser):
        parsed = parser.parse("заплатил 15000 налоги")
        assert parsed.category == "taxes"
        assert parsed.category_label == "налоги и взносы"

    def test_transport(self, parser):
        parsed = parser.parse("потратил 3000 на такси")
        assert parsed.category == "transport"
        assert parsed.category_label == "транспорт"

    def test_communication(self, parser):
        parsed = parser.parse("оплатил 2000 за интернет")
        assert parsed.category == "communication"
        assert parsed.category_label == "связь"

    def test_other(self, parser):
        parsed = parser.parse("потратил 1000 на что-то")
        assert parsed.category == "other"
        assert parsed.category_label == "прочее"


def test_confidence_values(parser):
    income = parser.parse("получил 1000 за услуги")
    assert income.confidence == 0.82
    expense = parser.parse("заплатил 500 за рекламу")
    assert expense.confidence == 0.78
