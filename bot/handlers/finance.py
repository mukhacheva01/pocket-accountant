"""Finance handlers — add income/expense, reports, balance, record lists."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import bot.handlers.helpers as _h
from bot.keyboards import finance_shortcuts_keyboard, main_menu_keyboard
from bot.states import FinanceInputStates


def register_finance_handlers(router: Router) -> None:
    async def prompt_finance_input(message: Message, state: FSMContext, record_kind: str, *, edit: bool = False) -> None:
        if record_kind == "income":
            await state.set_state(FinanceInputStates.income)
            text = "💰 Напиши доход одной фразой.\nПример: _получил 50к от клиента_"
        else:
            await state.set_state(FinanceInputStates.expense)
            text = "💸 Напиши расход одной фразой.\nПример: _заплатил 12к за рекламу_"
        await _h.respond(message, text, reply_markup=finance_shortcuts_keyboard(), edit=edit)

    router._prompt_finance_input = prompt_finance_input  # noqa: SLF001

    @router.message(Command("finance"))
    @router.message(F.text == "📊 Финансы")
    async def finance_handler(message: Message) -> None:
        await _h.show_finance(message)

    @router.message(Command("balance"))
    async def balance_handler(message: Message) -> None:
        await _h.show_balance(message)

    @router.message(Command("income"))
    async def income_list_handler(message: Message) -> None:
        await _h.show_record_list(message, "income")

    @router.message(Command("expenses"))
    async def expense_list_handler(message: Message) -> None:
        await _h.show_record_list(message, "expense")

    @router.message(Command("report"))
    async def report_handler(message: Message) -> None:
        await _h.show_finance(message)

    @router.message(Command("add_income"))
    @router.message(F.text == "💰 Добавить доход")
    async def add_income_handler(message: Message, state: FSMContext) -> None:
        payload = message.text.partition(" ")[2].strip()
        if not payload:
            await prompt_finance_input(message, state, "income")
            return
        client = _h._get_client()
        source_text = _h._normalize_finance_text(payload, "income")
        result = await client.add_from_text(message.from_user.id, source_text)
        if not result.get("ok"):
            await message.answer("Не понял формат. Пример: _получил 50к от клиента_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Доход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    @router.message(Command("add_expense"))
    @router.message(F.text == "💸 Добавить расход")
    async def add_expense_handler(message: Message, state: FSMContext) -> None:
        payload = message.text.partition(" ")[2].strip()
        if not payload:
            await prompt_finance_input(message, state, "expense")
            return
        client = _h._get_client()
        source_text = _h._normalize_finance_text(payload, "expense")
        result = await client.add_from_text(message.from_user.id, source_text)
        if not result.get("ok"):
            await message.answer("Не понял формат. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Расход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    @router.message(FinanceInputStates.income)
    async def income_state_handler(message: Message, state: FSMContext) -> None:
        source_text = _h._normalize_finance_text((message.text or "").strip(), "income")
        if not source_text:
            await message.answer("Напиши сумму. Пример: _получил 50к от клиента_", parse_mode="Markdown")
            return
        client = _h._get_client()
        result = await client.add_from_text(message.from_user.id, source_text)
        if not result.get("ok"):
            await message.answer("Не понял сумму. Пример: _получил 50к от клиента_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Доход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    @router.message(FinanceInputStates.expense)
    async def expense_state_handler(message: Message, state: FSMContext) -> None:
        source_text = _h._normalize_finance_text((message.text or "").strip(), "expense")
        if not source_text:
            await message.answer("Напиши сумму. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
            return
        client = _h._get_client()
        result = await client.add_from_text(message.from_user.id, source_text)
        if not result.get("ok"):
            await message.answer("Не понял сумму. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Расход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")
