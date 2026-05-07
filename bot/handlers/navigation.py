"""Navigation callbacks and catch-all handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.backend_client import BackendClient
from bot.callbacks import NavigationCallback, PageCallback
from bot.handlers._helpers import (
    AI_TOPIC_PROMPTS,
    INCOME_CATEGORY_LABELS,
    MAIN_MENU_BUTTONS,
    respond,
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


def register(parent_router: Router, client: BackendClient) -> None:
    from bot.handlers.ai_consult import do_ai_answer, show_ai_consult
    from bot.handlers.events import (
        show_calendar,
        show_documents,
        show_events,
        show_laws,
        show_overdue,
        show_reminders,
    )
    from bot.handlers.finance import (
        prompt_finance_input,
        show_balance,
        show_finance,
        show_record_list,
    )
    from bot.handlers.help import show_help
    from bot.handlers.profile import show_profile, show_settings
    from bot.handlers.regime import start_regime_picker
    from bot.handlers.start import show_home
    from bot.handlers.subscription import show_referral, show_subscription

    @parent_router.callback_query(NavigationCallback.filter())
    async def navigation_handler(query: CallbackQuery, callback_data: NavigationCallback, state: FSMContext) -> None:
        message = query.message
        if message is None:
            await query.answer()
            return
        target = callback_data.target

        target_map = {
            "home": lambda: show_home(message, client, query.from_user, edit=True),
            "profile": lambda: show_profile(message, client, query.from_user, edit=True),
            "events": lambda: show_events(message, client, query.from_user, edit=True),
            "calendar": lambda: show_calendar(message, client, query.from_user, edit=True),
            "overdue": lambda: show_overdue(message, client, query.from_user, edit=True),
            "documents": lambda: show_documents(message, client, query.from_user, edit=True),
            "reminders": lambda: show_reminders(message, client, query.from_user, edit=True),
            "laws": lambda: show_laws(message, client, query.from_user, edit=True),
            "finance": lambda: show_finance(message, client, query.from_user, edit=True),
            "balance": lambda: show_balance(message, client, query.from_user, edit=True),
            "income_list": lambda: show_record_list(message, client, "income", query.from_user, edit=True),
            "expense_list": lambda: show_record_list(message, client, "expense", query.from_user, edit=True),
            "income_prompt": lambda: prompt_finance_input(message, state, "income", edit=True),
            "expense_prompt": lambda: prompt_finance_input(message, state, "expense", edit=True),
            "pick_regime": lambda: start_regime_picker(message, state),
            "settings": lambda: show_settings(message, edit=True),
            "help": lambda: show_help(message, edit=True),
            "subscription": lambda: show_subscription(message, client, query.from_user, edit=True),
            "referral": lambda: show_referral(message, client, query.from_user, edit=True),
            "ai_consult": lambda: show_ai_consult(message, client, state, query.from_user, edit=True),
        }

        if target in AI_TOPIC_PROMPTS:
            await state.set_state(AIConsultStates.chatting)
            await query.answer()
            await do_ai_answer(message, client, AI_TOPIC_PROMPTS[target])
            return

        if target == "ai_clear_history":
            user_data = await client.ensure_user(
                telegram_id=query.from_user.id, username=query.from_user.username,
                first_name=query.from_user.first_name, timezone="Europe/Moscow",
            )
            await client.clear_ai_history(user_data["user_id"])
            await respond(message, "🗑 История очищена!\n\nЗадай новый вопрос 👇", reply_markup=ai_consult_keyboard(), edit=True)
            await query.answer("История очищена")
            return

        if target == "ai_exit":
            await state.clear()
            await show_home(message, client, query.from_user, edit=True)
            await query.answer()
            return

        if target == "restart_onboarding":
            await state.clear()
            await state.set_state(OnboardingStates.entity_type)
            await respond(message, welcome_text(query.from_user.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=True)
            await query.answer()
            return

        if target == "cancel_subscription":
            user_data = await client.ensure_user(
                telegram_id=query.from_user.id, username=query.from_user.username,
                first_name=query.from_user.first_name, timezone="Europe/Moscow",
            )
            await client.cancel_subscription(user_data["user_id"])
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

    @parent_router.callback_query(PageCallback.filter())
    async def page_handler(query: CallbackQuery, callback_data: PageCallback) -> None:
        await query.answer("Скоро будет!", show_alert=False)

    @parent_router.message(F.content_type.in_({"sticker", "voice", "video_note", "photo", "document", "video", "audio", "contact", "location"}))
    async def unsupported_content_handler(message: Message) -> None:
        await message.answer("Я пока работаю только с текстом. Напиши вопрос или выбери раздел 👇", reply_markup=main_menu_keyboard())

    @parent_router.message()
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
            user_data = await client.ensure_user(
                telegram_id=message.from_user.id, username=message.from_user.username,
                first_name=message.from_user.first_name, timezone="Europe/Moscow",
            )
            try:
                result = await client.add_finance_text(user_data["user_id"], raw_text)
                if result.get("record"):
                    record = result["record"]
                    label = INCOME_CATEGORY_LABELS.get(record.get("category", ""), record.get("category", ""))
                    kind = "доход" if record.get("record_type") == "income" else "расход"
                    await message.answer(
                        f"✅ Сохранил {kind}: *{record.get('amount', '')}* ₽, категория _{label}_",
                        reply_markup=finance_shortcuts_keyboard(),
                        parse_mode="Markdown",
                    )
                    return
            except Exception:
                pass

        # Try template match
        try:
            template_data = await client.match_template(raw_text)
            template = template_data.get("template")
            if template:
                await message.answer(template, reply_markup=main_menu_keyboard())
                return
        except Exception:
            pass

        # Try tax calculation
        try:
            tax_result = await client.parse_tax_query(raw_text)
            rendered = tax_result.get("rendered")
            if rendered:
                await message.answer(rendered, reply_markup=main_menu_keyboard())
                return
        except Exception:
            pass

        # AI question
        user_data = await client.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        user_id = user_data["user_id"]
        sub_data = await client.subscription_status(user_id)
        is_active = sub_data.get("is_active", False)
        remaining = sub_data.get("remaining_ai_requests", 0)
        can_use = sub_data.get("can_use_ai", remaining > 0 or is_active)

        if not can_use:
            prices = {
                "basic": settings.stars_price_basic,
                "pro": settings.stars_price_pro,
                "annual": settings.stars_price_annual,
            }
            await message.answer(paywall_text(0), reply_markup=subscription_keyboard(prices), parse_mode="Markdown")
            return

        await message.bot.send_chat_action(message.chat.id, "typing")

        result = await client.ask_ai_with_history(user_id, raw_text)
        answer_text = result.get("answer", "Не удалось получить ответ.")
        await message.answer(answer_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
