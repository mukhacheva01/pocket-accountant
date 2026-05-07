"""Tests for bot.states."""

from bot.states import AIConsultStates, FinanceInputStates, OnboardingStates, RegimeSelectionStates


def test_onboarding_states():
    assert OnboardingStates.entity_type is not None
    assert OnboardingStates.tax_regime is not None
    assert OnboardingStates.has_employees is not None
    assert OnboardingStates.region is not None


def test_finance_input_states():
    assert FinanceInputStates.income is not None
    assert FinanceInputStates.expense is not None


def test_regime_selection_states():
    assert RegimeSelectionStates.activity is not None
    assert RegimeSelectionStates.monthly_income is not None


def test_ai_consult_states():
    assert AIConsultStates.chatting is not None
