"""FSM onboarding handlers — entity type, tax regime, employees, region."""

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import bot.handlers.helpers as _h
from bot.keyboards import (
    main_menu_keyboard,
    onboarding_entity_type_keyboard,
    onboarding_tax_keyboard,
    planned_entity_type_keyboard,
    yes_no_keyboard,
)
from bot.messages import onboarding_complete_text
from bot.states import OnboardingStates
from shared.db.enums import EntityType, TaxRegime
from backend.services.onboarding import OnboardingDraft
from backend.services.profile_matching import ProfileContext


def register_onboarding_handlers(router: Router) -> None:
    @router.message(OnboardingStates.entity_type)
    async def onboarding_entity_handler(message: Message, state: FSMContext) -> None:
        if message.text == _h.PLANNED_ENTITY_TEXT:
            await state.update_data(planning_entity=True)
            await message.answer("Что планируешь открыть?", reply_markup=planned_entity_type_keyboard())
            return
        if message.text not in _h.ENTITY_TYPE_MAP:
            await message.answer("Выбери из кнопок 👇")
            return
        entity_type = _h.ENTITY_TYPE_MAP[message.text]
        await state.update_data(entity_type=entity_type.value)
        if entity_type == EntityType.SELF_EMPLOYED:
            await state.update_data(tax_regime=TaxRegime.NPD.value, has_employees=False)
            await state.set_state(OnboardingStates.region)
            await message.answer("📍 *Шаг 2/3.* Укажи регион:", parse_mode="Markdown")
            return
        await state.set_state(OnboardingStates.tax_regime)
        await message.answer("📋 *Шаг 2/4.* Налоговый режим:", reply_markup=onboarding_tax_keyboard(), parse_mode="Markdown")

    @router.message(OnboardingStates.tax_regime)
    async def onboarding_tax_handler(message: Message, state: FSMContext) -> None:
        if message.text not in _h.TAX_REGIME_MAP:
            await message.answer("Выбери режим из кнопок 👇")
            return
        await state.update_data(tax_regime=_h.TAX_REGIME_MAP[message.text].value)
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
            tax_regime_val = TaxRegime.NPD.value

        draft = OnboardingDraft(
            entity_type=EntityType(entity_type_val),
            tax_regime=TaxRegime(tax_regime_val),
            has_employees=payload.get("has_employees", False),
            marketplaces_enabled=False,
            industry=None,
            region=message.text.strip(),
            timezone="Europe/Moscow",
            reminder_settings={
                "notify_taxes": True,
                "notify_reporting": True,
                "notify_documents": True,
                "notify_laws": True,
                "offset_days": [3, 1],
                "planning_entity": bool(payload.get("planning_entity")),
            },
        )

        async with _h.SessionFactory() as session:
            services = _h.build_services(session)
            user = await services.onboarding.ensure_user(
                telegram_id=message.from_user.id, username=message.from_user.username,
                first_name=message.from_user.first_name, timezone=draft.timezone,
            )
            await services.onboarding.save_profile(str(user.id), draft)
            profile_context = ProfileContext(
                entity_type=draft.entity_type, tax_regime=draft.tax_regime,
                has_employees=draft.has_employees, marketplaces_enabled=draft.marketplaces_enabled,
                region=draft.region, industry=draft.industry, reminder_offsets=[3, 1],
            )
            await _h.sync_profile_events_and_reminders(
                session,
                services,
                str(user.id),
                profile_context,
                draft.reminder_settings,
                draft.timezone,
            )
            await session.commit()

        await state.clear()
        await message.answer(onboarding_complete_text(), reply_markup=main_menu_keyboard(), parse_mode="Markdown")
