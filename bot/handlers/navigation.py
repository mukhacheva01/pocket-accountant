"""Navigation callbacks, catch-all handlers, unsupported content."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import bot.handlers.helpers as _h
from bot.callbacks import NavigationCallback, PageCallback
from bot.keyboards import (
    ai_consult_keyboard,
    finance_shortcuts_keyboard,
    main_menu_keyboard,
    onboarding_entity_type_keyboard,
    section_shortcuts_keyboard,
    subscription_keyboard,
)
from bot.messages import paywall_text
from bot.states import AIConsultStates, OnboardingStates


def register_navigation_handlers(router: Router) -> None:
    from bot.handlers.ai_consult import do_ai_answer, show_ai_consult as show_ai_consult_fn
    from bot.handlers.regime import handle_tax_calculation

    @router.callback_query(NavigationCallback.filter())
    async def navigation_handler(query: CallbackQuery, callback_data: NavigationCallback, state: FSMContext) -> None:
        message = query.message
        if message is None:
            await query.answer()
            return
        target = callback_data.target

        prompt_finance_input = getattr(router, "_prompt_finance_input", None)
        start_regime_picker = getattr(router, "_start_regime_picker", None)

        target_map = {
            "home": lambda: _h.show_home(message, query.from_user, edit=True),
            "profile": lambda: _h.show_profile(message, query.from_user, edit=True),
            "events": lambda: _h.show_events(message, query.from_user, edit=True),
            "calendar": lambda: _h.show_calendar(message, query.from_user, edit=True),
            "overdue": lambda: _h.show_overdue(message, query.from_user, edit=True),
            "documents": lambda: _h.show_documents(message, query.from_user, edit=True),
            "reminders": lambda: _h.show_reminders(message, query.from_user, edit=True),
            "laws": lambda: _h.show_laws(message, query.from_user, edit=True),
            "finance": lambda: _h.show_finance(message, query.from_user, edit=True),
            "balance": lambda: _h.show_balance(message, query.from_user, edit=True),
            "income_list": lambda: _h.show_record_list(message, "income", query.from_user, edit=True),
            "expense_list": lambda: _h.show_record_list(message, "expense", query.from_user, edit=True),
            "settings": lambda: _h.show_settings(message, edit=True),
            "help": lambda: _h.show_help(message, edit=True),
            "subscription": lambda: _h.show_subscription(message, query.from_user, edit=True),
            "referral": lambda: _h.show_referral(message, query.from_user, edit=True),
            "ai_consult": lambda: show_ai_consult_fn(message, state, query.from_user, edit=True),
        }

        if prompt_finance_input:
            target_map["income_prompt"] = lambda: prompt_finance_input(message, state, "income", edit=True)
            target_map["expense_prompt"] = lambda: prompt_finance_input(message, state, "expense", edit=True)
        if start_regime_picker:
            target_map["pick_regime"] = lambda: start_regime_picker(message, state)

        if target in _h.AI_TOPIC_PROMPTS:
            await state.set_state(AIConsultStates.chatting)
            await query.answer()
            await do_ai_answer(message, _h.AI_TOPIC_PROMPTS[target])
            return

        if target == "ai_clear_history":
            client = _h._get_client()
            await client.ai_clear_history(query.from_user.id)
            await _h.respond(message, "🗑 История очищена!\n\nЗадай новый вопрос 👇", reply_markup=ai_consult_keyboard(), edit=True)
            await query.answer("История очищена")
            return

        if target == "ai_exit":
            await state.clear()
            await _h.show_home(message, query.from_user, edit=True)
            await query.answer()
            return

        if target == "restart_onboarding":
            await state.clear()
            await state.set_state(OnboardingStates.entity_type)
            await _h.respond(message, _h.welcome_text(query.from_user.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=True)
            await query.answer()
            return
        if target == "cancel_subscription":
            client = _h._get_client()
            await client.cancel_subscription(query.from_user.id)
            await _h.respond(
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

    @router.callback_query(PageCallback.filter())
    async def page_handler(query: CallbackQuery, callback_data: PageCallback) -> None:
        await query.answer("Скоро будет!", show_alert=False)

    @router.message(F.content_type.in_({"sticker", "voice", "video_note", "photo", "document", "video", "audio", "contact", "location"}))
    async def unsupported_content_handler(message: Message) -> None:
        await message.answer("Я пока работаю только с текстом. Напиши вопрос или выбери раздел 👇", reply_markup=main_menu_keyboard())

    @router.message()
    async def ai_question_handler(message: Message, state: FSMContext) -> None:
        if await state.get_state() is not None:
            return
        if message.text in _h.MAIN_MENU_BUTTONS:
            return

        raw_text = (message.text or "").strip()
        if not raw_text:
            return

        settings = _h.get_settings()
        normalized = raw_text.lower()
        finance_hints = ("получил", "пришло", "поступление", "заплатил", "оплатил", "потратил", "доход", "расход")
        tax_hints = ("налог", "усн", "нпд", "осно", "патент", "псн", "ндс", "режим", "ставка")

        if any(hint in normalized for hint in finance_hints) and not any(hint in normalized for hint in tax_hints):
            client = _h._get_client()
            result = await client.add_from_text(message.from_user.id, raw_text)
            if result.get("ok"):
                record_type = result.get("record_type", "expense")
                amount = result.get("amount", "0")
                category = result.get("category", "other")
                label = _h._category_label(record_type, category)
                kind = "доход" if record_type == "income" else "расход"
                await message.answer(
                    f"✅ Сохранил {kind}: *{amount}* ₽, категория _{label}_",
                    reply_markup=finance_shortcuts_keyboard(),
                    parse_mode="Markdown",
                )
                return

        client = _h._get_client()
        template_result = await client.match_template(raw_text)
        if template_result.get("matched"):
            await message.answer(template_result["response"], reply_markup=main_menu_keyboard())
            return

        if await handle_tax_calculation(message, raw_text):
            return

        result = await client.ai_full_question(message.from_user.id, raw_text)
        if not result.get("ok"):
            error = result.get("error", "")
            if error == "paywall":
                sub_data = await client.get_subscription_status(message.from_user.id)
                prices = sub_data.get("prices", {})
                await message.answer(paywall_text(0), reply_markup=subscription_keyboard(prices), parse_mode="Markdown")
                return
            if error == "rate_limit":
                await message.answer("⚠️ Слишком много запросов. Подожди минуту и повтори.", parse_mode="Markdown")
                return

        await message.answer(result.get("answer", ""), reply_markup=main_menu_keyboard(), parse_mode="Markdown")
