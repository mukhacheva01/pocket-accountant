import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
    User as TelegramUser,
)

from bot.backend_client import BackendClient
from bot.callbacks import EventActionCallback, NavigationCallback, PageCallback, SubscriptionCallback
from bot.keyboards import (
    ai_consult_keyboard,
    ai_consult_reply_keyboard,
    counterparties_keyboard,
    documents_shortcuts_keyboard,
    event_actions_keyboard,
    finance_shortcuts_keyboard,
    help_shortcuts_keyboard,
    laws_shortcuts_keyboard,
    main_menu_keyboard,
    onboarding_entity_type_keyboard,
    onboarding_tax_keyboard,
    planned_entity_type_keyboard,
    profile_shortcuts_keyboard,
    regime_activity_keyboard,
    regime_income_keyboard,
    reminders_shortcuts_keyboard,
    section_shortcuts_keyboard,
    settings_shortcuts_keyboard,
    subscription_keyboard,
    subscription_manage_keyboard,
    yes_no_keyboard,
)
from bot.messages import (
    ai_consult_welcome_text,
    help_text,
    onboarding_complete_text,
    payment_success_text,
    paywall_text,
    referral_text,
    subscription_status_text,
    welcome_text,
)
from bot.states import AIConsultStates, FinanceInputStates, OnboardingStates, RegimeSelectionStates
from shared.config import get_settings


logger = logging.getLogger(__name__)

PLANNED_ENTITY_TEXT = "Пока не открыт"

ENTITY_TYPE_MAP = {
    "ИП": "individual_entrepreneur",
    "ООО": "limited_company",
    "Самозанятый": "self_employed",
}

TAX_REGIME_MAP = {
    "УСН 6%": "usn_income",
    "УСН доходы-расходы": "usn_income_expense",
    "ОСНО": "osno",
    "НПД": "npd",
}

ENTITY_TYPE_LABELS = {
    "individual_entrepreneur": "ИП",
    "limited_company": "ООО",
    "self_employed": "Самозанятый",
}

TAX_REGIME_LABELS = {
    "usn_income": "УСН 6%",
    "usn_income_expense": "УСН доходы-расходы",
    "osno": "ОСНО",
    "npd": "НПД",
}

INCOME_CATEGORY_LABELS = {
    "sales": "Продажи",
    "services": "Услуги",
    "rent": "Аренда",
    "investments": "Инвестиции",
    "other": "Прочее",
}

EXPENSE_CATEGORY_LABELS = {
    "rent": "Аренда",
    "salary": "Зарплата",
    "taxes": "Налоги",
    "supplies": "Расходные материалы",
    "marketing": "Маркетинг",
    "transport": "Транспорт",
    "communication": "Связь",
    "insurance": "Страхование",
    "other": "Прочее",
}

PLAN_LABELS = {
    "basic": "Базовый",
    "pro": "Про",
    "annual": "Годовой",
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

PLAN_DETAILS: dict[str, dict] = {
    "basic": {"label": "Базовый", "days": 30, "ai_limit": 50},
    "pro": {"label": "Про", "days": 30, "ai_limit": 999},
    "annual": {"label": "Годовой", "days": 365, "ai_limit": 999},
}

_AMOUNT_PATTERN = re.compile(
    r"(?P<number>\d[\d\s.,]*)\s*(?P<suffix>к|k|тыс|т|млн|m)?",
    flags=re.IGNORECASE,
)


def _parse_amount(raw_text: str) -> Decimal | None:
    match = _AMOUNT_PATTERN.search(raw_text.lower())
    if match is None:
        return None
    amount = Decimal(match.group("number").replace(" ", "").replace(",", "."))
    suffix = (match.group("suffix") or "").lower()
    if suffix in {"к", "k", "тыс", "т"}:
        amount *= Decimal("1000")
    elif suffix in {"млн", "m"}:
        amount *= Decimal("1000000")
    return amount

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
    reminder_settings = profile.get("reminder_settings", {})
    if reminder_settings.get("planning_entity"):
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
    if isinstance(value, str):
        value = float(value)
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def build_router() -> Router:
    router = Router()
    settings = get_settings()
    api = BackendClient()

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

    async def load_profile(actor: TelegramUser) -> tuple[dict, dict | None]:
        user = await api.ensure_user(
            telegram_id=actor.id,
            username=actor.username,
            first_name=actor.first_name,
            timezone="Europe/Moscow",
        )
        profile = await api.get_profile(user["user_id"])
        if not profile.get("has_profile"):
            return user, None
        return user, profile

    # ── Show helpers ──

    async def show_home(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        user, profile = await load_profile(actor)
        if profile is None:
            await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
            return

        events_data = await api.upcoming_events(user["user_id"], 7)
        balance = await api.get_finance_report(user["user_id"])
        sub_data = await api.subscription_status(user["user_id"])
        events = events_data.get("events", [])
        next_event = events[0] if events else None
        planned = _planned_entity_label(profile)

        lines = [
            "🏠 *Главная*",
            f"👤 {planned or _entity_label(profile.get('entity_type', ''))} | {_tax_regime_label(profile.get('tax_regime', ''))}",
            f"💰 Баланс: *{_format_money(balance.get('balance', 0))}* ₽",
            f"📈 Доходы: {_format_money(balance.get('income', 0))} ₽ | 📉 Расходы: {_format_money(balance.get('expense', 0))} ₽",
        ]
        if next_event is not None:
            title = next_event.get("title", "Событие")
            lines.append(f"📅 Ближайшее: *{title}* до {next_event.get('due_date', '')}")
        else:
            lines.append("📅 Ближайших дедлайнов нет")

        if not sub_data.get("is_active"):
            lines.append(f"💬 AI-запросов сегодня: *{sub_data.get('remaining_ai_requests', 0)}*")

        await respond(
            message, "\n".join(lines),
            reply_markup=section_shortcuts_keyboard() if edit else main_menu_keyboard(),
            edit=edit,
        )

    async def show_profile(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        user, profile = await load_profile(actor)
        if profile is None:
            await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
            return
        planned = _planned_entity_label(profile)
        text = (
            f"👤 *Профиль бизнеса*\n\n"
            f"Тип: *{planned or _entity_label(profile.get('entity_type', ''))}*\n"
            f"Режим: *{_tax_regime_label(profile.get('tax_regime', ''))}*\n"
            f"Сотрудники: {'да' if profile.get('has_employees') else 'нет'}\n"
            f"Маркетплейсы: {'да' if profile.get('marketplaces_enabled') else 'нет'}\n"
            f"Регион: {profile.get('region', 'не указан')}"
        )
        await respond(message, text, reply_markup=profile_shortcuts_keyboard(), edit=edit)

    async def show_events(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        user, _ = await load_profile(actor)
        events_data = await api.upcoming_events(user["user_id"], 14)
        events = events_data.get("events", [])
        if not events:
            await respond(message, "📅 На ближайшие 14 дней событий нет.", reply_markup=section_shortcuts_keyboard(), edit=edit)
            return
        lines = ["📅 *Ближайшие события:*\n"]
        for item in events[:5]:
            title = item.get("title", "Событие")
            lines.append(f"• *{title}* — до {item.get('due_date', '')}")
        await respond(message, "\n".join(lines), reply_markup=event_actions_keyboard(events[0].get("user_event_id", "")), edit=edit)

    async def show_calendar(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        user, _ = await load_profile(actor)
        events_data = await api.upcoming_events(user["user_id"], 30)
        events = events_data.get("events", [])
        if not events:
            await respond(message, "📅 На ближайшие 30 дней событий нет.", reply_markup=section_shortcuts_keyboard(), edit=edit)
            return
        lines = ["📅 *Календарь на 30 дней:*\n"]
        for item in events[:10]:
            title = item.get("title", "Событие")
            lines.append(f"{item.get('due_date', '')} — {title}")
        await respond(message, "\n".join(lines), reply_markup=section_shortcuts_keyboard(), edit=edit)

    async def show_overdue(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        user, _ = await load_profile(actor)
        overdue_data = await api.overdue_events(user["user_id"])
        overdue = overdue_data.get("events", [])
        if not overdue:
            await respond(message, "✅ Просроченных событий нет!", reply_markup=section_shortcuts_keyboard(), edit=edit)
            return
        lines = ["🔴 *Просроченные события:*\n"]
        for item in overdue[:10]:
            title = item.get("title", "Событие")
            lines.append(f"• *{title}* — до {item.get('due_date', '')}")
        await respond(message, "\n".join(lines), reply_markup=section_shortcuts_keyboard(), edit=edit)

    async def show_documents(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        user, _ = await load_profile(actor)
        documents_data = await api.upcoming_documents(user["user_id"])
        documents = documents_data if isinstance(documents_data, list) else documents_data.get("documents", [])
        if not documents:
            await respond(message, "📋 Обязательных подач в ближайшие 30 дней нет.", reply_markup=documents_shortcuts_keyboard(), edit=edit)
            return
        lines = ["📋 *Что нужно подать:*\n"]
        for item in documents[:5]:
            lines.append(f"• *{item['title']}* до {item['due_date']}\n  {item['action_required']}")
        await respond(message, "\n".join(lines), reply_markup=documents_shortcuts_keyboard(), edit=edit)

    async def show_reminders(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        _, profile = await load_profile(actor)
        if profile is None:
            await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
            return
        s = profile.get("reminder_settings", {})
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
        user, profile = await load_profile(actor)
        report = await api.get_full_report(user["user_id"], 30)
        income = report.get("income", 0)
        expense = report.get("expense", 0)
        profit = report.get("profit", 0)
        tax_base = income
        if profile is not None and profile.get("tax_regime") == "usn_income_expense":
            tax_base = profit
        lines = [
            "📊 *Финансы за 30 дней*\n",
            f"📈 Доходы: *{_format_money(income)}* ₽",
            f"📉 Расходы: *{_format_money(expense)}* ₽",
            f"💰 Прибыль: *{_format_money(profit)}* ₽",
            f"📋 Налоговая база: {_format_money(tax_base)} ₽",
        ]
        top_expenses = report.get("top_expenses", [])
        if top_expenses:
            top = ", ".join(f"{_category_label('expense', cat)}: {amt}" for cat, amt in top_expenses[:3])
            lines.append(f"\nТоп расходов: {top}")
        await respond(message, "\n".join(lines), reply_markup=finance_shortcuts_keyboard(), edit=edit)

    async def show_balance(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        user, _ = await load_profile(actor)
        balance = await api.get_finance_report(user["user_id"])
        text = (
            "💰 *Баланс за текущий месяц*\n\n"
            f"📈 Доходы: *{_format_money(balance.get('income', 0))}* ₽\n"
            f"📉 Расходы: *{_format_money(balance.get('expense', 0))}* ₽\n"
            f"💰 Баланс: *{_format_money(balance.get('balance', 0))}* ₽"
        )
        await respond(message, text, reply_markup=finance_shortcuts_keyboard(), edit=edit)

    async def show_record_list(message: Message, record_type: str, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        user, _ = await load_profile(actor)
        records_data = await api.get_finance_records(user["user_id"], record_type=record_type, limit=20)
        records = records_data.get("records", [])
        emoji = "📈" if record_type == "income" else "📉"
        title = "Доходы" if record_type == "income" else "Расходы"
        await respond(message, f"{emoji} *{title}:*\n\n{_format_records(records)}", reply_markup=finance_shortcuts_keyboard(), edit=edit)

    async def show_laws(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        user, profile = await load_profile(actor)
        if profile is None:
            await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
            return
        laws_data = await api.relevant_laws(user["user_id"])
        updates = laws_data if isinstance(laws_data, list) else laws_data.get("updates", [])
        if not updates:
            await respond(message, "📰 Новых обновлений для твоего профиля нет.", reply_markup=laws_shortcuts_keyboard(), edit=edit)
            return
        lines = ["📰 *Новости законов:*\n"]
        for item in updates[:5]:
            effective = item.get("effective_date", "дата не указана")
            lines.append(f"• *{item.get('title', '')}*\n  Вступает: {effective}")
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
        user, _ = await load_profile(actor)
        sub_data = await api.subscription_status(user["user_id"])
        is_active = sub_data.get("is_active", False)
        prices = {
            "basic": settings.stars_price_basic,
            "pro": settings.stars_price_pro,
            "annual": settings.stars_price_annual,
        }
        if is_active:
            plan_label = PLAN_LABELS.get(sub_data.get("plan", ""), "Активна")
            expires = sub_data.get("expires_at", "—")
            if expires and expires != "—":
                try:
                    expires = datetime.fromisoformat(expires).strftime("%d.%m.%Y")
                except (ValueError, TypeError):
                    pass
            text = subscription_status_text(plan_label, expires, True)
            await respond(message, text, reply_markup=subscription_manage_keyboard(), edit=edit)
        else:
            remaining = sub_data.get("remaining_ai_requests", 0)
            text = paywall_text(remaining)
            await respond(message, text, reply_markup=subscription_keyboard(prices), edit=edit)

    async def show_referral(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        user, _ = await load_profile(actor)
        bot_info = await message.bot.me()
        info = await api.referral_info(user["user_id"])
        text = referral_text(bot_info.username, actor.id, info.get("count", 0), info.get("bonus_days_earned", 0))
        await respond(message, text, reply_markup=section_shortcuts_keyboard(), edit=edit)

    async def show_ai_consult(message: Message, state: FSMContext, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
        actor = actor or message.from_user
        user, _ = await load_profile(actor)
        sub_data = await api.subscription_status(user["user_id"])
        is_active = sub_data.get("is_active", False)
        can_use = sub_data.get("can_use_ai", True)
        remaining = sub_data.get("remaining_ai_requests", 0)

        if not can_use:
            prices = {
                "basic": settings.stars_price_basic,
                "pro": settings.stars_price_pro,
                "annual": settings.stars_price_annual,
            }
            await respond(message, paywall_text(0), reply_markup=subscription_keyboard(prices), edit=edit)
            return

        await state.set_state(AIConsultStates.chatting)
        text = ai_consult_welcome_text(remaining, is_active)
        if edit:
            await respond(message, text, reply_markup=ai_consult_keyboard(), edit=True)
        else:
            await message.answer(text, reply_markup=ai_consult_reply_keyboard(), parse_mode="Markdown")
            await message.answer("Выбери тему или напиши свой вопрос:", reply_markup=ai_consult_keyboard(), parse_mode="Markdown")

    async def do_ai_answer(message: Message, question: str) -> None:
        """Shared AI answer logic for consult mode and topic shortcuts."""
        user, _ = await load_profile(message.from_user)
        sub_data = await api.subscription_status(user["user_id"])
        can_use = sub_data.get("can_use_ai", True)

        if not can_use:
            prices = {
                "basic": settings.stars_price_basic,
                "pro": settings.stars_price_pro,
                "annual": settings.stars_price_annual,
            }
            await message.answer(paywall_text(0), reply_markup=subscription_keyboard(prices), parse_mode="Markdown")
            return

        await message.bot.send_chat_action(message.chat.id, "typing")

        result = await api.ask_ai(user["user_id"], question)
        response_text = result.get("text", "")

        footer = ""
        is_active = sub_data.get("is_active", False)
        if not is_active:
            new_remaining = result.get("remaining_ai_requests", sub_data.get("remaining_ai_requests", 0))
            if isinstance(new_remaining, int) and new_remaining <= 2:
                footer = f"\n\n💬 Осталось запросов: *{new_remaining}*"

        await message.answer(response_text + footer, reply_markup=ai_consult_keyboard(), parse_mode="Markdown")

    async def prompt_finance_input(message: Message, state: FSMContext, record_kind: str, *, edit: bool = False) -> None:
        if record_kind == "income":
            await state.set_state(FinanceInputStates.income)
            text = "💰 Напиши доход одной фразой.\nПример: _получил 50к от клиента_"
        else:
            await state.set_state(FinanceInputStates.expense)
            text = "💸 Напиши расход одной фразой.\nПример: _заплатил 12к за рекламу_"
        await respond(message, text, reply_markup=finance_shortcuts_keyboard(), edit=edit)

    async def start_regime_picker(message: Message, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(RegimeSelectionStates.activity)
        await message.answer("🔍 *Подбор режима* (1/5)\n\nЧем занимаешься?", reply_markup=regime_activity_keyboard(), parse_mode="Markdown")

    async def handle_tax_calculation(message: Message, raw_query: str) -> bool:
        user, profile = await load_profile(message.from_user)
        profile_ctx = {}
        if profile:
            profile_ctx = {
                "entity_type": profile.get("entity_type"),
                "tax_regime": profile.get("tax_regime"),
                "has_employees": profile.get("has_employees", False),
            }
        result = await api.parse_tax_query(raw_query, profile_ctx)
        if result.get("question"):
            await message.answer(result["question"])
            return True
        if result.get("text"):
            await message.answer(result["text"], reply_markup=main_menu_keyboard())
            return True
        return False

    async def check_ai_limit(message: Message, user_id: str) -> bool:
        """Returns True if user can proceed, False if paywall should be shown."""
        sub_data = await api.subscription_status(user_id)
        can_use = sub_data.get("can_use_ai", True)
        if not can_use:
            prices = {
                "basic": settings.stars_price_basic,
                "pro": settings.stars_price_pro,
                "annual": settings.stars_price_annual,
            }
            await message.answer(paywall_text(0), reply_markup=subscription_keyboard(prices), parse_mode="Markdown")
            return False
        remaining = sub_data.get("remaining_ai_requests", 0)
        if remaining <= 1 and not sub_data.get("is_active"):
            await message.answer("⚠️ Это последний бесплатный AI-запрос сегодня.", parse_mode="Markdown")
        return True

    # ── Handlers ──

    @router.message(CommandStart())
    async def start_handler(message: Message, state: FSMContext) -> None:
        args = message.text.split(maxsplit=1)
        ref_id = None
        if len(args) > 1 and args[1].startswith("ref_"):
            ref_id = args[1][4:]

        user, profile = await load_profile(message.from_user)

        if ref_id and str(message.from_user.id) != ref_id:
            try:
                await api.process_referral(user["user_id"], ref_id)
            except Exception:
                logger.warning("Referral processing failed for ref_id=%s", ref_id)

        if profile is not None:
            await state.clear()
            await show_home(message)
            return
        await state.set_state(OnboardingStates.entity_type)
        await message.answer(welcome_text(message.from_user.first_name), reply_markup=onboarding_entity_type_keyboard(), parse_mode="Markdown")

    @router.message(Command("menu"))
    @router.message(F.text == "🏠 Главная")
    async def menu_handler(message: Message) -> None:
        await show_home(message)

    @router.message(Command("help"))
    @router.message(F.text == "❓ Помощь")
    async def help_handler(message: Message) -> None:
        await show_help(message)

    @router.message(Command("profile"))
    @router.message(F.text == "👤 Профиль")
    async def profile_handler(message: Message) -> None:
        await show_profile(message)

    @router.message(Command("events"))
    @router.message(F.text == "📅 События")
    async def events_handler(message: Message) -> None:
        await show_events(message)

    @router.message(Command("calendar"))
    async def calendar_handler(message: Message) -> None:
        await show_calendar(message)

    @router.message(Command("overdue"))
    async def overdue_handler(message: Message) -> None:
        await show_overdue(message)

    @router.message(Command("documents"))
    @router.message(F.text == "📋 Что подать")
    async def documents_handler(message: Message) -> None:
        await show_documents(message)

    @router.message(Command("reminders"))
    async def reminders_handler(message: Message) -> None:
        await show_reminders(message)

    @router.message(Command("laws"))
    async def laws_handler(message: Message) -> None:
        await show_laws(message)

    @router.message(Command("finance"))
    @router.message(F.text == "📊 Финансы")
    async def finance_handler(message: Message) -> None:
        await show_finance(message)

    @router.message(Command("balance"))
    async def balance_handler(message: Message) -> None:
        await show_balance(message)

    @router.message(Command("income"))
    async def income_list_handler(message: Message) -> None:
        await show_record_list(message, "income")

    @router.message(Command("expenses"))
    async def expense_list_handler(message: Message) -> None:
        await show_record_list(message, "expense")

    @router.message(Command("report"))
    async def report_handler(message: Message) -> None:
        await show_finance(message)

    @router.message(Command("consult"))
    @router.message(F.text == "💬 AI Консультация")
    async def ai_consult_handler(message: Message, state: FSMContext) -> None:
        await show_ai_consult(message, state)

    @router.message(Command("subscription"))
    @router.message(F.text == "⭐ Подписка")
    async def subscription_handler(message: Message) -> None:
        await show_subscription(message)

    @router.message(Command("referral"))
    async def referral_handler(message: Message) -> None:
        await show_referral(message)

    @router.message(Command("calc"))
    async def calc_handler(message: Message) -> None:
        payload = message.text.partition(" ")[2].strip()
        if not payload:
            await message.answer("Пришли запрос так: /calc усн 6 доход 500000", parse_mode="Markdown")
            return
        handled = await handle_tax_calculation(message, payload)
        if not handled:
            await message.answer("Не понял режим или сумму.\nПример: /calc самозанятый доход 120к от физлиц", parse_mode="Markdown")

    @router.message(Command("regime"))
    @router.message(Command("choose_regime"))
    @router.message(F.text == "🔍 Подобрать режим")
    async def regime_handler(message: Message, state: FSMContext) -> None:
        await start_regime_picker(message, state)

    @router.message(Command("add_income"))
    @router.message(F.text == "💰 Добавить доход")
    async def add_income_handler(message: Message, state: FSMContext) -> None:
        payload = message.text.partition(" ")[2].strip()
        if not payload:
            await prompt_finance_input(message, state, "income")
            return
        user, _ = await load_profile(message.from_user)
        try:
            await api.add_from_text(user["user_id"], _normalize_finance_text(payload, "income"))
        except Exception:
            await message.answer("Не понял формат. Пример: _получил 50к от клиента_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Доход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    @router.message(Command("add_expense"))
    @router.message(F.text == "💸 Добавить расход")
    async def add_expense_handler(message: Message, state: FSMContext) -> None:
        payload = message.text.partition(" ")[2].strip()
        if not payload:
            await prompt_finance_input(message, state, "expense")
            return
        user, _ = await load_profile(message.from_user)
        try:
            await api.add_from_text(user["user_id"], _normalize_finance_text(payload, "expense"))
        except Exception:
            await message.answer("Не понял формат. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Расход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    @router.message(Command("settings"))
    async def settings_handler(message: Message) -> None:
        await show_settings(message)

    @router.message(F.text == "Отмена")
    async def cancel_handler(message: Message, state: FSMContext) -> None:
        await state.clear()
        await show_home(message)

    @router.message(F.text == "🗑 Новый диалог")
    async def clear_ai_history_handler(message: Message, state: FSMContext) -> None:
        user, _ = await load_profile(message.from_user)
        await api.clear_ai_history(user["user_id"])
        await state.set_state(AIConsultStates.chatting)
        await message.answer("🗑 История очищена. Начинаем с чистого листа!\n\nЗадай вопрос 👇", reply_markup=ai_consult_reply_keyboard(), parse_mode="Markdown")

    # ── Onboarding (shortened: 4 steps) ──

    @router.message(OnboardingStates.entity_type)
    async def onboarding_entity_handler(message: Message, state: FSMContext) -> None:
        if message.text == PLANNED_ENTITY_TEXT:
            await state.update_data(planning_entity=True)
            await message.answer("Что планируешь открыть?", reply_markup=planned_entity_type_keyboard())
            return
        if message.text not in ENTITY_TYPE_MAP:
            await message.answer("Выбери из кнопок 👇")
            return
        entity_type_str = ENTITY_TYPE_MAP[message.text]
        await state.update_data(entity_type=entity_type_str)
        if entity_type_str == "self_employed":
            await state.update_data(tax_regime="npd", has_employees=False)
            await state.set_state(OnboardingStates.region)
            await message.answer("📍 *Шаг 2/3.* Укажи регион:", parse_mode="Markdown")
            return
        await state.set_state(OnboardingStates.tax_regime)
        await message.answer("📋 *Шаг 2/4.* Налоговый режим:", reply_markup=onboarding_tax_keyboard(), parse_mode="Markdown")

    @router.message(OnboardingStates.tax_regime)
    async def onboarding_tax_handler(message: Message, state: FSMContext) -> None:
        if message.text not in TAX_REGIME_MAP:
            await message.answer("Выбери режим из кнопок 👇")
            return
        await state.update_data(tax_regime=TAX_REGIME_MAP[message.text])
        await state.set_state(OnboardingStates.has_employees)
        await message.answer("👥 *Шаг 3/4.* Есть сотрудники?", reply_markup=yes_no_keyboard(), parse_mode="Markdown")

    @router.message(OnboardingStates.has_employees)
    async def onboarding_employees_handler(message: Message, state: FSMContext) -> None:
        if message.text not in {"Да", "Нет"}:
            await message.answer("Нажми Да или Нет.")
            return
        await state.update_data(has_employees=message.text == "Да")
        await state.set_state(OnboardingStates.region)
        await message.answer("📍 *Последний шаг.* Укажи регион:", parse_mode="Markdown")

    @router.message(OnboardingStates.region)
    async def onboarding_finish_handler(message: Message, state: FSMContext) -> None:
        payload = await state.get_data()

        entity_type_val = payload.get("entity_type")
        tax_regime_val = payload.get("tax_regime")
        if not entity_type_val:
            await state.clear()
            await message.answer("Что-то пошло не так. Начни заново: /start")
            return

        if not tax_regime_val:
            tax_regime_val = "npd"

        draft = {
            "entity_type": entity_type_val,
            "tax_regime": tax_regime_val,
            "has_employees": payload.get("has_employees", False),
            "marketplaces_enabled": False,
            "industry": None,
            "region": message.text.strip(),
            "timezone": "Europe/Moscow",
            "reminder_settings": {
                "notify_taxes": True,
                "notify_reporting": True,
                "notify_documents": True,
                "notify_laws": True,
                "offset_days": [3, 1],
                "planning_entity": bool(payload.get("planning_entity")),
            },
        }

        user, _ = await load_profile(message.from_user)
        await api.save_profile(user["user_id"], draft)

        await state.clear()
        await message.answer(onboarding_complete_text(), reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    # ── AI Consult state ──

    @router.message(AIConsultStates.chatting)
    async def ai_consult_chatting_handler(message: Message, state: FSMContext) -> None:
        raw_text = (message.text or "").strip()
        if not raw_text:
            return
        # Let menu buttons escape consult mode
        if raw_text == "🏠 Главная":
            await state.clear()
            await show_home(message)
            return
        if raw_text in MAIN_MENU_BUTTONS and raw_text not in {"💬 AI Консультация", "🗑 Новый диалог"}:
            await state.clear()
            return
        if raw_text == "💬 AI Консультация":
            await show_ai_consult(message, state)
            return
        # Process as AI question
        await do_ai_answer(message, raw_text)

    # ── Finance input states ──

    @router.message(FinanceInputStates.income)
    async def income_state_handler(message: Message, state: FSMContext) -> None:
        source_text = _normalize_finance_text((message.text or "").strip(), "income")
        if not source_text:
            await message.answer("Напиши сумму. Пример: _получил 50к от клиента_", parse_mode="Markdown")
            return
        user, _ = await load_profile(message.from_user)
        try:
            await api.add_from_text(user["user_id"], source_text)
        except Exception:
            await message.answer("Не понял сумму. Пример: _получил 50к от клиента_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Доход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    @router.message(FinanceInputStates.expense)
    async def expense_state_handler(message: Message, state: FSMContext) -> None:
        source_text = _normalize_finance_text((message.text or "").strip(), "expense")
        if not source_text:
            await message.answer("Напиши сумму. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
            return
        user, _ = await load_profile(message.from_user)
        try:
            await api.add_from_text(user["user_id"], source_text)
        except Exception:
            await message.answer("Не понял сумму. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Расход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    # ── Regime picker states ──

    @router.message(RegimeSelectionStates.activity)
    async def regime_activity_handler(message: Message, state: FSMContext) -> None:
        if message.text not in REGIME_ACTIVITY_MAP:
            await message.answer("Выбери из кнопок 👇")
            return
        await state.update_data(activity=REGIME_ACTIVITY_MAP[message.text])
        await state.set_state(RegimeSelectionStates.monthly_income)
        await message.answer("🔍 *(2/5)* Доход в месяц?", reply_markup=regime_income_keyboard(), parse_mode="Markdown")

    @router.message(RegimeSelectionStates.monthly_income)
    async def regime_income_handler(message: Message, state: FSMContext) -> None:
        amount = _parse_amount(message.text or "")
        if amount is None:
            await message.answer("Напиши сумму числом. Например: 300000")
            return
        await state.update_data(monthly_income=str(amount))
        await state.set_state(RegimeSelectionStates.has_employees)
        await message.answer("🔍 *(3/5)* Есть сотрудники?", reply_markup=yes_no_keyboard(), parse_mode="Markdown")

    @router.message(RegimeSelectionStates.has_employees)
    async def regime_employees_handler(message: Message, state: FSMContext) -> None:
        if message.text not in {"Да", "Нет"}:
            await message.answer("Нажми Да или Нет.")
            return
        await state.update_data(has_employees=message.text == "Да")
        await state.set_state(RegimeSelectionStates.counterparties)
        await message.answer("🔍 *(4/5)* Кто контрагенты?", reply_markup=counterparties_keyboard(), parse_mode="Markdown")

    @router.message(RegimeSelectionStates.counterparties)
    async def regime_counterparties_handler(message: Message, state: FSMContext) -> None:
        if message.text not in COUNTERPARTIES_MAP:
            await message.answer("Выбери из кнопок 👇")
            return
        await state.update_data(counterparties=COUNTERPARTIES_MAP[message.text])
        await state.set_state(RegimeSelectionStates.region)
        await message.answer("🔍 *(5/5)* Укажи регион:", parse_mode="Markdown")

    @router.message(RegimeSelectionStates.region)
    async def regime_region_handler(message: Message, state: FSMContext) -> None:
        payload = await state.get_data()
        try:
            monthly_income = Decimal(str(payload["monthly_income"]))
        except (KeyError, InvalidOperation):
            await state.clear()
            await message.answer("Не удалось собрать данные. Начни заново: /regime")
            return
        result = await api.compare_regimes(
            activity=payload["activity"], monthly_income=str(monthly_income),
            has_employees=payload["has_employees"], counterparties=payload["counterparties"],
            region=message.text.strip(),
        )
        await state.clear()
        text = result.get("text", "Не удалось сравнить режимы.")
        await message.answer(text, reply_markup=main_menu_keyboard())

    # ── Subscription callbacks ──

    @router.callback_query(SubscriptionCallback.filter())
    async def subscription_action_handler(query: CallbackQuery, callback_data: SubscriptionCallback) -> None:
        if query.message is None:
            await query.answer()
            return

        if callback_data.action == "buy":
            plan_key = callback_data.plan
            if plan_key not in PLAN_DETAILS:
                await query.answer("Неизвестный тариф", show_alert=True)
                return

            details = PLAN_DETAILS[plan_key]
            price_map = {
                "basic": settings.stars_price_basic,
                "pro": settings.stars_price_pro,
                "annual": settings.stars_price_annual,
            }
            price = price_map.get(plan_key, settings.stars_price_basic)

            await query.message.answer_invoice(
                title=f"Подписка «{details['label']}»",
                description=f"AI без лимитов на {details['days']} дней",
                payload=f"sub_{plan_key}",
                currency="XTR",
                prices=[LabeledPrice(label=f"Подписка {details['label']}", amount=price)],
            )
            await query.answer()

    @router.pre_checkout_query()
    async def pre_checkout_handler(pre_checkout: PreCheckoutQuery) -> None:
        payload = pre_checkout.invoice_payload
        price_map = {
            "sub_basic": settings.stars_price_basic,
            "sub_pro": settings.stars_price_pro,
            "sub_annual": settings.stars_price_annual,
        }
        expected = price_map.get(payload)
        if expected is None or expected != pre_checkout.total_amount:
            await pre_checkout.answer(ok=False, error_message="Некорректные данные платежа. Попробуй снова.")
            return
        await pre_checkout.answer(ok=True)

    @router.message(F.successful_payment)
    async def successful_payment_handler(message: Message) -> None:
        payment = message.successful_payment
        payload = payment.invoice_payload

        plan_key_map = {
            "sub_basic": "basic",
            "sub_pro": "pro",
            "sub_annual": "annual",
        }
        plan_key = plan_key_map.get(payload)
        if plan_key is None:
            await message.answer("Оплата получена, но тариф не распознан. Напиши в поддержку.")
            return

        user, _ = await load_profile(message.from_user)
        result = await api.process_payment(
            user_id=user["user_id"],
            plan=plan_key,
            amount=payment.total_amount,
            charge_id=payment.telegram_payment_charge_id,
        )
        if result.get("already_processed"):
            await message.answer("Оплата уже обработана. Если доступ не появился — напиши в поддержку.")
            return

        details = PLAN_DETAILS.get(plan_key, {})
        expires = result.get("expires_at", "—")
        if expires and expires != "—":
            try:
                expires = datetime.fromisoformat(expires).strftime("%d.%m.%Y")
            except (ValueError, TypeError):
                pass
        await message.answer(
            payment_success_text(details.get("label", plan_key), expires),
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )

    # ── Navigation callbacks ──

    @router.callback_query(NavigationCallback.filter())
    async def navigation_handler(query: CallbackQuery, callback_data: NavigationCallback, state: FSMContext) -> None:
        message = query.message
        if message is None:
            await query.answer()
            return
        target = callback_data.target
        target_map = {
            "home": lambda: show_home(message, query.from_user, edit=True),
            "profile": lambda: show_profile(message, query.from_user, edit=True),
            "events": lambda: show_events(message, query.from_user, edit=True),
            "calendar": lambda: show_calendar(message, query.from_user, edit=True),
            "overdue": lambda: show_overdue(message, query.from_user, edit=True),
            "documents": lambda: show_documents(message, query.from_user, edit=True),
            "reminders": lambda: show_reminders(message, query.from_user, edit=True),
            "laws": lambda: show_laws(message, query.from_user, edit=True),
            "finance": lambda: show_finance(message, query.from_user, edit=True),
            "balance": lambda: show_balance(message, query.from_user, edit=True),
            "income_list": lambda: show_record_list(message, "income", query.from_user, edit=True),
            "expense_list": lambda: show_record_list(message, "expense", query.from_user, edit=True),
            "income_prompt": lambda: prompt_finance_input(message, state, "income", edit=True),
            "expense_prompt": lambda: prompt_finance_input(message, state, "expense", edit=True),
            "pick_regime": lambda: start_regime_picker(message, state),
            "settings": lambda: show_settings(message, edit=True),
            "help": lambda: show_help(message, edit=True),
            "subscription": lambda: show_subscription(message, query.from_user, edit=True),
            "referral": lambda: show_referral(message, query.from_user, edit=True),
            "ai_consult": lambda: show_ai_consult(message, state, query.from_user, edit=True),
        }

        # AI topic quick-questions
        if target in AI_TOPIC_PROMPTS:
            await state.set_state(AIConsultStates.chatting)
            await query.answer()
            await do_ai_answer(message, AI_TOPIC_PROMPTS[target])
            return

        # Clear AI history
        if target == "ai_clear_history":
            user, _ = await load_profile(query.from_user)
            await api.clear_ai_history(user["user_id"])
            await respond(message, "🗑 История очищена!\n\nЗадай новый вопрос 👇", reply_markup=ai_consult_keyboard(), edit=True)
            await query.answer("История очищена")
            return

        # Exit AI consult
        if target == "ai_exit":
            await state.clear()
            await show_home(message, query.from_user, edit=True)
            await query.answer()
            return

        if target == "restart_onboarding":
            await state.clear()
            await state.set_state(OnboardingStates.entity_type)
            await respond(message, welcome_text(query.from_user.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=True)
            await query.answer()
            return
        if target == "cancel_subscription":
            user, _ = await load_profile(query.from_user)
            await api.cancel_subscription(user["user_id"])
            await respond(
                message,
                "🚫 Подписка отменена. Доступ сохранится до конца оплаченного периода.",
                reply_markup=section_shortcuts_keyboard(),
                edit=True,
            )
            await query.answer()
            return

        action = target_map.get(target)
        if action:
            await action()
        else:
            await query.answer("Скоро будет!", show_alert=False)
            return
        await query.answer()

    @router.callback_query(EventActionCallback.filter())
    async def event_action_handler(query: CallbackQuery, callback_data: EventActionCallback) -> None:
        if query.message is None:
            await query.answer()
            return
        await api.event_action(callback_data.event_id, callback_data.action)
        if callback_data.action == "snooze":
            await query.message.edit_text("⏰ Отложено на 1 день.", reply_markup=section_shortcuts_keyboard())
        else:
            await query.message.edit_text("✅ Выполнено!", reply_markup=section_shortcuts_keyboard())
        await query.answer()

    @router.callback_query(PageCallback.filter())
    async def page_handler(query: CallbackQuery, callback_data: PageCallback) -> None:
        await query.answer("Скоро будет!", show_alert=False)

    # ── Catch-all: AI + finance + tax + templates ──

    @router.message(F.content_type.in_({"sticker", "voice", "video_note", "photo", "document", "video", "audio", "contact", "location"}))
    async def unsupported_content_handler(message: Message) -> None:
        await message.answer("Я пока работаю только с текстом. Напиши вопрос или выбери раздел 👇", reply_markup=main_menu_keyboard())

    @router.message()
    async def ai_question_handler(message: Message, state: FSMContext) -> None:
        if await state.get_state() is not None:
            return
        if message.text in MAIN_MENU_BUTTONS:
            return

        raw_text = (message.text or "").strip()
        if not raw_text:
            return

        normalized = raw_text.lower()
        finance_hints = ("получил", "пришло", "поступление", "заплатил", "оплатил", "потратил", "доход", "расход")
        tax_hints = ("налог", "усн", "нпд", "осно", "патент", "псн", "ндс", "режим", "ставка")

        # Try finance first
        if any(hint in normalized for hint in finance_hints) and not any(hint in normalized for hint in tax_hints):
            user, _ = await load_profile(message.from_user)
            try:
                result = await api.add_from_text(user["user_id"], raw_text)
                if result and result.get("saved"):
                    record_type = result.get("record_type", "income")
                    label = _category_label(record_type, result.get("category", ""))
                    kind = "доход" if record_type == "income" else "расход"
                    await message.answer(
                        f"✅ Сохранил {kind}: *{result.get('amount', 0)}* ₽, категория _{label}_",
                        reply_markup=finance_shortcuts_keyboard(),
                        parse_mode="Markdown",
                    )
                    return
            except Exception:
                pass

        # Try tax calculation
        if await handle_tax_calculation(message, raw_text):
            return

        # AI question
        await do_ai_answer(message, raw_text)

    return router
