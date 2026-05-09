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
        amount = _h.TaxQueryParser.parse_amount(message.text or "")
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
        try:
            monthly_income = Decimal(str(payload["monthly_income"]))
        except (KeyError, InvalidOperation):
            await state.clear()
            await message.answer("Не удалось собрать данные. Начни заново: /regime")
            return
        async with _h.SessionFactory() as session:
            services = _h.build_services(session)
            result = services.tax.compare_regimes(
                activity=payload["activity"], monthly_income=monthly_income,
                has_employees=payload["has_employees"], counterparties=payload["counterparties"],
                region=message.text.strip(),
            )
        await state.clear()
        await message.answer(result.render(), reply_markup=main_menu_keyboard())


async def handle_tax_calculation(message: Message, raw_query: str, *, force: bool = False) -> bool:
    if not force and not _h.TaxQueryParser.looks_like_calculation_request(raw_query):
        return False
    async with _h.SessionFactory() as session:
        services = _h.build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        profile = await services.onboarding.load_profile(str(user.id))
        parsed = _h.TaxQueryParser.parse(
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
