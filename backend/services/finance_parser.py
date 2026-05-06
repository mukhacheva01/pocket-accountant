import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from shared.db.enums import FinanceRecordType


AMOUNT_PATTERN = re.compile(
    r"(?P<number>\d[\d\s]*[.,]?\d*)\s*(?P<suffix>к|k|тыс|т|млн|m)?",
    flags=re.IGNORECASE,
)

INCOME_CATEGORY_LABELS = {
    "services": "услуги",
    "goods": "товары",
    "rent": "аренда",
    "other": "прочее",
}

EXPENSE_CATEGORY_LABELS = {
    "rent": "аренда",
    "salary": "зарплата",
    "marketing": "реклама",
    "materials": "материалы",
    "taxes": "налоги и взносы",
    "transport": "транспорт",
    "communication": "связь",
    "other": "прочее",
}


@dataclass
class ParsedFinanceText:
    record_type: FinanceRecordType
    amount: Decimal
    category: str
    category_label: str
    confidence: float


class FinanceTextParser:
    INCOME_HINTS = ("доход", "приход", "получил", "оплата", "пришло", "поступление", "аванс")
    EXPENSE_HINTS = ("расход", "заплатил", "оплатил", "потратил", "списали", "купил")

    @staticmethod
    def _parse_amount(source_text: str) -> Optional[Decimal]:
        amount_match = AMOUNT_PATTERN.search(source_text.lower())
        if amount_match is None:
            return None

        raw_number = amount_match.group("number").replace(" ", "").replace(",", ".")
        amount = Decimal(raw_number)
        suffix = (amount_match.group("suffix") or "").lower()
        if suffix in {"к", "k", "тыс", "т"}:
            amount *= Decimal("1000")
        elif suffix in {"млн", "m"}:
            amount *= Decimal("1000000")
        return amount

    def parse(self, source_text: str) -> Optional[ParsedFinanceText]:
        normalized = source_text.lower()
        amount = self._parse_amount(normalized)
        if amount is None:
            return None
        if any(hint in normalized for hint in self.INCOME_HINTS):
            record_type = FinanceRecordType.INCOME
            category = self._classify_income(normalized)
            confidence = 0.82
        elif any(hint in normalized for hint in self.EXPENSE_HINTS):
            record_type = FinanceRecordType.EXPENSE
            category = self._classify_expense(normalized)
            confidence = 0.78
        else:
            return None

        category_label = (
            INCOME_CATEGORY_LABELS.get(category, category)
            if record_type == FinanceRecordType.INCOME
            else EXPENSE_CATEGORY_LABELS.get(category, category)
        )
        return ParsedFinanceText(
            record_type=record_type,
            amount=amount,
            category=category,
            category_label=category_label,
            confidence=confidence,
        )

    @staticmethod
    def _classify_income(normalized: str) -> str:
        if any(token in normalized for token in ("аренда", "сдал", "арендатор")):
            return "rent"
        if any(token in normalized for token in ("товар", "маркетплейс", "wb", "wildberries", "ozon", "продажа")):
            return "goods"
        if any(token in normalized for token in ("услуг", "клиент", "проект", "консультац", "разработк", "дизайн")):
            return "services"
        return "other"

    @staticmethod
    def _classify_expense(normalized: str) -> str:
        if any(token in normalized for token in ("аренда", "офис", "склад")):
            return "rent"
        if any(token in normalized for token in ("зарплат", "оклад", "сотрудник", "команда")):
            return "salary"
        if any(token in normalized for token in ("реклам", "таргет", "директ", "продвиж")):
            return "marketing"
        if any(token in normalized for token in ("материал", "сырье", "закупк", "фулфилмент", "упаков")):
            return "materials"
        if any(token in normalized for token in ("налог", "взнос", "енп", "страхов")):
            return "taxes"
        if any(token in normalized for token in ("доставка", "логист", "такси", "бензин", "транспорт")):
            return "transport"
        if any(token in normalized for token in ("интернет", "телефон", "связь", "crm")):
            return "communication"
        return "other"
