from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    entity_type = State()
    tax_regime = State()
    has_employees = State()
    region = State()


class FinanceInputStates(StatesGroup):
    income = State()
    expense = State()


class RegimeSelectionStates(StatesGroup):
    activity = State()
    monthly_income = State()
    has_employees = State()
    counterparties = State()
    region = State()


class AIConsultStates(StatesGroup):
    chatting = State()
