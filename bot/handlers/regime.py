"""Tax regime picker — 5-step FSM flow."""

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import bot.handlers.helpers as _h
from bot.keyboards import (
    counterparties_keyboard,
    main_menu_keyboard,
    regime_activity_keyboard,
    regime_income_keyboard,
    yes_no_keyboard,
)
from bot.states import RegimeSelectionStates


def register_regime_handlers(router: Router) -> None:
    async def start_regime_picker(message: Message, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(RegimeSelectionStates.activity)
        await message.answer("🔍 *Подбор режима* (1/5)\n\nЧем занимаешься?", reply_markup=regime_activity_keyboard(), parse_mode="Markdown")

    router._start_regime_picker = start_regime_picker  # noqa: SLF001

    @router.message(Command("regime"))
    @router.message(Command("choose_regime"))
    @router.message(F.text == "🔍 Подобрать режим")
    async def regime_handler(message: Message, state: FSMContext) -> None:
        await start_regime_picker(message, state)

    @router.message(Command("calc"))
    async def calc_handler(message: Message) -> None:
        payload = message.text.partition(" ")[2].strip()
        if not payload:
            await message.answer("Пришли запрос так: /calc усн 6 доход 500000", parse_mode="Markdown")
            return
        handled = await handle_tax_calculation(message, payload, force=True)
        if not handled:
            await message.answer("Не понял режим или сумму.\nПример: /calc самозанятый доход 120к от физлиц", parse_mode="Markdown")

    @router.message(RegimeSelectionStates.activity)
    async def regime_activity_handler(message: Message, state: FSMContext) -> None:
        if message.text not in _h.REGIME_ACTIVITY_MAP:
            await message.answer("Выбери из кнопок 👇")
            return
        await state.update_data(activity=_h.REGIME_ACTIVITY_MAP[message.text])
        await state.set_state(RegimeSelectionStates.monthly_income)
        await message.answer("🔍 *(2/5)* Доход в месяц?", reply_markup=regime_income_keyboard(), parse_mode="Markdown")

    @router.message(RegimeSelectionStates.monthly_income)
    async def regime_income_handler(message: Message, state: FSMContext) -> None:
        raw = (message.text or "").strip().lower().replace(" ", "")
        amount = _parse_amount(raw)
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
        if message.text not in _h.COUNTERPARTIES_MAP:
            await message.answer("Выбери из кнопок 👇")
            return
        await state.update_data(counterparties=_h.COUNTERPARTIES_MAP[message.text])
        await state.set_state(RegimeSelectionStates.region)
        await message.answer("🔍 *(5/5)* Укажи регион:", parse_mode="Markdown")

    @router.message(RegimeSelectionStates.region)
    async def regime_region_handler(message: Message, state: FSMContext) -> None:
        payload = await state.get_data()
        monthly_income = payload.get("monthly_income", "0")
        client = _h._get_client()
        result = await client.compare_regimes(
            activity=payload.get("activity", "other"),
            monthly_income=monthly_income,
            has_employees=payload.get("has_employees", False),
            counterparties=payload.get("counterparties", "mixed"),
            region=message.text.strip(),
        )
        await state.clear()
        rendered = result.get("rendered", "Ошибка расчёта.")
        await message.answer(rendered, reply_markup=main_menu_keyboard())


def _parse_amount(raw: str) -> Decimal | None:
    raw = raw.replace(",", ".").replace("₽", "").replace("руб", "").strip()
    multiplier = 1
    if raw.endswith("к") or raw.endswith("k"):
        multiplier = 1000
        raw = raw[:-1]
    elif raw.endswith("м") or raw.endswith("m") or raw.endswith("млн"):
        multiplier = 1_000_000
        raw = raw.rstrip("млнm")
    try:
        return Decimal(raw) * multiplier
    except (InvalidOperation, ValueError):
        return None


async def handle_tax_calculation(message: Message, raw_query: str, *, force: bool = False) -> bool:
    client = _h._get_client()
    result = await client.parse_and_calculate_tax(message.from_user.id, raw_query)

    if not result.get("ok"):
        if force:
            return False
        return False

    if result.get("question"):
        await message.answer(result["question"])
        return True

    rendered = result.get("result")
    if rendered:
        await message.answer(rendered, reply_markup=main_menu_keyboard())
        return True

    return False
