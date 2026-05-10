"""Shared constants, maps, and helper functions used across handler modules."""

import logging
from datetime import date, timedelta

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    User as TelegramUser,
)

from bot.keyboards import (
    documents_shortcuts_keyboard,
    event_actions_keyboard,
    finance_shortcuts_keyboard,
    help_shortcuts_keyboard,
    laws_shortcuts_keyboard,
    main_menu_keyboard,
    onboarding_entity_type_keyboard,
    profile_shortcuts_keyboard,
    reminders_shortcuts_keyboard,
    section_shortcuts_keyboard,
    settings_shortcuts_keyboard,
    subscription_keyboard,
    subscription_manage_keyboard,
)
from bot.messages import (
    help_text,
    paywall_text,
    referral_text,
    subscription_status_text,
    welcome_text,
)
from shared.config import get_settings

logger = logging.getLogger(__name__)

PLANNED_ENTITY_TEXT = "Пока не открыт"

ENTITY_TYPE_MAP = {
    "ИП": "ip",
    "ООО": "ooo",
    "Самозанятый": "self_employed",
}

TAX_REGIME_MAP = {
    "УСН 6%": "usn_income",
    "УСН доходы-расходы": "usn_income_expense",
    "ОСНО": "osno",
    "НПД": "npd",
}

ENTITY_TYPE_LABELS = {
    "ip": "ИП",
    "ooo": "ООО",
    "self_employed": "Самозанятый",
}

TAX_REGIME_LABELS = {
    "usn_income": "УСН 6%",
    "usn_income_expense": "УСН доходы-расходы",
    "osno": "ОСНО",
    "npd": "НПД",
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
    "sales": "Продажи",
    "services": "Услуги",
    "rent": "Аренда",
    "marketplace": "Маркетплейс",
    "investment": "Инвестиции",
    "other": "Прочее",
}

EXPENSE_CATEGORY_LABELS = {
    "salary": "Зарплата",
    "rent": "Аренда",
    "supplies": "Закупки",
    "tax": "Налоги",
    "insurance": "Страхование",
    "marketing": "Маркетинг",
    "transport": "Транспорт",
    "communication": "Связь",
    "other": "Прочее",
}


def _entity_label(value: str) -> str:
    return ENTITY_TYPE_LABELS.get(value, value)


def _tax_regime_label(value: str) -> str:
    return TAX_REGIME_LABELS.get(value, value)


def _category_label(record_type: str, category: str) -> str:
    if record_type == "income":
        return INCOME_CATEGORY_LABELS.get(category, category)
    return EXPENSE_CATEGORY_LABELS.get(category, category)


def _contains_hint(source_text: str, hints: tuple[str, ...]) -> bool:
    normalized = source_text.lower()
    return any(hint in normalized for hint in hints)


def _normalize_finance_text(source_text: str, record_kind: str) -> str:
    source_text = source_text.strip()
    if not source_text:
        return source_text
    if record_kind == "income":
        hints = ("доход", "приход", "получил", "оплата", "поступление")
        return source_text if _contains_hint(source_text, hints) else f"доход {source_text}"
    hints = ("расход", "заплатил", "оплатил", "потратил", "списали")
    return source_text if _contains_hint(source_text, hints) else f"расход {source_text}"


def _planned_entity_label(profile: dict) -> str | None:
    rs = profile.get("reminder_settings") or {}
    if rs.get("planning_entity"):
        return "Пока не открыт"
    return None


def _format_records(records: list[dict]) -> str:
    if not records:
        return "Записей пока нет."
    lines = []
    for record in records:
        sign = "+" if record["record_type"] == "income" else "-"
        label = _category_label(record["record_type"], record["category"])
        lines.append(f"{record['operation_date']} | {sign}{record['amount']} ₽ | {label}")
    return "\n".join(lines)


def _format_money(value) -> str:
    return f"{float(value):,.2f}".replace(",", " ").replace(".", ",")


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


def _get_client():
    from bot.runtime import get_backend_client
    return get_backend_client()


async def load_profile(actor: TelegramUser):
    client = _get_client()
    data = await client.get_profile(actor.id)
    return data


async def show_home(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    data = await client.get_home(actor.id)

    if not data.get("has_profile"):
        await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
        return

    profile = data["profile"]
    balance = data["balance"]
    next_event = data.get("next_event")
    is_active = data.get("subscription_active", False)
    remaining = data.get("remaining_ai", 0)
    planned = _planned_entity_label(profile)

    lines = [
        "🏠 *Главная*",
        f"👤 {planned or _entity_label(profile['entity_type'])} | {_tax_regime_label(profile['tax_regime'])}",
        f"💰 Баланс: *{_format_money(balance['balance'])}* ₽",
        f"📈 Доходы: {_format_money(balance['income'])} ₽ | 📉 Расходы: {_format_money(balance['expense'])} ₽",
    ]
    if next_event is not None:
        lines.append(f"📅 Ближайшее: *{next_event['title']}* до {next_event['due_date']}")
    else:
        lines.append("📅 Ближайших дедлайнов нет")

    if not is_active:
        lines.append(f"💬 AI-запросов сегодня: *{remaining}*")

    await respond(
        message, "\n".join(lines),
        reply_markup=section_shortcuts_keyboard() if edit else main_menu_keyboard(),
        edit=edit,
    )


async def show_profile(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    data = await client.get_profile(actor.id)

    if not data.get("has_profile"):
        await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
        return

    profile = data["profile"]
    planned = _planned_entity_label(profile)
    text = (
        f"👤 *Профиль бизнеса*\n\n"
        f"Тип: *{planned or _entity_label(profile['entity_type'])}*\n"
        f"Режим: *{_tax_regime_label(profile['tax_regime'])}*\n"
        f"Сотрудники: {'да' if profile.get('has_employees') else 'нет'}\n"
        f"Маркетплейсы: {'да' if profile.get('marketplaces_enabled') else 'нет'}\n"
        f"Регион: {profile.get('region', '—')}"
    )
    await respond(message, text, reply_markup=profile_shortcuts_keyboard(), edit=edit)


async def show_events(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    data = await client.get_events(actor.id, days=14)
    events = data.get("events", [])

    if not events:
        await respond(message, "📅 На ближайшие 14 дней событий нет.", reply_markup=section_shortcuts_keyboard(), edit=edit)
        return
    lines = ["📅 *Ближайшие события:*\n"]
    for item in events[:5]:
        lines.append(f"• *{item['title']}* — до {item['due_date']}")
    await respond(message, "\n".join(lines), reply_markup=event_actions_keyboard(events[0]["user_event_id"]), edit=edit)


async def show_calendar(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    data = await client.get_calendar(actor.id, days=30)
    events = data.get("events", [])

    if not events:
        await respond(message, "📅 На ближайшие 30 дней событий нет.", reply_markup=section_shortcuts_keyboard(), edit=edit)
        return
    lines = ["📅 *Календарь на 30 дней:*\n"]
    for item in events[:10]:
        lines.append(f"{item['due_date']} — {item['title']}")
    await respond(message, "\n".join(lines), reply_markup=section_shortcuts_keyboard(), edit=edit)


async def show_overdue(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    data = await client.get_overdue(actor.id)
    overdue = data.get("events", [])

    if not overdue:
        await respond(message, "✅ Просроченных событий нет!", reply_markup=section_shortcuts_keyboard(), edit=edit)
        return
    lines = ["🔴 *Просроченные события:*\n"]
    for item in overdue[:10]:
        lines.append(f"• *{item['title']}* — до {item['due_date']}")
    await respond(message, "\n".join(lines), reply_markup=section_shortcuts_keyboard(), edit=edit)


async def show_documents(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    data = await client.get_documents(actor.id)
    documents = data.get("documents", [])

    if not documents:
        await respond(message, "📋 Обязательных подач в ближайшие 30 дней нет.", reply_markup=documents_shortcuts_keyboard(), edit=edit)
        return
    lines = ["📋 *Что нужно подать:*\n"]
    for item in documents[:5]:
        lines.append(f"• *{item['title']}* до {item['due_date']}\n  {item['action_required']}")
    await respond(message, "\n".join(lines), reply_markup=documents_shortcuts_keyboard(), edit=edit)


async def show_reminders(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    data = await client.get_reminders(actor.id)

    if not data.get("has_profile"):
        await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
        return
    s = data.get("reminder_settings", {})
    offsets = s.get("offset_days", [3, 1])
    text = (
        "🔔 *Напоминания*\n\n"
        f"Интервалы: *{', '.join(str(i) for i in offsets)}* дней\n"
        f"Налоги: {'✅' if s.get('notify_taxes', True) else '❌'}\n"
        f"Отчётность: {'✅' if s.get('notify_reporting', True) else '❌'}\n"
        f"Документы: {'✅' if s.get('notify_documents', True) else '❌'}\n"
        f"Законы: {'✅' if s.get('notify_laws', True) else '❌'}"
    )
    await respond(message, text, reply_markup=reminders_shortcuts_keyboard(), edit=edit)


async def show_finance(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    report = await client.get_finance_report(actor.id, days=30)

    lines = [
        "📊 *Финансы за 30 дней*\n",
        f"📈 Доходы: *{_format_money(report['income'])}* ₽",
        f"📉 Расходы: *{_format_money(report['expense'])}* ₽",
        f"💰 Прибыль: *{_format_money(report['profit'])}* ₽",
        f"📋 Налоговая база: {_format_money(report['tax_base'])} ₽",
    ]
    top_expenses = report.get("top_expenses", [])
    if top_expenses:
        top = ", ".join(f"{_category_label('expense', item['category'])}: {item['amount']}" for item in top_expenses[:3])
        lines.append(f"\nТоп расходов: {top}")
    await respond(message, "\n".join(lines), reply_markup=finance_shortcuts_keyboard(), edit=edit)


async def show_balance(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    balance = await client.get_balance(actor.id)

    text = (
        "💰 *Баланс за текущий месяц*\n\n"
        f"📈 Доходы: *{_format_money(balance['income'])}* ₽\n"
        f"📉 Расходы: *{_format_money(balance['expense'])}* ₽\n"
        f"💰 Баланс: *{_format_money(balance['balance'])}* ₽"
    )
    await respond(message, text, reply_markup=finance_shortcuts_keyboard(), edit=edit)


async def show_record_list(message: Message, record_type: str, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    data = await client.get_finance_records(actor.id, record_type=record_type, limit=20)
    records = data.get("records", [])

    emoji = "📈" if record_type == "income" else "📉"
    title = "Доходы" if record_type == "income" else "Расходы"
    await respond(message, f"{emoji} *{title}:*\n\n{_format_records(records)}", reply_markup=finance_shortcuts_keyboard(), edit=edit)


async def show_laws(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    data = await client.get_laws(actor.id)

    if not data.get("has_profile"):
        await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
        return

    updates = data.get("updates", [])
    if not updates:
        await respond(message, "📰 Новых обновлений для твоего профиля нет.", reply_markup=laws_shortcuts_keyboard(), edit=edit)
        return
    lines = ["📰 *Новости законов:*\n"]
    for item in updates[:5]:
        effective = item.get("effective_date") or "дата не указана"
        lines.append(f"• *{item['title']}*\n  Вступает: {effective}")
    await respond(message, "\n".join(lines), reply_markup=laws_shortcuts_keyboard(), edit=edit)


async def show_settings(message: Message, *, edit: bool = False) -> None:
    await respond(
        message,
        "⚙️ *Настройки*\n\nОбнови профиль или измени напоминания 👇",
        reply_markup=settings_shortcuts_keyboard(),
        edit=edit,
    )


async def show_help(message: Message, *, edit: bool = False) -> None:
    await respond(message, help_text(), reply_markup=help_shortcuts_keyboard(), edit=edit)


async def show_subscription(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _get_client()
    data = await client.get_subscription_status(actor.id)

    is_active = data.get("is_active", False)
    if is_active:
        plan_label = data.get("plan_label", "Активна")
        expires = data.get("expires_at", "—")
        text = subscription_status_text(plan_label, expires, True)
        await respond(message, text, reply_markup=subscription_manage_keyboard(), edit=edit)
    else:
        remaining = data.get("remaining_ai", 0)
        prices = data.get("prices", {})
        text = paywall_text(remaining)
        await respond(message, text, reply_markup=subscription_keyboard(prices), edit=edit)


async def show_referral(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    bot_info = await message.bot.me()
    client = _get_client()
    data = await client.get_referral(actor.id)

    ref_count = data.get("referral_count", 0)
    bonus_requests = data.get("bonus_requests", 0)
    text = referral_text(bot_info.username, actor.id, ref_count, bonus_requests)
    await respond(message, text, reply_markup=section_shortcuts_keyboard(), edit=edit)
