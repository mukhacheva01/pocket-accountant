import unittest
from decimal import Decimal

from shared.db.enums import EntityType
from backend.services.finance_parser import FinanceTextParser
from backend.services.tax_engine import TaxCalculationRequest, TaxCalculatorService, TaxQueryParser


class FinanceAndTaxTests(unittest.TestCase):
    def test_finance_parser_handles_k_suffix_and_marketing_category(self) -> None:
        parser = FinanceTextParser()
        parsed = parser.parse("заплатил 12к за рекламу")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.amount, Decimal("12000"))
        self.assertEqual(parsed.category, "marketing")
        self.assertEqual(parsed.category_label, "реклама")

    def test_finance_parser_detects_services_income(self) -> None:
        parser = FinanceTextParser()
        parsed = parser.parse("получил 50000 от клиента за услуги")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.category, "services")
        self.assertEqual(parsed.category_label, "услуги")

    def test_tax_parser_requests_counterparty_for_npd(self) -> None:
        parsed = TaxQueryParser.parse("посчитай нпд с дохода 100000", {"tax_regime": None, "entity_type": None, "has_employees": False})
        self.assertEqual(parsed.question, "Доход считать от физлиц или от ИП/юрлиц?")

    def test_tax_parser_does_not_treat_deadline_question_as_calculation(self) -> None:
        self.assertFalse(TaxQueryParser.looks_like_calculation_request("когда платить усн?"))

    def test_usn_income_calculation_applies_ip_contribution_reduction(self) -> None:
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(
                regime="usn6",
                income=Decimal("500000"),
                entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
                has_employees=False,
            )
        )
        self.assertEqual(result.tax_amount, Decimal("30000.00"))
        self.assertEqual(result.payable, Decimal("0.00"))

    def test_usn_income_expense_uses_minimum_tax(self) -> None:
        result = TaxCalculatorService.calculate(
            TaxCalculationRequest(
                regime="usn15",
                income=Decimal("1000000"),
                expenses=Decimal("990000"),
                entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
                has_employees=False,
            )
        )
        self.assertEqual(result.payable, Decimal("10000.00"))


if __name__ == "__main__":
    unittest.main()
