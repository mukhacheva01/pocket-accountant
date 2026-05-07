"""Finance handlers: income, expense, balance, reports."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import User as TelegramUser

from bot.backend_client import BackendClient
from bot.handlers._helpers import (
    EXPENSE_CATEGORY_LABELS,
    format_money,
    format_records,
    normalize_finance_text,
    respond,
)
from bot.keyboards import finance_shortcuts_keyboard
from bot.states import FinanceInputStates


async def show_finance(
    message: Message, client: BackendClient,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    actor = actor or message.from_user
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    user_id = user_data["user_id"]
    report = await client.get_full_report(user_id)
    profile_data = await client.get_profile(user_id)
    profile = profile_data.get("profile")

    tax_base = report.get("totals", {}).get("income", 0)
    if profile and profile.get("tax_regime") == "usn_income_expense":
        tax_base = report.get("profit", 0)

    lines = [
        "📊 *Финансы за 30 дней*\n",
        f"📈 Доходы: *{format_money(report.get('totals', {}).get('income', 0))}* ₽",
        f"📉 Расходы: *{format_money(report.get('totals', {}).get('expense', 0))}* ₽",
        f"💰 Прибыль: *{format_money(report.get('profit', 0))}* ₽",
        f"📋 Налоговая база: {format_money(tax_base)} ₽",
    ]
    top_expenses = report.get("top_expenses", [])
    if top_expenses:
        top = ", ".join(
            f"{EXPENSE_CATEGORY_LABELS.get(cat, cat)}: {amt}"
            for cat, amt in top_expenses[:3]
        )
        lines.append(f"\nТоп расходов: {top}")
    await respond(message, "\n".join(lines), reply_markup=finance_shortcuts_keyboard(), edit=edit)


async def show_balance(
    message: Message, client: BackendClient,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    actor = actor or message.from_user
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    balance = await client.get_balance(user_data["user_id"])
    text = (
        "💰 *Баланс за текущий месяц*\n\n"
        f"📈 Доходы: *{format_money(balance.get('income', 0))}* ₽\n"
        f"📉 Расходы: *{format_money(balance.get('expense', 0))}* ₽\n"
        f"💰 Баланс: *{format_money(balance.get('balance', 0))}* ₽"
    )
    await respond(message, text, reply_markup=finance_shortcuts_keyboard(), edit=edit)


async def show_record_list(
    message: Message, client: BackendClient, record_type: str,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    actor = actor or message.from_user
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    data = await client.get_finance_records(user_data["user_id"], record_type=record_type, limit=20)
    records = data.get("records", [])
    emoji = "📈" if record_type == "income" else "📉"
    title = "Доходы" if record_type == "income" else "Расходы"
    await respond(message, f"{emoji} *{title}:*\n\n{format_records(records)}", reply_markup=finance_shortcuts_keyboard(), edit=edit)


async def prompt_finance_input(
    message: Message, state: FSMContext, record_kind: str, *, edit: bool = False,
) -> None:
    if record_kind == "income":
        await state.set_state(FinanceInputStates.income)
        text = "💰 Напиши доход одной фразой.\nПример: _получил 50к от клиента_"
    else:
        await state.set_state(FinanceInputStates.expense)
        text = "💸 Напиши расход одной фразой.\nПример: _заплатил 12к за рекламу_"
    await respond(message, text, reply_markup=finance_shortcuts_keyboard(), edit=edit)


def register(parent_router: Router, client: BackendClient) -> None:
    @parent_router.message(Command("finance"))
    @parent_router.message(F.text == "📊 Финансы")
    async def finance_handler(message: Message) -> None:
        await show_finance(message, client)

    @parent_router.message(Command("balance"))
    async def balance_handler(message: Message) -> None:
        await show_balance(message, client)

    @parent_router.message(Command("income_list"))
    async def income_list_handler(message: Message) -> None:
        await show_record_list(message, client, "income")

    @parent_router.message(Command("expense_list"))
    async def expense_list_handler(message: Message) -> None:
        await show_record_list(message, client, "expense")

    @parent_router.message(Command("report"))
    async def report_handler(message: Message) -> None:
        await show_finance(message, client)

    @parent_router.message(Command("add_income"))
    @parent_router.message(F.text == "💰 Добавить доход")
    async def add_income_handler(message: Message, state: FSMContext) -> None:
        payload = message.text.partition(" ")[2].strip()
        if not payload:
            await prompt_finance_input(message, state, "income")
            return
        user_data = await client.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        try:
            await client.add_finance_text(user_data["user_id"], normalize_finance_text(payload, "income"))
        except Exception:
            await message.answer("Не понял формат. Пример: _получил 50к от клиента_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Доход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    @parent_router.message(Command("add_expense"))
    @parent_router.message(F.text == "💸 Добавить расход")
    async def add_expense_handler(message: Message, state: FSMContext) -> None:
        payload = message.text.partition(" ")[2].strip()
        if not payload:
            await prompt_finance_input(message, state, "expense")
            return
        user_data = await client.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        try:
            await client.add_finance_text(user_data["user_id"], normalize_finance_text(payload, "expense"))
        except Exception:
            await message.answer("Не понял формат. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Расход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    # ── Finance input states ──

    @parent_router.message(FinanceInputStates.income)
    async def income_state_handler(message: Message, state: FSMContext) -> None:
        source_text = normalize_finance_text((message.text or "").strip(), "income")
        if not source_text:
            await message.answer("Напиши сумму. Пример: _получил 50к от клиента_", parse_mode="Markdown")
            return
        user_data = await client.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        try:
            await client.add_finance_text(user_data["user_id"], source_text)
        except Exception:
            await message.answer("Не понял сумму. Пример: _получил 50к от клиента_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Доход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")

    @parent_router.message(FinanceInputStates.expense)
    async def expense_state_handler(message: Message, state: FSMContext) -> None:
        source_text = normalize_finance_text((message.text or "").strip(), "expense")
        if not source_text:
            await message.answer("Напиши сумму. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
            return
        user_data = await client.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        try:
            await client.add_finance_text(user_data["user_id"], source_text)
        except Exception:
            await message.answer("Не понял сумму. Пример: _заплатил 12к за рекламу_", parse_mode="Markdown")
            return
        await state.clear()
        await message.answer("✅ Расход сохранён.", reply_markup=finance_shortcuts_keyboard(), parse_mode="Markdown")
