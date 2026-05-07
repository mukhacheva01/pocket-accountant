"""Tests for backend.services.tax_engine — TaxQueryParser + TaxCalculatorService."""

from decimal import Decimal


from shared.db.enums import EntityType
from backend.services.tax_engine import (
    TaxCalculationRequest,
    TaxCalculatorService,
    TaxComparisonResult,
    TaxQueryParser,
    _format_money,
    _money,
)


# --- helpers ---


class TestFormatMoney:
    def test_integer(self):
        assert _format_money(Decimal("1000")) == "1 000,00"

    def test_fraction(self):
        assert _format_money(Decimal("1234.5")) == "1 234,50"

    def test_large(self):
        assert _format_money(Decimal("1234567.89")) == "1 234 567,89"

    def test_zero(self):
        assert _format_money(Decimal("0")) == "0,00"


class TestMoney:
    def test_rounds_half_up(self):
        assert _money(Decimal("1.235")) == Decimal("1.24")
        assert _money(Decimal("1.234")) == Decimal("1.23")


# --- TaxQueryParser ---


class TestTaxQueryParser:
    def test_parse_amount_plain(self):
        assert TaxQueryParser.parse_amount("100000") == Decimal("100000")

    def test_parse_amount_k(self):
        assert TaxQueryParser.parse_amount("15к") == Decimal("15000")

    def test_parse_amount_m(self):
        assert TaxQueryParser.parse_amount("2млн") == Decimal("2000000")

    def test_parse_amount_none(self):
        assert TaxQueryParser.parse_amount("abc") is None

    def test_looks_like_calculation_positive(self):
        assert TaxQueryParser.looks_like_calculation_request("посчитай налог с 100000")
        assert TaxQueryParser.looks_like_calculation_request("сколько платить усн с 500к")

    def test_looks_like_calculation_negative(self):
        assert not TaxQueryParser.looks_like_calculation_request("когда платить усн?")

    def test_parse_npd_asks_counterparty(self):
        result = TaxQueryParser.parse("посчитай нпд с дохода 100000", {"tax_regime": None, "entity_type": None, "has_employees": False})
        assert result.question == "Доход считать от физлиц или от ИП/юрлиц?"

    def test_parse_npd_with_counterparty(self):
        result = TaxQueryParser.parse("нпд доход 100000 от физлиц", {"tax_regime": None, "entity_type": None, "has_employees": False})
        assert result.request is not None
        assert result.request.regime == "npd"
        assert result.request.counterparties == "individuals"

    def test_parse_usn6_from_text(self):
        result = TaxQueryParser.parse("усн 6 доход 500000", {"entity_type": "ip", "has_employees": False})
        assert result.request is not None
        assert result.request.regime == "usn6"

    def test_parse_usn15_asks_expenses(self):
        result = TaxQueryParser.parse("усн 15 доход 1000000", {"entity_type": "ip", "has_employees": False})
        assert result.question == "Какая сумма подтвержденных расходов за этот же период?"

    def test_parse_usn15_with_expenses(self):
        result = TaxQueryParser.parse("усн 15 доход 1000000 расходы 600000", {"entity_type": "ip", "has_employees": False})
        assert result.request is not None
        assert result.request.expenses == Decimal("600000")

    def test_parse_osno(self):
        result = TaxQueryParser.parse("осно доход 3000000", {"entity_type": "ip", "has_employees": False})
        assert result.request is not None
        assert result.request.regime == "osno"

    def test_parse_psn_asks_patent_cost(self):
        result = TaxQueryParser.parse("псн посчитай доход 1000000", {"entity_type": "ip", "has_employees": False})
        assert result.question == "Какая стоимость патента по твоему виду деятельности и региону?"

    def test_parse_no_regime_returns_empty(self):
        result = TaxQueryParser.parse("сколько налог?", {"tax_regime": None, "entity_type": None, "has_employees": False})
        assert result.request is None
        assert result.question is None

    def test_parse_no_amount_asks(self):
        result = TaxQueryParser.parse("усн доходы посчитай", {"entity_type": "ip", "has_employees": False})
        assert result.question == "Какую сумму дохода берем в расчет?"

    def test_parse_vat_rates(self):
        result = TaxQueryParser.parse("осно доход 5000000 ндс 22", {"entity_type": "ip", "has_employees": False})
        assert result.request.vat_rate == Decimal("0.22")

    def test_parse_regime_from_profile(self):
        result = TaxQueryParser.parse("посчитай доход 100000", {"tax_regime": "npd", "entity_type": None, "has_employees": False})
        assert result.question == "Доход считать от физлиц или от ИП/юрлиц?"

    def test_parse_counterparties_business(self):
        result = TaxQueryParser.parse("нпд доход 100000 от юрлиц", {"tax_regime": None, "entity_type": None, "has_employees": False})
        assert result.request.counterparties == "business"

    def test_parse_named_amount(self):
        val = TaxQueryParser.parse_named_amount("доход 250к", "доход")
        assert val == Decimal("250000")


# --- TaxCalculatorService ---


class TestTaxCalculatorService:
    def test_npd_individuals(self):
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(regime="npd", income=Decimal("100000"), counterparties="individuals")
        )
        assert result.regime_label == "НПД"
        assert result.tax_amount == Decimal("4000.00")
        assert result.payable == Decimal("4000.00")

    def test_npd_business(self):
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(regime="npd", income=Decimal("100000"), counterparties="business")
        )
        assert result.tax_amount == Decimal("6000.00")

    def test_usn_income_ip_no_employees(self):
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(
                regime="usn6",
                income=Decimal("500000"),
                entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
                has_employees=False,
            )
        )
        assert result.tax_amount == Decimal("30000.00")
        assert result.payable == Decimal("0.00")

    def test_usn_income_ip_with_employees(self):
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(
                regime="usn6",
                income=Decimal("500000"),
                entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
                has_employees=True,
            )
        )
        assert result.tax_amount == Decimal("30000.00")
        assert result.payable == Decimal("15000.00")

    def test_usn_income_expense_minimum_tax(self):
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(
                regime="usn15",
                income=Decimal("1000000"),
                expenses=Decimal("990000"),
                entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
                has_employees=False,
            )
        )
        assert result.payable == Decimal("10000.00")

    def test_usn_income_expense_regular_tax(self):
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(
                regime="usn15",
                income=Decimal("1000000"),
                expenses=Decimal("500000"),
                entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
                has_employees=False,
            )
        )
        assert result.payable > Decimal("10000.00")

    def test_osno_basic(self):
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(
                regime="osno",
                income=Decimal("1000000"),
                entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
            )
        )
        assert result.regime_label == "ОСНО"
        assert result.payable > 0

    def test_osno_with_vat(self):
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(
                regime="osno",
                income=Decimal("1000000"),
                vat_rate=Decimal("0.22"),
                entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
            )
        )
        assert result.tax_amount > Decimal("220000")

    def test_psn_basic(self):
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(
                regime="psn",
                income=Decimal("1000000"),
                patent_cost=Decimal("30000"),
            )
        )
        assert result.payable == Decimal("30000.00")
        assert result.regime_label == "Патент"

    def test_psn_exceeds_limit(self):
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(
                regime="psn",
                income=Decimal("70000000"),
                patent_cost=Decimal("30000"),
            )
        )
        assert any("Лимит" in note for note in result.notes)

    def test_estimate_ip_contributions_ip(self):
        c = TaxCalculatorService.estimate_ip_contributions(Decimal("500000"), EntityType.INDIVIDUAL_ENTREPRENEUR)
        expected = _money(Decimal("57390") + Decimal("2000"))
        assert c == expected

    def test_estimate_ip_contributions_non_ip(self):
        c = TaxCalculatorService.estimate_ip_contributions(Decimal("500000"), EntityType.LIMITED_COMPANY)
        assert c == Decimal("0")

    def test_progressive_ndfl(self):
        result = TaxCalculatorService._progressive_ndfl(Decimal("3000000"))
        bracket1 = _money(Decimal("2400000") * Decimal("0.13"))
        bracket2 = _money(Decimal("600000") * Decimal("0.15"))
        assert result == _money(bracket1 + bracket2)

    def test_usn_vat_note_exempt(self):
        note = TaxCalculatorService._usn_vat_note(Decimal("10000000"))
        assert "освобождение" in note

    def test_usn_vat_note_5_percent(self):
        note = TaxCalculatorService._usn_vat_note(Decimal("100000000"))
        assert "5%" in note

    def test_usn_vat_note_7_percent(self):
        note = TaxCalculatorService._usn_vat_note(Decimal("400000000"))
        assert "7%" in note

    def test_usn_vat_note_exceeded(self):
        note = TaxCalculatorService._usn_vat_note(Decimal("500000000"))
        assert "превышен" in note

    def test_render_output(self):
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(regime="npd", income=Decimal("100000"), counterparties="individuals")
        )
        rendered = result.render()
        assert "НПД" in rendered
        assert "4 000,00" in rendered

    def test_compare_regimes(self):
        result = TaxCalculatorService.compare_regimes(
            activity="services",
            monthly_income=Decimal("100000"),
            has_employees=False,
            counterparties="individuals",
            region="Moscow",
        )
        assert isinstance(result, TaxComparisonResult)
        assert result.recommendation
        assert len(result.comparisons) > 0
        rendered = result.render()
        assert "Режим:" in rendered

    def test_compare_regimes_no_npd_with_employees(self):
        result = TaxCalculatorService.compare_regimes(
            activity="services",
            monthly_income=Decimal("100000"),
            has_employees=True,
            counterparties="individuals",
            region="Moscow",
        )
        assert not any("НПД" in c for c in result.comparisons)
