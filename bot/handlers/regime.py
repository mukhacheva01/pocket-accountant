"""Tax regime selection handlers."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers._helpers import (
    COUNTERPARTIES_MAP,
    REGIME_ACTIVITY_MAP,
    handle_tax_calculation,
    start_regime_picker,
)
from bot.keyboards import (
    counterparties_keyboard,
    main_menu_keyboard,
    regime_income_keyboard,
    yes_no_keyboard,
)
from bot.states import RegimeSelectionStates
from shared.db.session import SessionFactory
from backend.services.container import build_services
from backend.services.tax_engine import TaxQueryParser


router = Router()


@router.message(Command("calc"))
async def calc_handler(message: Message) -> None:
    payload = message.text.partition(" ")[2].strip()
    if not payload:
        await message.answer("Пришли запрос так: /calc усн 6 доход 500000", parse_mode="Markdown")
        return
    handled = await handle_tax_calculation(message, payload, force=True)
    if not handled:
        await message.answer("Не понял режим или сумму.\nПример: /calc самозанятый доход 120к от физлиц", parse_mode="Markdown")


@router.message(Command("regime"))
@router.message(Command("choose_regime"))
@router.message(F.text == "🔍 Подобрать режим")
async def regime_handler(message: Message, state: FSMContext) -> None:
    await start_regime_picker(message, state)


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
    amount = TaxQueryParser.parse_amount(message.text or "")
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
    async with SessionFactory() as session:
        services = build_services(session)
        result = services.tax.compare_regimes(
            activity=payload["activity"], monthly_income=monthly_income,
            has_employees=payload["has_employees"], counterparties=payload["counterparties"],
            region=message.text.strip(),
        )
    await state.clear()
    await message.answer(result.render(), reply_markup=main_menu_keyboard())
