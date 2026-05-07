"""Onboarding flow handlers."""

from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.backend_client import BackendClient
from bot.handlers._helpers import (
    ENTITY_TYPE_MAP,
    PLANNED_ENTITY_TEXT,
    TAX_REGIME_MAP,
)
from bot.keyboards import (
    main_menu_keyboard,
    onboarding_tax_keyboard,
    planned_entity_type_keyboard,
    yes_no_keyboard,
)
from bot.messages import onboarding_complete_text
from bot.states import OnboardingStates


def register(parent_router: Router, client: BackendClient) -> None:
    @parent_router.message(OnboardingStates.entity_type)
    async def onboarding_entity_handler(message: Message, state: FSMContext) -> None:
        if message.text == PLANNED_ENTITY_TEXT:
            await state.update_data(planning_entity=True)
            await message.answer("Что планируешь открыть?", reply_markup=planned_entity_type_keyboard())
            return
        if message.text not in ENTITY_TYPE_MAP:
            await message.answer("Выбери из кнопок 👇")
            return
        entity_type = ENTITY_TYPE_MAP[message.text]
        await state.update_data(entity_type=entity_type)
        if entity_type == "self_employed":
            await state.update_data(tax_regime="npd", has_employees=False)
            await state.set_state(OnboardingStates.region)
            await message.answer("📍 *Шаг 2/3.* Укажи регион:", parse_mode="Markdown")
            return
        await state.set_state(OnboardingStates.tax_regime)
        await message.answer("📋 *Шаг 2/4.* Налоговый режим:", reply_markup=onboarding_tax_keyboard(), parse_mode="Markdown")

    @parent_router.message(OnboardingStates.tax_regime)
    async def onboarding_tax_handler(message: Message, state: FSMContext) -> None:
        if message.text not in TAX_REGIME_MAP:
            await message.answer("Выбери режим из кнопок 👇")
            return
        await state.update_data(tax_regime=TAX_REGIME_MAP[message.text])
        await state.set_state(OnboardingStates.has_employees)
        await message.answer("👥 *Шаг 3/4.* Есть сотрудники?", reply_markup=yes_no_keyboard(), parse_mode="Markdown")

    @parent_router.message(OnboardingStates.has_employees)
    async def onboarding_employees_handler(message: Message, state: FSMContext) -> None:
        if message.text not in {"Да", "Нет"}:
            await message.answer("Нажми Да или Нет.")
            return
        await state.update_data(has_employees=message.text == "Да")
        await state.set_state(OnboardingStates.region)
        await message.answer("📍 *Последний шаг.* Укажи регион:", parse_mode="Markdown")

    @parent_router.message(OnboardingStates.region)
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

        user_data = await client.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        user_id = user_data["user_id"]
        await client.complete_onboarding_full(
            user_id=user_id,
            entity_type=entity_type_val,
            tax_regime=tax_regime_val,
            has_employees=payload.get("has_employees", False),
            region=message.text.strip(),
            planning_entity=bool(payload.get("planning_entity")),
        )

        await state.clear()
        await message.answer(onboarding_complete_text(), reply_markup=main_menu_keyboard(), parse_mode="Markdown")
