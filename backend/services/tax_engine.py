import re
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from shared.db.enums import EntityType, TaxRegime


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_money(value: Decimal) -> str:
    normalized = _money(value)
    integer, _, fraction = f"{normalized:.2f}".partition(".")
    integer = f"{int(integer):,}".replace(",", " ")
    return f"{integer},{fraction}"


@dataclass
class TaxCalculationRequest:
    regime: str
    income: Decimal
    expenses: Decimal = Decimal("0")
    counterparties: Optional[str] = None
    patent_cost: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    has_employees: bool = False
    entity_type: Optional[EntityType] = None


@dataclass
class TaxCalculationResult:
    regime_label: str
    rate_label: str
    income: Decimal
    formula: str
    tax_amount: Decimal
    contributions: Decimal
    payable: Decimal
    deadline: str
    next_step: str
    notes: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            f"📊 Режим: {self.regime_label}",
            f"Ставка: {self.rate_label}",
            f"Доход: {_format_money(self.income)} ₽",
            f"Формула: {self.formula}",
            f"Налог ({self.rate_label}): {_format_money(self.tax_amount)} ₽",
            f"Взносы: {_format_money(self.contributions)} ₽",
            f"К уплате: {_format_money(self.payable)} ₽",
            f"Срок: {self.deadline}",
            f"Что делать: {self.next_step}",
        ]
        lines.extend(self.notes)
        return "\n".join(lines)


@dataclass
class TaxComparisonResult:
    recommendation: str
    summary: str
    comparisons: list[str]

    def render(self) -> str:
        return "\n".join(
            [
                f"Режим: {self.recommendation}",
                f"Ставка: {self.summary}",
                "Сумма: сравнение сделано по годовому доходу",
                "Что делать: выбери этот режим как базовый вариант и потом проверь детали по региону и видам деятельности.",
                *self.comparisons,
            ]
        )


@dataclass
class TaxParseResult:
    request: Optional[TaxCalculationRequest] = None
    question: Optional[str] = None


class TaxQueryParser:
    AMOUNT_PATTERN = re.compile(
        r"(?P<number>\d[\d\s]*[.,]?\d*)\s*(?P<suffix>к|k|тыс|т|млн|m)?",
        flags=re.IGNORECASE,
    )

    @classmethod
    def parse_amount(cls, raw_text: str) -> Optional[Decimal]:
        match = cls.AMOUNT_PATTERN.search(raw_text.lower())
        if match is None:
            return None
        amount = Decimal(match.group("number").replace(" ", "").replace(",", "."))
        suffix = (match.group("suffix") or "").lower()
        if suffix in {"к", "k", "тыс", "т"}:
            amount *= Decimal("1000")
        elif suffix in {"млн", "m"}:
            amount *= Decimal("1000000")
        return amount

    @classmethod
    def parse_named_amount(cls, text: str, *tokens: str) -> Optional[Decimal]:
        for token in tokens:
            pattern = re.compile(rf"{token}\D+(?P<chunk>\d[\d\s.,]*\s*(?:к|k|тыс|т|млн|m)?)", flags=re.IGNORECASE)
            match = pattern.search(text)
            if match is not None:
                amount = cls.parse_amount(match.group("chunk"))
                if amount is not None:
                    return amount
        return None

    @classmethod
    def looks_like_calculation_request(cls, text: str) -> bool:
        normalized = text.lower()
        calculator_hints = (
            "посчитай",
            "рассчитай",
            "сколько",
            "к уплате",
            "налог с",
            "налог при",
            "/calc",
        )
        regime_hints = ("нпд", "самозан", "усн", "осно", "патент", "псн")
        amount = cls.parse_amount(normalized)
        if any(hint in normalized for hint in calculator_hints):
            return True
        if amount is None:
            return False
        return any(hint in normalized for hint in regime_hints)

    @classmethod
    def parse(cls, text: str, profile: dict[str, object]) -> TaxParseResult:
        normalized = text.lower()
        regime = None
        if "нпд" in normalized or "самозан" in normalized:
            regime = "npd"
        elif "усн 15" in normalized or "доходы-расходы" in normalized or "доходы минус расходы" in normalized:
            regime = "usn15"
        elif "усн 6" in normalized or "усн доходы" in normalized:
            regime = "usn6"
        elif "осно" in normalized:
            regime = "osno"
        elif "патент" in normalized or "псн" in normalized:
            regime = "psn"
        elif profile.get("tax_regime") == TaxRegime.NPD.value:
            regime = "npd"
        elif profile.get("tax_regime") == TaxRegime.USN_INCOME.value:
            regime = "usn6"
        elif profile.get("tax_regime") == TaxRegime.USN_INCOME_EXPENSE.value:
            regime = "usn15"
        elif profile.get("tax_regime") == TaxRegime.OSNO.value:
            regime = "osno"

        if regime is None:
            return TaxParseResult()

        income = cls.parse_named_amount(normalized, "доход", "выручк", "получил", "заработал")
        if income is None:
            income = cls.parse_amount(normalized)
        if income is None:
            return TaxParseResult(question="Какую сумму дохода берем в расчет?")

        expenses = cls.parse_named_amount(normalized, "расход", "затрат", "расходы")
        if expenses is None:
            expenses = Decimal("0")

        counterparties = None
        if "физлиц" in normalized or "физлица" in normalized:
            counterparties = "individuals"
        elif "юрлиц" in normalized or "юрлица" in normalized or "ип" in normalized or "компан" in normalized:
            counterparties = "business"
        elif "смешан" in normalized:
            counterparties = "mixed"

        patent_cost = cls.parse_named_amount(normalized, "патент", "стоимость патента")
        vat_rate = None
        if "ндс 22" in normalized:
            vat_rate = Decimal("0.22")
        elif "ндс 10" in normalized:
            vat_rate = Decimal("0.10")
        elif "ндс 0" in normalized:
            vat_rate = Decimal("0.00")

        request = TaxCalculationRequest(
            regime=regime,
            income=income,
            expenses=expenses,
            counterparties=counterparties,
            patent_cost=patent_cost,
            vat_rate=vat_rate,
            has_employees=bool(profile.get("has_employees")),
            entity_type=EntityType(profile["entity_type"]) if profile.get("entity_type") else None,
        )

        if regime == "npd" and counterparties is None:
            return TaxParseResult(question="Доход считать от физлиц или от ИП/юрлиц?")
        if regime == "psn" and patent_cost is None:
            return TaxParseResult(question="Какая стоимость патента по твоему виду деятельности и региону?")
        if regime == "usn15" and expenses == Decimal("0") and "расход" not in normalized:
            return TaxParseResult(question="Какая сумма подтвержденных расходов за этот же период?")
        return TaxParseResult(request=request)


class TaxCalculatorService:
    FIXED_IP_CONTRIBUTIONS_2026 = Decimal("57390")
    NPD_LIMIT = Decimal("2400000")
    USN_LIMIT = Decimal("490500000")
    USN_VAT_EXEMPT_LIMIT = Decimal("20000000")
    USN_VAT_5_LIMIT = Decimal("272500000")
    PSN_LIMIT = Decimal("60000000")

    @classmethod
    def estimate_ip_contributions(cls, income: Decimal, entity_type: Optional[EntityType]) -> Decimal:
        if entity_type != EntityType.INDIVIDUAL_ENTREPRENEUR:
            return Decimal("0")
        additional = max(Decimal("0"), income - Decimal("300000")) * Decimal("0.01")
        return _money(cls.FIXED_IP_CONTRIBUTIONS_2026 + additional)

    @classmethod
    def calculate(cls, request: TaxCalculationRequest) -> TaxCalculationResult:
        if request.regime == "npd":
            return cls._calculate_npd(request)
        if request.regime == "usn6":
            return cls._calculate_usn_income(request)
        if request.regime == "usn15":
            return cls._calculate_usn_income_expense(request)
        if request.regime == "osno":
            return cls._calculate_osno(request)
        return cls._calculate_psn(request)

    @classmethod
    def compare_regimes(
        cls,
        *,
        activity: str,
        monthly_income: Decimal,
        has_employees: bool,
        counterparties: str,
        region: str,
    ) -> TaxComparisonResult:
        annual_income = monthly_income * Decimal("12")
        expense_ratio_map = {
            "services": Decimal("0.20"),
            "trade": Decimal("0.65"),
            "rent": Decimal("0.15"),
            "production": Decimal("0.70"),
            "other": Decimal("0.35"),
        }
        ratio = expense_ratio_map.get(activity, Decimal("0.35"))
        expenses = annual_income * ratio

        comparisons: list[tuple[str, Decimal]] = []
        if not has_employees and annual_income <= cls.NPD_LIMIT:
            npd_rate = Decimal("0.04") if counterparties == "individuals" else Decimal("0.06")
            comparisons.append(("НПД", _money(annual_income * npd_rate)))

        usn6 = cls._calculate_usn_income(
            TaxCalculationRequest(
                regime="usn6",
                income=annual_income,
                entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
                has_employees=has_employees,
            )
        )
        usn15 = cls._calculate_usn_income_expense(
            TaxCalculationRequest(
                regime="usn15",
                income=annual_income,
                expenses=expenses,
                entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
                has_employees=has_employees,
            )
        )
        comparisons.append(("УСН 6%", usn6.payable))
        comparisons.append(("УСН 15%", usn15.payable))

        ordered = sorted(comparisons, key=lambda item: item[1])
        best_name, best_value = ordered[0]
        comparison_lines = []
        for name, value in ordered:
            if name == best_name:
                comparison_lines.append(f"{name}: {_format_money(value)} ₽ в год")
                continue
            saving = _money(value - best_value)
            comparison_lines.append(
                f"{name}: {_format_money(value)} ₽ в год, дороже на {_format_money(saving)} ₽"
            )
        comparison_lines.append(
            f"Регион: {region}. ПСН не сравнивал в рублях, потому что нужна точная стоимость патента по региону."
        )
        return TaxComparisonResult(
            recommendation=best_name,
            summary=f"минимальная расчетная нагрузка по сравнению с альтернативами; расходы приняты как {int(ratio * 100)}% выручки",
            comparisons=comparison_lines,
        )

    @classmethod
    def _calculate_npd(cls, request: TaxCalculationRequest) -> TaxCalculationResult:
        rate = Decimal("0.04") if request.counterparties == "individuals" else Decimal("0.06")
        tax = _money(request.income * rate)
        notes = [
            "Что делать дальше: проверь лимит 2 400 000 ₽ в год и учти вычет 10 000 ₽, если он у тебя еще не исчерпан.",
            "Актуально на 2026 год, сверь с nalog.ru",
        ]
        return TaxCalculationResult(
            regime_label="НПД",
            rate_label=f"{int(rate * 100)}%",
            income=request.income,
            formula=f"{_format_money(request.income)} × {int(rate * 100)}%",
            tax_amount=tax,
            contributions=Decimal("0"),
            payable=tax,
            deadline="до 28-го числа следующего месяца",
            next_step="Проверь начисление в приложении «Мой налог» и оплати до дедлайна.",
            notes=notes,
        )

    @classmethod
    def _calculate_usn_income(cls, request: TaxCalculationRequest) -> TaxCalculationResult:
        rate = Decimal("0.06")
        base_tax = _money(request.income * rate)
        contributions = cls.estimate_ip_contributions(request.income, request.entity_type)
        max_reduction = base_tax if not request.has_employees else _money(base_tax * Decimal("0.5"))
        payable = _money(max(Decimal("0"), base_tax - min(contributions, max_reduction)))
        vat_note = cls._usn_vat_note(request.income)
        return TaxCalculationResult(
            regime_label="УСН «Доходы»",
            rate_label="6%",
            income=request.income,
            formula=(
                f"{_format_money(request.income)} × 6%"
                f" - уменьшение на взносы до {'50%' if request.has_employees else '100%'} налога"
            ),
            tax_amount=base_tax,
            contributions=contributions,
            payable=payable,
            deadline="аванс до 28-го числа после квартала, итоговый платеж по году после сдачи декларации",
            next_step="Подготовь аванс или итоговый платеж и проверь, что взносы уплачены и учтены в уменьшении.",
            notes=[vat_note, "Актуально на 2026 год, сверь с nalog.ru"],
        )

    @classmethod
    def _calculate_usn_income_expense(cls, request: TaxCalculationRequest) -> TaxCalculationResult:
        rate = Decimal("0.15")
        contributions = cls.estimate_ip_contributions(request.income, request.entity_type)
        tax_base = max(Decimal("0"), request.income - request.expenses - contributions)
        regular_tax = _money(tax_base * rate)
        minimum_tax = _money(request.income * Decimal("0.01"))
        payable = regular_tax if regular_tax >= minimum_tax else minimum_tax
        return TaxCalculationResult(
            regime_label="УСН «Доходы минус расходы»",
            rate_label="15%",
            income=request.income,
            formula=(
                f"({_format_money(request.income)} - {_format_money(request.expenses)} - {_format_money(contributions)}) × 15%"
                f", минимум 1% от дохода = {_format_money(minimum_tax)}"
            ),
            tax_amount=regular_tax,
            contributions=contributions,
            payable=payable,
            deadline="аванс до 28-го числа после квартала, итоговый платеж по году после сдачи декларации",
            next_step="Проверь подтвержденные расходы и сравни расчет с минимальным налогом 1% от дохода.",
            notes=[cls._usn_vat_note(request.income), "Актуально на 2026 год, сверь с nalog.ru"],
        )

    @classmethod
    def _calculate_osno(cls, request: TaxCalculationRequest) -> TaxCalculationResult:
        contributions = cls.estimate_ip_contributions(request.income, request.entity_type)
        base = max(Decimal("0"), request.income - request.expenses - contributions)
        ndfl = cls._progressive_ndfl(base)
        vat = _money(request.income * request.vat_rate) if request.vat_rate is not None else Decimal("0")
        rate_label = "НДФЛ 13/15/18/20%"
        if request.vat_rate is not None:
            rate_label += f" + НДС {int(request.vat_rate * 100)}%"
        notes = ["Актуально на 2026 год, сверь с nalog.ru"]
        if request.vat_rate is None:
            notes.append("НДС в расчет не включен. Если нужен расчет с НДС, укажи ставку 22%, 10% или 0%.")
        return TaxCalculationResult(
            regime_label="ОСНО",
            rate_label=rate_label,
            income=request.income,
            formula=(
                f"НДФЛ с базы {_format_money(base)} ₽ по прогрессивной шкале"
                + (f" + НДС {_format_money(request.income)} × {int(request.vat_rate * 100)}%" if request.vat_rate is not None else "")
            ),
            tax_amount=_money(ndfl + vat),
            contributions=contributions,
            payable=_money(ndfl + vat),
            deadline="НДФЛ и НДС платятся по разным срокам, ориентируйся на период и вид обязательства",
            next_step="Уточни период и нужен ли отдельный расчет НДС, если считаем ОСНО полностью.",
            notes=notes,
        )

    @classmethod
    def _calculate_psn(cls, request: TaxCalculationRequest) -> TaxCalculationResult:
        patent_cost = _money(request.patent_cost or Decimal("0"))
        notes = ["Проверь региональный расчет стоимости патента и лимит дохода.", "Актуально на 2026 год, сверь с nalog.ru"]
        if request.income > cls.PSN_LIMIT:
            notes.insert(0, "Лимит для ПСН превышен, режим применять нельзя.")
        return TaxCalculationResult(
            regime_label="Патент",
            rate_label="фиксированная стоимость",
            income=request.income,
            formula=f"Стоимость патента = {_format_money(patent_cost)} ₽",
            tax_amount=patent_cost,
            contributions=Decimal("0"),
            payable=patent_cost,
            deadline="срок зависит от длительности патента",
            next_step="Проверь стоимость патента по региону и виду деятельности и оплату по графику патента.",
            notes=notes,
        )

    @classmethod
    def _progressive_ndfl(cls, base: Decimal) -> Decimal:
        brackets = [
            (Decimal("2400000"), Decimal("0.13")),
            (Decimal("5000000"), Decimal("0.15")),
            (Decimal("20000000"), Decimal("0.18")),
            (Decimal("999999999999"), Decimal("0.20")),
        ]
        previous_limit = Decimal("0")
        total = Decimal("0")
        remaining = base
        for limit, rate in brackets:
            if remaining <= 0:
                break
            taxable = min(remaining, limit - previous_limit)
            total += taxable * rate
            remaining -= taxable
            previous_limit = limit
        return _money(total)

    @classmethod
    def _usn_vat_note(cls, income: Decimal) -> str:
        if income <= cls.USN_VAT_EXEMPT_LIMIT:
            return "НДС: освобождение при доходе до 20 млн ₽."
        if income <= cls.USN_VAT_5_LIMIT:
            return "НДС: возможна ставка 5% в диапазоне 20-272,5 млн ₽."
        if income <= cls.USN_LIMIT:
            return "НДС: возможна ставка 7% в диапазоне 272,5-490,5 млн ₽."
        return "Лимит УСН превышен, режим нужно пересмотреть."
