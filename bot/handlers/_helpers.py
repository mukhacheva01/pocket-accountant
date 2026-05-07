"""Shared helpers and constants for handler modules."""

from __future__ import annotations

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
    subscription_status_text,
    welcome_text,
)
from shared.clock import utcnow  # noqa: F401
from shared.config import get_settings
from shared.db.enums import EntityType, FinanceRecordType, TaxRegime
from shared.db.session import SessionFactory
from backend.services.container import build_services
from backend.services.finance_parser import EXPENSE_CATEGORY_LABELS, INCOME_CATEGORY_LABELS
from backend.services.profile_matching import ProfileContext
from backend.services.subscription import PLAN_DETAILS


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


def _entity_label(value: str) -> str:
    return ENTITY_TYPE_LABELS.get(value, value)


def _tax_regime_label(value: str) -> str:
    return TAX_REGIME_LABELS.get(value, value)


def _category_label(record_type: FinanceRecordType, category: str) -> str:
    if record_type == FinanceRecordType.INCOME:
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


def _planned_entity_label(profile) -> str | None:
    if profile.reminder_settings.get("planning_entity"):
        return "Пока не открыт"
    return None


def _format_records(records) -> str:
    if not records:
        return "Записей пока нет."
    lines = []
    for record in records:
        sign = "+" if record.record_type == FinanceRecordType.INCOME else "-"
        label = _category_label(record.record_type, record.category)
        lines.append(f"{record.operation_date.isoformat()} | {sign}{record.amount} ₽ | {label}")
    return "\n".join(lines)


def _format_money(value) -> str:
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


async def load_profile(actor: TelegramUser):
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id,
            username=actor.username,
            first_name=actor.first_name,
            timezone="Europe/Moscow",
        )
        profile = await services.onboarding.load_profile(str(user.id))
        return user, profile


async def sync_profile_events_and_reminders(
    session,
    services,
    user_id: str,
    profile_context: ProfileContext,
    reminder_settings: dict,
    timezone: str,
) -> None:
    await services.calendar.sync_user_events(user_id, profile_context)
    user_events = await services.calendar.upcoming(user_id, 370)
    for user_event in user_events:
        await services.reminders.create_reminders_for_event(user_event, reminder_settings, timezone)


async def show_home(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        profile = await services.onboarding.load_profile(str(user.id))
        if profile is None:
            await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
            return

        events = await services.calendar.upcoming(str(user.id), 7)
        balance = await services.finance.balance(str(user.id))
        sub = await services.subscription.get_subscription(str(user.id))
        can_ai, remaining = await services.subscription.can_use_ai(user, sub)
        next_event = events[0] if events else None
        planned = _planned_entity_label(profile)

        lines = [
            "🏠 *Главная*",
            f"👤 {planned or _entity_label(profile.entity_type.value)} | {_tax_regime_label(profile.tax_regime.value)}",
            f"💰 Баланс: *{_format_money(balance['balance'])}* ₽",
            f"📈 Доходы: {_format_money(balance['income'])} ₽ | 📉 Расходы: {_format_money(balance['expense'])} ₽",
        ]
        if next_event is not None:
            title = next_event.calendar_event.title if next_event.calendar_event else "Событие"
            lines.append(f"📅 Ближайшее: *{title}* до {next_event.due_date.isoformat()}")
        else:
            lines.append("📅 Ближайших дедлайнов нет")

        if not services.subscription.is_active(sub):
            lines.append(f"💬 AI-запросов сегодня: *{remaining}*")

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
        f"Тип: *{planned or _entity_label(profile.entity_type.value)}*\n"
        f"Режим: *{_tax_regime_label(profile.tax_regime.value)}*\n"
        f"Сотрудники: {'да' if profile.has_employees else 'нет'}\n"
        f"Маркетплейсы: {'да' if profile.marketplaces_enabled else 'нет'}\n"
        f"Регион: {profile.region}"
    )
    await respond(message, text, reply_markup=profile_shortcuts_keyboard(), edit=edit)


async def show_events(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        events = await services.calendar.upcoming(str(user.id), 14)
        if not events:
            await respond(message, "📅 На ближайшие 14 дней событий нет.", reply_markup=section_shortcuts_keyboard(), edit=edit)
            return
        lines = ["📅 *Ближайшие события:*\n"]
        for item in events[:5]:
            title = item.calendar_event.title if item.calendar_event else "Событие"
            lines.append(f"• *{title}* — до {item.due_date.isoformat()}")
        await respond(message, "\n".join(lines), reply_markup=event_actions_keyboard(str(events[0].id)), edit=edit)


async def show_calendar(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        events = await services.calendar.upcoming(str(user.id), 30)
        if not events:
            await respond(message, "📅 На ближайшие 30 дней событий нет.", reply_markup=section_shortcuts_keyboard(), edit=edit)
            return
        lines = ["📅 *Календарь на 30 дней:*\n"]
        for item in events[:10]:
            title = item.calendar_event.title if item.calendar_event else "Событие"
            lines.append(f"{item.due_date.isoformat()} — {title}")
        await respond(message, "\n".join(lines), reply_markup=section_shortcuts_keyboard(), edit=edit)


async def show_overdue(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        events = await services.calendar.overdue(str(user.id))
        overdue = [item for item in events if item.due_date < date.today()]
        if not overdue:
            await respond(message, "✅ Просроченных событий нет!", reply_markup=section_shortcuts_keyboard(), edit=edit)
            return
        lines = ["🔴 *Просроченные события:*\n"]
        for item in overdue[:10]:
            title = item.calendar_event.title if item.calendar_event else "Событие"
            lines.append(f"• *{title}* — до {item.due_date.isoformat()}")
        await respond(message, "\n".join(lines), reply_markup=section_shortcuts_keyboard(), edit=edit)


async def show_documents(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        documents = await services.documents.upcoming_documents(str(user.id))
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
    s = profile.reminder_settings
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
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        profile = await services.onboarding.load_profile(str(user.id))
        report = await services.finance.report(str(user.id), date.today() - timedelta(days=30), date.today())
        tax_base = report["totals"]["income"]
        if profile is not None and profile.tax_regime == TaxRegime.USN_INCOME_EXPENSE:
            tax_base = report["profit"]
        lines = [
            "📊 *Финансы за 30 дней*\n",
            f"📈 Доходы: *{_format_money(report['totals']['income'])}* ₽",
            f"📉 Расходы: *{_format_money(report['totals']['expense'])}* ₽",
            f"💰 Прибыль: *{_format_money(report['profit'])}* ₽",
            f"📋 Налоговая база: {_format_money(tax_base)} ₽",
        ]
        if report["top_expenses"]:
            top = ", ".join(f"{_category_label(FinanceRecordType.EXPENSE, cat)}: {amt}" for cat, amt in report["top_expenses"][:3])
            lines.append(f"\nТоп расходов: {top}")
        await respond(message, "\n".join(lines), reply_markup=finance_shortcuts_keyboard(), edit=edit)


async def show_balance(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        balance = await services.finance.balance(str(user.id))
        text = (
            "💰 *Баланс за текущий месяц*\n\n"
            f"📈 Доходы: *{_format_money(balance['income'])}* ₽\n"
            f"📉 Расходы: *{_format_money(balance['expense'])}* ₽\n"
            f"💰 Баланс: *{_format_money(balance['balance'])}* ₽"
        )
        await respond(message, text, reply_markup=finance_shortcuts_keyboard(), edit=edit)


async def show_record_list(message: Message, record_type: FinanceRecordType, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        records = await services.finance.list_records(str(user.id), record_type=record_type, limit=20)
        emoji = "📈" if record_type == FinanceRecordType.INCOME else "📉"
        title = "Доходы" if record_type == FinanceRecordType.INCOME else "Расходы"
        await respond(message, f"{emoji} *{title}:*\n\n{_format_records(records)}", reply_markup=finance_shortcuts_keyboard(), edit=edit)


async def show_laws(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        profile = await services.onboarding.load_profile(str(user.id))
        if profile is None:
            await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
            return
        context = ProfileContext(
            entity_type=profile.entity_type, tax_regime=profile.tax_regime,
            has_employees=profile.has_employees, marketplaces_enabled=profile.marketplaces_enabled,
            region=profile.region, industry=profile.industry,
            reminder_offsets=profile.reminder_settings.get("offset_days", [3, 1]),
        )
        updates = await services.laws.relevant_updates(context, min_importance=70)
        if not updates:
            await respond(message, "📰 Новых обновлений для твоего профиля нет.", reply_markup=laws_shortcuts_keyboard(), edit=edit)
            return
        lines = ["📰 *Новости законов:*\n"]
        for item in updates[:5]:
            effective = item.effective_date.isoformat() if item.effective_date else "дата не указана"
            lines.append(f"• *{item.title}*\n  Вступает: {effective}")
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
    settings = get_settings()
    actor = actor or message.from_user
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        sub = await services.subscription.get_subscription(str(user.id))
        is_active = services.subscription.is_active(sub)
        if is_active:
            plan_label = PLAN_DETAILS.get(sub.plan, {}).get("label", "Активна")
            expires = sub.expires_at.strftime("%d.%m.%Y") if sub.expires_at else "—"
            text = subscription_status_text(plan_label, expires, True)
            await respond(message, text, reply_markup=subscription_manage_keyboard(), edit=edit)
        else:
            prices = {
                "basic": settings.stars_price_basic,
                "pro": settings.stars_price_pro,
                "annual": settings.stars_price_annual,
            }
            can_ai, remaining = await services.subscription.can_use_ai(user, sub)
            text = paywall_text(remaining)
            await respond(message, text, reply_markup=subscription_keyboard(prices), edit=edit)


async def show_referral(message: Message, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    from bot.messages import referral_text

    actor = actor or message.from_user
    bot_info = await message.bot.me()
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        from sqlalchemy import select, func
        from shared.db.models import User
        result = await session.execute(
            select(func.count()).select_from(User).where(User.referred_by == str(actor.id))
        )
        ref_count = result.scalar() or 0
        text = referral_text(bot_info.username, actor.id, ref_count, user.referral_bonus_requests)
        await respond(message, text, reply_markup=section_shortcuts_keyboard(), edit=edit)


async def show_ai_consult(message: Message, state, actor: TelegramUser | None = None, *, edit: bool = False) -> None:
    from bot.keyboards import ai_consult_keyboard, ai_consult_reply_keyboard
    from bot.messages import ai_consult_welcome_text
    from bot.states import AIConsultStates

    settings = get_settings()
    actor = actor or message.from_user
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        sub = await services.subscription.get_subscription(str(user.id))
        is_active = services.subscription.is_active(sub)
        can_use, remaining = await services.subscription.can_use_ai(user, sub)

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
    from bot.keyboards import ai_consult_keyboard, subscription_keyboard
    from backend.services.rate_limit import allow_ai_request

    settings = get_settings()
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        sub = await services.subscription.get_subscription(str(user.id))
        can_use, remaining = await services.subscription.can_use_ai(user, sub)

        if not can_use:
            prices = {
                "basic": settings.stars_price_basic,
                "pro": settings.stars_price_pro,
                "annual": settings.stars_price_annual,
            }
            await message.answer(paywall_text(0), reply_markup=subscription_keyboard(prices), parse_mode="Markdown")
            return

        if not await allow_ai_request(settings, str(user.id)):
            await message.answer("⚠️ Слишком много запросов. Подожди минуту и повтори.", parse_mode="Markdown")
            return

        await message.bot.send_chat_action(message.chat.id, "typing")

        profile = await services.onboarding.load_profile(str(user.id))

        from sqlalchemy import select, desc
        from shared.db.models import AIDialog
        result = await session.execute(
            select(AIDialog)
            .where(AIDialog.user_id == user.id)
            .order_by(desc(AIDialog.created_at))
            .limit(5)
        )
        dialogs = list(reversed(result.scalars().all()))
        history = []
        for d in dialogs:
            history.append({"role": "user", "content": d.question})
            history.append({"role": "assistant", "content": d.answer})

        response = await services.ai.answer_tax_question(
            question,
            {
                "entity_type": profile.entity_type.value if profile else None,
                "tax_regime": profile.tax_regime.value if profile else None,
                "has_employees": profile.has_employees if profile else None,
            },
            history=history,
        )

        session.add(AIDialog(user_id=user.id, question=question, answer=response.text, sources=response.sources))
        await services.subscription.increment_ai_usage(user)
        await session.commit()

        is_active = services.subscription.is_active(sub)
        footer = ""
        if not is_active:
            _, new_remaining = await services.subscription.can_use_ai(user, sub)
            if new_remaining <= 2:
                footer = f"\n\n💬 Осталось запросов: *{new_remaining}*"

    await message.answer(response.text + footer, reply_markup=ai_consult_keyboard(), parse_mode="Markdown")


async def prompt_finance_input(message: Message, state, record_kind: str, *, edit: bool = False) -> None:
    from bot.states import FinanceInputStates

    if record_kind == "income":
        await state.set_state(FinanceInputStates.income)
        text = "💰 Напиши доход одной фразой.\nПример: _получил 50к от клиента_"
    else:
        await state.set_state(FinanceInputStates.expense)
        text = "💸 Напиши расход одной фразой.\nПример: _заплатил 12к за рекламу_"
    await respond(message, text, reply_markup=finance_shortcuts_keyboard(), edit=edit)


async def start_regime_picker(message: Message, state) -> None:
    from bot.keyboards import regime_activity_keyboard
    from bot.states import RegimeSelectionStates

    await state.clear()
    await state.set_state(RegimeSelectionStates.activity)
    await message.answer("🔍 *Подбор режима* (1/5)\n\nЧем занимаешься?", reply_markup=regime_activity_keyboard(), parse_mode="Markdown")


async def handle_tax_calculation(message: Message, raw_query: str, *, force: bool = False) -> bool:
    from backend.services.tax_engine import TaxQueryParser

    if not force and not TaxQueryParser.looks_like_calculation_request(raw_query):
        return False
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        profile = await services.onboarding.load_profile(str(user.id))
        parsed = TaxQueryParser.parse(
            raw_query,
            {
                "entity_type": profile.entity_type.value if profile else None,
                "tax_regime": profile.tax_regime.value if profile else None,
                "has_employees": profile.has_employees if profile else False,
            },
        )
        if parsed.question:
            await message.answer(parsed.question)
            return True
        if parsed.request is None:
            return False
        result = services.tax.calculate(parsed.request)
        await message.answer(result.render(), reply_markup=main_menu_keyboard())
        return True


async def check_ai_limit(message: Message, user, sub) -> bool:
    settings = get_settings()
    async with SessionFactory() as session:
        services = build_services(session)
        can_use, remaining = await services.subscription.can_use_ai(user, sub)
        if not can_use:
            prices = {
                "basic": settings.stars_price_basic,
                "pro": settings.stars_price_pro,
                "annual": settings.stars_price_annual,
            }
            await message.answer(paywall_text(0), reply_markup=subscription_keyboard(prices), parse_mode="Markdown")
            return False
        if remaining <= 1 and not services.subscription.is_active(sub):
            await message.answer("⚠️ Это последний бесплатный AI-запрос сегодня.", parse_mode="Markdown")
        return True
