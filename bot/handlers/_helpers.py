"""Shared helpers for handler modules."""

from __future__ import annotations

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup

from bot.backend_client import BackendClient
from shared.db.enums import EntityType, FinanceRecordType, TaxRegime

logger = logging.getLogger(__name__)

PLANNED_ENTITY_TEXT = "Пока не открыт"

ENTITY_TYPE_MAP = {
    "ИП": EntityType.INDIVIDUAL_ENTREPRENEUR,
    "ООО": EntityType.LIMITED_COMPANY,
    "Самозанятый": EntityType.SELF_EMPLOYED,
}

TAX_REGIME_MAP = {
    "УСН 6%": TaxRegime.USN_INCOME,
    "УСН доходы-расходы": TaxRegime.USN_INCOME_EXPENSE,
    "ОСНО": TaxRegime.OSNO,
    "НПД": TaxRegime.NPD,
}

ENTITY_TYPE_LABELS = {
    EntityType.INDIVIDUAL_ENTREPRENEUR.value: "ИП",
    EntityType.LIMITED_COMPANY.value: "ООО",
    EntityType.SELF_EMPLOYED.value: "Самозанятый",
}

TAX_REGIME_LABELS = {
    TaxRegime.USN_INCOME.value: "УСН 6%",
    TaxRegime.USN_INCOME_EXPENSE.value: "УСН доходы-расходы",
    TaxRegime.OSNO.value: "ОСНО",
    TaxRegime.NPD.value: "НПД",
}

REGIME_ACTIVITY_MAP = {
    "Услуги": "services",
    "Торговля": "trade",
    "Аренда": "rent",
    "Производство": "production",
    "Другое": "other",
}

COUNTERPARTIES_MAP = {
    "Физлица": "individuals",
    "Юрлица/ИП": "business",
    "Смешанно": "mixed",
}

MAIN_MENU_BUTTONS = {
    "🏠 Главная",
    "👤 Профиль",
    "💬 AI Консультация",
    "📅 События",
    "📋 Что подать",
    "💰 Добавить доход",
    "💸 Добавить расход",
    "📊 Финансы",
    "🔍 Подобрать режим",
    "⭐ Подписка",
    "❓ Помощь",
    "🗑 Новый диалог",
    "Отмена",
}

AI_TOPIC_PROMPTS = {
    "ai_topic_calc": "Как рассчитать налог? Расскажи основные формулы для моего режима.",
    "ai_topic_deadlines": "Какие ближайшие сроки сдачи отчётности и уплаты налогов для моего профиля?",
    "ai_topic_reports": "Какую отчётность я должен сдавать и в какие сроки?",
    "ai_topic_deductions": "Как уменьшить налог на страховые взносы? Какие вычеты мне доступны?",
}

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

PLAN_DETAILS = {
    "basic": {"label": "Базовый", "days": 30, "ai_limit": 50},
    "pro": {"label": "Про", "days": 30, "ai_limit": 999},
    "annual": {"label": "Годовой", "days": 365, "ai_limit": 999},
}


def get_client() -> BackendClient:
    from shared.config import get_settings
    settings = get_settings()
    base_url = getattr(settings, "backend_base_url", "http://backend:8080")
    return BackendClient(base_url=base_url)


def entity_label(value: str) -> str:
    return ENTITY_TYPE_LABELS.get(value, value)


def tax_regime_label(value: str) -> str:
    return TAX_REGIME_LABELS.get(value, value)


def category_label(record_type: FinanceRecordType | str, category: str) -> str:
    if record_type == FinanceRecordType.INCOME or record_type == "income":
        return INCOME_CATEGORY_LABELS.get(category, category)
    return EXPENSE_CATEGORY_LABELS.get(category, category)


def contains_hint(source_text: str, hints: tuple[str, ...]) -> bool:
    normalized = source_text.lower()
    return any(hint in normalized for hint in hints)


def normalize_finance_text(source_text: str, record_kind: str) -> str:
    source_text = source_text.strip()
    if not source_text:
        return source_text
    if record_kind == "income":
        hints = ("доход", "приход", "получил", "оплата", "поступление")
        return source_text if contains_hint(source_text, hints) else f"доход {source_text}"
    hints = ("расход", "заплатил", "оплатил", "потратил", "списали")
    return source_text if contains_hint(source_text, hints) else f"расход {source_text}"


def planned_entity_label(profile) -> str | None:
    if profile is None:
        return None
    if hasattr(profile, "reminder_settings"):
        reminder_settings = profile.reminder_settings
    else:
        reminder_settings = (profile.get("reminder_settings") if isinstance(profile, dict) else {}) or {}
    if isinstance(reminder_settings, dict) and reminder_settings.get("planning_entity"):
        return "Пока не открыт"
    return None


def format_records(records) -> str:
    if not records:
        return "Записей пока нет."
    lines = []
    for record in records:
        if isinstance(record, dict):
            rt = record.get("record_type", "")
            sign = "+" if rt == FinanceRecordType.INCOME or rt == "income" else "-"
            label = category_label(rt, record.get("category", ""))
            op_date = record.get("operation_date", "")
            amount = record.get("amount", "")
        else:
            sign = "+" if record.record_type == FinanceRecordType.INCOME else "-"
            label = category_label(record.record_type, record.category)
            op_date = record.operation_date.isoformat() if hasattr(record.operation_date, "isoformat") else str(record.operation_date)
            amount = record.amount
        lines.append(f"{op_date} | {sign}{amount} ₽ | {label}")
    return "\n".join(lines)


def format_money(value) -> str:
    from decimal import Decimal
    if isinstance(value, str):
        value = Decimal(value)
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


async def respond(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None,
    *,
    edit: bool = False,
    parse_mode: str = "Markdown",
) -> None:
    if edit and not isinstance(reply_markup, ReplyKeyboardMarkup):
        try:
            await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except TelegramBadRequest:
            pass
    await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
