"""Tests for bot.keyboards — all keyboard factory functions."""

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from bot.keyboards import (
    ai_consult_keyboard,
    ai_consult_reply_keyboard,
    back_home_row,
    counterparties_keyboard,
    documents_shortcuts_keyboard,
    event_actions_keyboard,
    finance_shortcuts_keyboard,
    help_shortcuts_keyboard,
    laws_shortcuts_keyboard,
    main_menu_keyboard,
    navigation_keyboard,
    onboarding_entity_type_keyboard,
    onboarding_tax_keyboard,
    planned_entity_type_keyboard,
    profile_shortcuts_keyboard,
    regime_activity_keyboard,
    regime_income_keyboard,
    reminder_offsets_keyboard,
    reminders_shortcuts_keyboard,
    retry_keyboard,
    section_shortcuts_keyboard,
    settings_shortcuts_keyboard,
    subscription_keyboard,
    subscription_manage_keyboard,
    yes_no_keyboard,
)
from bot.callbacks import NavigationCallback
from bot.handlers.navigation import HANDLED_NAVIGATION_TARGETS


def _navigation_targets(markup: InlineKeyboardMarkup) -> set[str]:
    targets = set()
    for row in markup.inline_keyboard:
        for button in row:
            if button.callback_data and button.callback_data.startswith("nav:"):
                targets.add(NavigationCallback.unpack(button.callback_data).target)
    return targets


class TestReplyKeyboards:
    def test_onboarding_entity_type(self):
        kb = onboarding_entity_type_keyboard()
        assert isinstance(kb, ReplyKeyboardMarkup)
        assert len(kb.keyboard) == 2

    def test_planned_entity_type(self):
        kb = planned_entity_type_keyboard()
        assert isinstance(kb, ReplyKeyboardMarkup)

    def test_onboarding_tax(self):
        kb = onboarding_tax_keyboard()
        assert isinstance(kb, ReplyKeyboardMarkup)
        texts = [btn.text for row in kb.keyboard for btn in row]
        assert "УСН 6%" in texts

    def test_yes_no(self):
        kb = yes_no_keyboard()
        texts = [btn.text for row in kb.keyboard for btn in row]
        assert "Да" in texts
        assert "Нет" in texts

    def test_reminder_offsets(self):
        kb = reminder_offsets_keyboard()
        assert len(kb.keyboard) == 4

    def test_main_menu(self):
        kb = main_menu_keyboard()
        texts = [btn.text for row in kb.keyboard for btn in row]
        assert any("Главная" in t for t in texts)

    def test_regime_activity(self):
        kb = regime_activity_keyboard()
        texts = [btn.text for row in kb.keyboard for btn in row]
        assert "Услуги" in texts

    def test_regime_income(self):
        kb = regime_income_keyboard()
        texts = [btn.text for row in kb.keyboard for btn in row]
        assert "100000" in texts

    def test_counterparties(self):
        kb = counterparties_keyboard()
        texts = [btn.text for row in kb.keyboard for btn in row]
        assert "Физлица" in texts

    def test_ai_consult_reply(self):
        kb = ai_consult_reply_keyboard()
        assert isinstance(kb, ReplyKeyboardMarkup)


class TestInlineKeyboards:
    def test_navigation_keyboard(self):
        kb = navigation_keyboard([[("A", "target_a"), ("B", "target_b")]])
        assert isinstance(kb, InlineKeyboardMarkup)
        assert len(kb.inline_keyboard) == 1
        assert len(kb.inline_keyboard[0]) == 2

    def test_back_home_row(self):
        row = back_home_row()
        assert row == [("🏠 В меню", "home")]

    def test_section_shortcuts(self):
        kb = section_shortcuts_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_finance_shortcuts(self):
        kb = finance_shortcuts_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_documents_shortcuts(self):
        kb = documents_shortcuts_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_profile_shortcuts(self):
        kb = profile_shortcuts_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_laws_shortcuts(self):
        kb = laws_shortcuts_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_reminders_shortcuts(self):
        kb = reminders_shortcuts_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_settings_shortcuts(self):
        kb = settings_shortcuts_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_help_shortcuts(self):
        kb = help_shortcuts_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_event_actions(self):
        kb = event_actions_keyboard("ev123")
        assert isinstance(kb, InlineKeyboardMarkup)
        assert len(kb.inline_keyboard) == 2

    def test_subscription_keyboard(self):
        prices = {"basic": 150, "pro": 400, "annual": 3500}
        kb = subscription_keyboard(prices)
        assert isinstance(kb, InlineKeyboardMarkup)
        assert len(kb.inline_keyboard) == 5

    def test_subscription_manage(self):
        kb = subscription_manage_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_retry_keyboard(self):
        kb = retry_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)
        assert len(kb.inline_keyboard) == 1

    def test_ai_consult_keyboard(self):
        kb = ai_consult_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_all_navigation_buttons_have_handlers(self):
        markups = [
            section_shortcuts_keyboard(),
            finance_shortcuts_keyboard(),
            documents_shortcuts_keyboard(),
            profile_shortcuts_keyboard(),
            laws_shortcuts_keyboard(),
            reminders_shortcuts_keyboard(),
            settings_shortcuts_keyboard(),
            help_shortcuts_keyboard(),
            event_actions_keyboard("ev123"),
            subscription_keyboard({"basic": 150, "pro": 400, "annual": 3500}),
            subscription_manage_keyboard(),
            retry_keyboard(),
            ai_consult_keyboard(),
        ]
        targets = set().union(*(_navigation_targets(markup) for markup in markups))
        assert targets <= HANDLED_NAVIGATION_TARGETS
