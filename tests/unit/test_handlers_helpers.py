"""Tests for helper functions in bot.handlers.__init__."""

from bot.handlers import (
    _entity_label,
    _tax_regime_label,
    _category_label,
    _contains_hint,
    _normalize_finance_text,
    _planned_entity_label,
    _format_records,
    ENTITY_TYPE_MAP,
    TAX_REGIME_MAP,
    REGIME_ACTIVITY_MAP,
    COUNTERPARTIES_MAP,
    MAIN_MENU_BUTTONS,
    AI_TOPIC_PROMPTS,
    PLANNED_ENTITY_TEXT,
)


class TestMaps:
    def test_entity_type_map(self):
        assert ENTITY_TYPE_MAP["ИП"] == "ip"
        assert ENTITY_TYPE_MAP["ООО"] == "ooo"
        assert ENTITY_TYPE_MAP["Самозанятый"] == "self_employed"

    def test_tax_regime_map(self):
        assert TAX_REGIME_MAP["УСН 6%"] == "usn_income"
        assert TAX_REGIME_MAP["ОСНО"] == "osno"
        assert TAX_REGIME_MAP["НПД"] == "npd"

    def test_regime_activity_map(self):
        assert REGIME_ACTIVITY_MAP["Услуги"] == "services"
        assert REGIME_ACTIVITY_MAP["Торговля"] == "trade"

    def test_counterparties_map(self):
        assert COUNTERPARTIES_MAP["Физлица"] == "individuals"
        assert COUNTERPARTIES_MAP["Юрлица/ИП"] == "business"

    def test_main_menu_buttons(self):
        assert "🏠 Главная" in MAIN_MENU_BUTTONS
        assert "❓ Помощь" in MAIN_MENU_BUTTONS

    def test_ai_topic_prompts(self):
        assert "ai_topic_calc" in AI_TOPIC_PROMPTS
        assert "налог" in AI_TOPIC_PROMPTS["ai_topic_calc"]

    def test_planned_entity_text(self):
        assert PLANNED_ENTITY_TEXT == "Пока не открыт"


class TestEntityLabel:
    def test_known(self):
        assert _entity_label("ip") == "ИП"
        assert _entity_label("ooo") == "ООО"

    def test_unknown(self):
        assert _entity_label("xxx") == "xxx"


class TestTaxRegimeLabel:
    def test_known(self):
        assert _tax_regime_label("usn_income") == "УСН 6%"
        assert _tax_regime_label("osno") == "ОСНО"

    def test_unknown(self):
        assert _tax_regime_label("yyy") == "yyy"


class TestCategoryLabel:
    def test_income(self):
        label = _category_label("income", "services")
        assert label == "Услуги"

    def test_expense(self):
        label = _category_label("expense", "marketing")
        assert label == "Маркетинг"

    def test_unknown(self):
        label = _category_label("income", "unknown_cat")
        assert label == "unknown_cat"


class TestContainsHint:
    def test_found(self):
        assert _contains_hint("получил 1000", ("доход", "получил"))

    def test_not_found(self):
        assert not _contains_hint("привет мир", ("доход", "получил"))


class TestNormalizeFinanceText:
    def test_income_with_hint(self):
        result = _normalize_finance_text("получил 5000", "income")
        assert result == "получил 5000"

    def test_income_without_hint(self):
        result = _normalize_finance_text("5000 за проект", "income")
        assert result.startswith("доход")

    def test_expense_with_hint(self):
        result = _normalize_finance_text("заплатил 1000", "expense")
        assert result == "заплатил 1000"

    def test_expense_without_hint(self):
        result = _normalize_finance_text("1000 за рекламу", "expense")
        assert result.startswith("расход")

    def test_empty(self):
        assert _normalize_finance_text("", "income") == ""

    def test_whitespace_stripped(self):
        result = _normalize_finance_text("  получил 5000  ", "income")
        assert result == "получил 5000"


class TestPlannedEntityLabel:
    def test_planning(self):
        assert _planned_entity_label({"reminder_settings": {"planning_entity": True}}) == "Пока не открыт"

    def test_not_planning(self):
        assert _planned_entity_label({"reminder_settings": {}}) is None


class TestFormatRecords:
    def test_empty(self):
        assert _format_records([]) == "Записей пока нет."

    def test_with_records(self):
        records = [
            {
                "record_type": "income",
                "amount": "5000",
                "category": "services",
                "operation_date": "2026-01-15",
            },
            {
                "record_type": "expense",
                "amount": "1000",
                "category": "marketing",
                "operation_date": "2026-01-16",
            },
        ]
        result = _format_records(records)
        assert "+" in result
        assert "-" in result
        assert "5000" in result
