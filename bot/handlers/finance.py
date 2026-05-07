"""Finance handlers: income/expense recording and display."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers._helpers import (
    _normalize_finance_text,
    prompt_finance_input,
    show_balance,
    show_finance,
    show_record_list,
)
from bot.keyboards import finance_shortcuts_keyboard
from bot.states import FinanceInputStates
from shared.db.enums import FinanceRecordType
from shared.db.session import SessionFactory
from backend.services.container import build_services


def make_router() -> Router:
    router = Router()

    @router.message(Command("finance"))
    @router.message(F.text == "📊 Финансы")
    async def finance_handler(message: Message) -> None:
        await show_finance(message)

    @router.message(Command("balance"))
    async def balance_handler(message: Message) -> None:
        await show_balance(message)

    @router.message(Command("income"))
    async def income_list_handler(message: Message) -> None:
        await show_record_list(message, FinanceRecordType.INCOME)

    @router.message(Command("expenses"))
    async def expense_list_handler(message: Message) -> None:
        await show_record_list(message, FinanceRecordType.EXPENSE)

    @router.message(Command("report"))
    async def report_handler(message: Message) -> None:
        await show_finance(message)

    @router.message(Command("add_income"))
    @router.message(F.text == "💰 Добавить доход")
    async def add_income_handler(message: Message, state: FSMContext) -> None:
        payload = message.text.partition(" ")[2].strip()
        if not payload:
            await prompt_finance_input(message, state, "income")
            return
        async with SessionFactory() as session:
            services = build_services(session)
            user = await services.onboarding.ensure_user(
                telegram_id=message.from_user.id, username=message.from_user.username,
                first_name=message.from_user.first_name, timezone="Europe/Moscow",
            )
            try:
                await services.finance.add_from_text(str(user.id), _normalize_finance_text(payload, "income"))
            except ValueError:
                await message.answer("Не понял формат. Пример: _получил 50к от клиента_", parse_mode="Markdown")
                return
            await session.commit()
        await state.clear()
        await message.answer("✅ Доход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    @router.message(Command("add_expense"))
    @router.message(F.text == "💸 Добавить расход")
    async def add_expense_handler(message: Message, state: FSMContext) -> None:
        payload = message.text.partition(" ")[2].strip()
        if not payload:
            await prompt_finance_input(message, state, "expense")
            return
        async with SessionFactory() as session:
            services = build_services(session)
            user = await services.onboarding.ensure_user(
                telegram_id=message.from_user.id, username=message.from_user.username,
                first_name=message.from_user.first_name, timezone="Europe/Moscow",
            )
            try:
                await services.finance.add_from_text(str(user.id), _normalize_finance_text(payload, "expense"))
            except ValueError:
                await message.answer("Не понял формат. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
                return
            await session.commit()
        await state.clear()
        await message.answer("✅ Расход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    # ── Finance input FSM states ──

    @router.message(FinanceInputStates.income)
    async def income_state_handler(message: Message, state: FSMContext) -> None:
        source_text = _normalize_finance_text((message.text or "").strip(), "income")
        if not source_text:
            await message.answer("Напиши сумму. Пример: _получил 50к от клиента_", parse_mode="Markdown")
            return
        async with SessionFactory() as session:
            services = build_services(session)
            user = await services.onboarding.ensure_user(
                telegram_id=message.from_user.id, username=message.from_user.username,
                first_name=message.from_user.first_name, timezone="Europe/Moscow",
            )
            try:
                await services.finance.add_from_text(str(user.id), source_text)
            except ValueError:
                await message.answer("Не понял сумму. Пример: _получил 50к от клиента_", parse_mode="Markdown")
                return
            await session.commit()
        await state.clear()
        await message.answer("✅ Доход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    @router.message(FinanceInputStates.expense)
    async def expense_state_handler(message: Message, state: FSMContext) -> None:
        source_text = _normalize_finance_text((message.text or "").strip(), "expense")
        if not source_text:
            await message.answer("Напиши сумму. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
            return
        async with SessionFactory() as session:
            services = build_services(session)
            user = await services.onboarding.ensure_user(
                telegram_id=message.from_user.id, username=message.from_user.username,
                first_name=message.from_user.first_name, timezone="Europe/Moscow",
            )
            try:
                await services.finance.add_from_text(str(user.id), source_text)
            except ValueError:
                await message.answer("Не понял сумму. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
                return
            await session.commit()
        await state.clear()
        await message.answer("✅ Расход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    return router
