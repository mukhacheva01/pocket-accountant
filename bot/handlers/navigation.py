"""Navigation callbacks and catch-all handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.callbacks import NavigationCallback, SubscriptionCallback
from bot.handlers._helpers import (
    AI_TOPIC_PROMPTS,
    MAIN_MENU_BUTTONS,
    _category_label,
    _normalize_finance_text,
    do_ai_answer,
    handle_tax_calculation,
    prompt_finance_input,
    respond,
    show_ai_consult,
    show_balance,
    show_events,
    show_calendar,
    show_documents,
    show_finance,
    show_help,
    show_home,
    show_laws,
    show_overdue,
    show_profile,
    show_record_list,
    show_referral,
    show_reminders,
    show_settings,
    show_subscription,
    start_regime_picker,
)
from bot.keyboards import (
    ai_consult_keyboard,
    finance_shortcuts_keyboard,
    main_menu_keyboard,
    onboarding_entity_type_keyboard,
    section_shortcuts_keyboard,
    subscription_keyboard,
)
from bot.messages import paywall_text, welcome_text
from bot.states import AIConsultStates, OnboardingStates
from shared.config import get_settings
from shared.db.enums import FinanceRecordType
from shared.db.session import SessionFactory
from backend.services.container import build_services
from backend.services.rate_limit import allow_ai_request


router = Router()


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
        "income_list": lambda: show_record_list(message, FinanceRecordType.INCOME, query.from_user, edit=True),
        "expense_list": lambda: show_record_list(message, FinanceRecordType.EXPENSE, query.from_user, edit=True),
        "income_prompt": lambda: prompt_finance_input(message, state, "income", edit=True),
        "expense_prompt": lambda: prompt_finance_input(message, state, "expense", edit=True),
        "pick_regime": lambda: start_regime_picker(message, state),
        "settings": lambda: show_settings(message, edit=True),
        "help": lambda: show_help(message, edit=True),
        "subscription": lambda: show_subscription(message, query.from_user, edit=True),
        "referral": lambda: show_referral(message, query.from_user, edit=True),
        "ai_consult": lambda: show_ai_consult(message, state, query.from_user, edit=True),
    }

    if target in AI_TOPIC_PROMPTS:
        await state.set_state(AIConsultStates.chatting)
        await query.answer()
        await do_ai_answer(message, AI_TOPIC_PROMPTS[target])
        return

    if target == "ai_clear_history":
        async with SessionFactory() as session:
            services = build_services(session)
            user = await services.onboarding.ensure_user(
                telegram_id=query.from_user.id, username=query.from_user.username,
                first_name=query.from_user.first_name, timezone="Europe/Moscow",
            )
            from sqlalchemy import delete
            from shared.db.models import AIDialog
            await session.execute(delete(AIDialog).where(AIDialog.user_id == user.id))
            await session.commit()
        await respond(message, "🗑 История очищена!\n\nЗадай новый вопрос 👇", reply_markup=ai_consult_keyboard(), edit=True)
        await query.answer("История очищена")
        return

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
        async with SessionFactory() as session:
            services = build_services(session)
            user = await services.onboarding.ensure_user(
                telegram_id=query.from_user.id, username=query.from_user.username,
                first_name=query.from_user.first_name, timezone="Europe/Moscow",
            )
            await services.subscription.cancel(str(user.id))
            await session.commit()
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


# ── Catch-all handlers (must be registered last) ──

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

    settings = get_settings()
    normalized = raw_text.lower()
    finance_hints = ("получил", "пришло", "поступление", "заплатил", "оплатил", "потратил", "доход", "расход")
    tax_hints = ("налог", "усн", "нпд", "осно", "патент", "псн", "ндс", "режим", "ставка")

    if any(hint in normalized for hint in finance_hints) and not any(hint in normalized for hint in tax_hints):
        async with SessionFactory() as session:
            services = build_services(session)
            user = await services.onboarding.ensure_user(
                telegram_id=message.from_user.id, username=message.from_user.username,
                first_name=message.from_user.first_name, timezone="Europe/Moscow",
            )
            try:
                record = await services.finance.add_from_text(str(user.id), raw_text)
            except ValueError:
                record = None
            if record is not None:
                await session.commit()
                label = _category_label(record.record_type, record.category)
                kind = "доход" if record.record_type == FinanceRecordType.INCOME else "расход"
                await message.answer(
                    f"✅ Сохранил {kind}: *{record.amount}* ₽, категория _{label}_",
                    reply_markup=finance_shortcuts_keyboard(),
                    parse_mode="Markdown",
                )
                return

    async with SessionFactory() as session:
        services = build_services(session)
        template = services.templates.match_template(raw_text)
        if template is not None:
            await message.answer(template, reply_markup=main_menu_keyboard())
            return

    if await handle_tax_calculation(message, raw_text):
        return

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
            raw_text,
            {
                "entity_type": profile.entity_type.value if profile else None,
                "tax_regime": profile.tax_regime.value if profile else None,
                "has_employees": profile.has_employees if profile else None,
            },
            history=history,
        )

        session.add(AIDialog(user_id=user.id, question=raw_text, answer=response.text, sources=response.sources))
        await services.subscription.increment_ai_usage(user)
        await session.commit()

    await message.answer(response.text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
