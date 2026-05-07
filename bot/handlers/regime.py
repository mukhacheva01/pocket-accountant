"""Tax regime selection wizard handlers."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.backend_client import BackendClient
from bot.handlers._helpers import COUNTERPARTIES_MAP, REGIME_ACTIVITY_MAP
from bot.keyboards import (
    counterparties_keyboard,
    main_menu_keyboard,
    regime_activity_keyboard,
    regime_income_keyboard,
    yes_no_keyboard,
)
from bot.states import RegimeSelectionStates


async def start_regime_picker(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(RegimeSelectionStates.activity)
    await message.answer("🔍 *Подбор режима* (1/5)\n\nЧем занимаешься?", reply_markup=regime_activity_keyboard(), parse_mode="Markdown")


def register(parent_router: Router, client: BackendClient) -> None:
    @parent_router.message(Command("regime"))
    @parent_router.message(Command("choose_regime"))
    @parent_router.message(F.text == "🔍 Подобрать режим")
    async def regime_handler(message: Message, state: FSMContext) -> None:
        await start_regime_picker(message, state)

    @parent_router.message(RegimeSelectionStates.activity)
    async def regime_activity_handler(message: Message, state: FSMContext) -> None:
        if message.text not in REGIME_ACTIVITY_MAP:
            await message.answer("Выбери из кнопок 👇")
            return
        await state.update_data(activity=REGIME_ACTIVITY_MAP[message.text])
        await state.set_state(RegimeSelectionStates.monthly_income)
        await message.answer("🔍 *(2/5)* Доход в месяц?", reply_markup=regime_income_keyboard(), parse_mode="Markdown")

    @parent_router.message(RegimeSelectionStates.monthly_income)
    async def regime_income_handler(message: Message, state: FSMContext) -> None:
        raw = (message.text or "").strip().lower()
        raw = raw.replace(" ", "").replace("к", "000").replace("k", "000").replace("м", "000000").replace("m", "000000")
        try:
            amount = Decimal(raw)
        except (InvalidOperation, ValueError):
            await message.answer("Напиши сумму числом. Например: 300000")
            return
        await state.update_data(monthly_income=str(amount))
        await state.set_state(RegimeSelectionStates.has_employees)
        await message.answer("🔍 *(3/5)* Есть сотрудники?", reply_markup=yes_no_keyboard(), parse_mode="Markdown")

    @parent_router.message(RegimeSelectionStates.has_employees)
    async def regime_employees_handler(message: Message, state: FSMContext) -> None:
        if message.text not in {"Да", "Нет"}:
            await message.answer("Нажми Да или Нет.")
            return
        await state.update_data(has_employees=message.text == "Да")
        await state.set_state(RegimeSelectionStates.counterparties)
        await message.answer("🔍 *(4/5)* Кто контрагенты?", reply_markup=counterparties_keyboard(), parse_mode="Markdown")

    @parent_router.message(RegimeSelectionStates.counterparties)
    async def regime_counterparties_handler(message: Message, state: FSMContext) -> None:
        if message.text not in COUNTERPARTIES_MAP:
            await message.answer("Выбери из кнопок 👇")
            return
        await state.update_data(counterparties=COUNTERPARTIES_MAP[message.text])
        await state.set_state(RegimeSelectionStates.region)
        await message.answer("🔍 *(5/5)* Укажи регион:", parse_mode="Markdown")

    @parent_router.message(RegimeSelectionStates.region)
    async def regime_region_handler(message: Message, state: FSMContext) -> None:
        payload = await state.get_data()
        try:
            monthly_income = Decimal(str(payload["monthly_income"]))
        except (KeyError, InvalidOperation):
            await state.clear()
            await message.answer("Не удалось собрать данные. Начни заново: /regime")
            return
        result = await client.compare_regimes(
            activity=payload["activity"],
            monthly_income=monthly_income,
            has_employees=payload["has_employees"],
            counterparties=payload["counterparties"],
            region=message.text.strip(),
        )
        await state.clear()
        rendered = result.get("rendered", result.get("text", "Результат сравнения"))
        await message.answer(rendered, reply_markup=main_menu_keyboard())
