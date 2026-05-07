"""Shared helpers for bot handler tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User as TelegramUser

from shared.db.enums import (
    EntityType,
    TaxRegime,
)

MODULE = "bot.handlers"


def make_user(
    user_id=123,
    first_name="Тест",
    username="tester",
):
    u = MagicMock(spec=TelegramUser)
    u.id = user_id
    u.first_name = first_name
    u.username = username
    return u


def make_message(
    text="/start",
    user_id=123,
    first_name="Тест",
    username="tester",
):
    msg = AsyncMock(spec=Message)
    msg.text = text
    msg.from_user = make_user(user_id, first_name, username)
    msg.answer = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.bot = AsyncMock()
    msg.chat = MagicMock(id=user_id)
    msg.content_type = "text"
    return msg


def make_state(data=None, current_state=None):
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value=data or {})
    state.get_state = AsyncMock(return_value=current_state)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.clear = AsyncMock()
    return state


def make_callback_query(data="nav:home", user_id=123, first_name="Тест", username="tester"):
    q = AsyncMock(spec=CallbackQuery)
    q.data = data
    q.from_user = make_user(user_id, first_name, username)
    q.message = make_message(user_id=user_id)
    q.answer = AsyncMock()
    return q


def make_db_user(user_id="u1", telegram_id=123):
    user = MagicMock()
    user.id = user_id
    user.telegram_id = telegram_id
    user.referred_by = None
    user.referral_bonus_requests = 0
    user.ai_requests_today = 0
    user.ai_requests_reset_date = None
    return user


def make_profile(
    entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
    tax_regime=TaxRegime.USN_INCOME,
    has_employees=False,
    marketplaces_enabled=False,
    region="Москва",
    industry=None,
):
    profile = MagicMock()
    profile.entity_type = entity_type
    profile.tax_regime = tax_regime
    profile.has_employees = has_employees
    profile.marketplaces_enabled = marketplaces_enabled
    profile.region = region
    profile.industry = industry
    profile.reminder_settings = {
        "notify_taxes": True,
        "notify_reporting": True,
        "notify_documents": True,
        "notify_laws": True,
        "offset_days": [3, 1],
    }
    return profile


def make_services():
    svc = MagicMock()
    svc.onboarding.ensure_user = AsyncMock(return_value=make_db_user())
    svc.onboarding.load_profile = AsyncMock(return_value=make_profile())
    svc.onboarding.save_profile = AsyncMock()
    svc.calendar.upcoming = AsyncMock(return_value=[])
    svc.calendar.overdue = AsyncMock(return_value=[])
    svc.calendar.sync_user_events = AsyncMock()
    svc.calendar.calendar_repo = MagicMock()
    svc.calendar.calendar_repo.snooze = AsyncMock()
    svc.calendar.calendar_repo.mark_completed = AsyncMock()
    svc.finance.balance = AsyncMock(return_value={"income": 100000, "expense": 50000, "balance": 50000})
    svc.finance.report = AsyncMock(return_value={
        "totals": {"income": 100000, "expense": 50000},
        "profit": 50000,
        "top_expenses": [("marketing", 20000)],
    })
    svc.finance.list_records = AsyncMock(return_value=[])
    svc.finance.add_from_text = AsyncMock()
    svc.subscription.get_subscription = AsyncMock(return_value=None)
    svc.subscription.is_active = MagicMock(return_value=False)
    svc.subscription.can_use_ai = AsyncMock(return_value=(True, 3))
    svc.subscription.increment_ai_usage = AsyncMock()
    svc.subscription.activate = AsyncMock()
    svc.subscription.record_payment = AsyncMock()
    svc.subscription.cancel = AsyncMock()
    svc.subscription.payment_exists = AsyncMock(return_value=False)
    svc.documents.upcoming_documents = AsyncMock(return_value=[])
    svc.laws.relevant_updates = AsyncMock(return_value=[])
    svc.reminders.create_reminders_for_event = AsyncMock(return_value=[])
    svc.ai.answer_tax_question = AsyncMock(return_value=SimpleNamespace(text="AI answer", sources=[], confidence=0.9))
    svc.templates.match_template = MagicMock(return_value=None)
    svc.tax = MagicMock()
    return svc


def make_mock_client():
    """Create a mock BackendClient with all methods returning sensible defaults."""
    client = AsyncMock()
    client.ensure_user = AsyncMock(return_value={"user_id": "u1", "telegram_id": 123})
    client.get_profile = AsyncMock(return_value={"profile": {
        "entity_type": "ip",
        "tax_regime": "usn_income",
        "has_employees": False,
        "marketplaces_enabled": False,
        "region": "Москва",
        "industry": None,
        "reminder_settings": {
            "notify_taxes": True,
            "notify_reporting": True,
            "notify_documents": True,
            "notify_laws": True,
            "offset_days": [3, 1],
        },
    }})
    client.complete_onboarding = AsyncMock(return_value={})
    client.complete_onboarding_full = AsyncMock(return_value={})
    client.touch = AsyncMock(return_value={})
    client.set_referral = AsyncMock(return_value={})
    client.get_referral_info = AsyncMock(return_value={"referral_count": 0, "bonus_requests": 0})
    client.upcoming_events = AsyncMock(return_value={"events": []})
    client.overdue_events = AsyncMock(return_value={"events": []})
    client.event_action = AsyncMock(return_value={})
    client.add_finance_record = AsyncMock(return_value={"record": {
        "record_type": "income", "amount": "50000", "category": "services",
    }})
    client.add_finance_text = AsyncMock(return_value={"record": {
        "record_type": "income", "amount": "50000", "category": "services",
    }})
    client.get_finance_report = AsyncMock(return_value={
        "totals": {"income": 100000, "expense": 50000},
        "profit": 50000,
        "top_expenses": [("marketing", 20000)],
    })
    client.get_full_report = AsyncMock(return_value={
        "totals": {"income": 100000, "expense": 50000},
        "profit": 50000,
        "top_expenses": [("marketing", 20000)],
    })
    client.get_balance = AsyncMock(return_value={"income": 100000, "expense": 50000, "balance": 50000})
    client.get_finance_records = AsyncMock(return_value={"records": []})
    client.ask_ai = AsyncMock(return_value={"answer": "AI answer", "sources": []})
    client.ask_ai_with_history = AsyncMock(return_value={"answer": "AI answer", "sources": [], "remaining_ai_requests": 2})
    client.clear_ai_history = AsyncMock(return_value={})
    client.subscription_status = AsyncMock(return_value={
        "is_active": False, "remaining_ai_requests": 3, "can_use_ai": True,
    })
    client.activate_subscription = AsyncMock(return_value={"expires_at": "2026-08-01"})
    client.cancel_subscription = AsyncMock(return_value={})
    client.record_payment = AsyncMock(return_value={})
    client.calculate_tax = AsyncMock(return_value={"rendered": "Расчёт: ..."})
    client.parse_tax_query = AsyncMock(return_value={"rendered": "Расчёт: ..."})
    client.compare_regimes = AsyncMock(return_value={"rendered": "Рекомендация: УСН 6%"})
    client.upcoming_documents = AsyncMock(return_value={"documents": []})
    client.law_updates = AsyncMock(return_value={"updates": []})
    client.match_template = AsyncMock(return_value={"template": None})
    return client


def patch_handler_deps(mock_client=None):
    """Patch BackendClient and get_settings for handler tests.

    Returns (client_patch, gs_patch, mock_client).
    Usage:
        cl_p, gs_p, mock_client = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
    """
    mc = mock_client or make_mock_client()
    cl_patch = patch(f"{MODULE}.BackendClient", return_value=mc)
    gs_patch = patch(f"{MODULE}.get_settings", return_value=MagicMock(
        stars_price_basic=150,
        stars_price_pro=400,
        stars_price_annual=3500,
        backend_base_url="http://test:8080",
    ))
    return cl_patch, gs_patch, mc
