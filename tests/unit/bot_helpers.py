"""Shared helpers for bot handler tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User as TelegramUser


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


def make_mock_backend_client():
    client = AsyncMock()
    client.track_activity = AsyncMock(return_value={
        "ok": True, "user_id": "u1", "has_profile": True,
        "profile": {
            "entity_type": "ip", "tax_regime": "usn_income",
            "has_employees": False, "marketplaces_enabled": False,
            "region": "Москва", "industry": None,
            "reminder_settings": {"notify_taxes": True, "notify_reporting": True,
                                   "notify_documents": True, "notify_laws": True, "offset_days": [3, 1]},
        },
        "subscription": {"is_active": False, "remaining_ai": 3},
    })
    client.get_home = AsyncMock(return_value={
        "has_profile": True,
        "profile": {"entity_type": "ip", "tax_regime": "usn_income", "has_employees": False,
                     "marketplaces_enabled": False, "region": "Москва"},
        "balance": {"income": 100000, "expense": 50000, "balance": 50000},
        "next_event": None, "subscription_active": False, "remaining_ai": 3,
    })
    client.get_profile = AsyncMock(return_value={
        "has_profile": True,
        "profile": {"entity_type": "ip", "tax_regime": "usn_income", "has_employees": False,
                     "marketplaces_enabled": False, "region": "Москва"},
    })
    client.get_events = AsyncMock(return_value={"events": []})
    client.get_calendar = AsyncMock(return_value={"events": []})
    client.get_overdue = AsyncMock(return_value={"events": []})
    client.get_documents = AsyncMock(return_value={"documents": []})
    client.get_laws = AsyncMock(return_value={"has_profile": True, "updates": []})
    client.get_reminders = AsyncMock(return_value={"has_profile": True, "reminder_settings": {}})
    client.get_finance_report = AsyncMock(return_value={
        "income": 100000, "expense": 50000, "profit": 50000, "tax_base": 100000, "top_expenses": [],
    })
    client.get_balance = AsyncMock(return_value={"income": 100000, "expense": 50000, "balance": 50000})
    client.get_finance_records = AsyncMock(return_value={"records": []})
    client.add_from_text = AsyncMock(return_value={"ok": True, "record_type": "income", "amount": "5000", "category": "other"})
    client.ai_full_question = AsyncMock(return_value={"ok": True, "answer": "AI answer", "remaining_ai": 3, "subscription_active": False})
    client.ai_clear_history = AsyncMock(return_value={"ok": True})
    client.get_subscription_status = AsyncMock(return_value={
        "is_active": False, "can_ai": True, "remaining_ai": 3, "prices": {"basic": 150, "pro": 400, "annual": 3500},
    })
    client.cancel_subscription = AsyncMock(return_value={"ok": True})
    client.activate_subscription = AsyncMock(return_value={"ok": True})
    client.record_payment = AsyncMock(return_value={"ok": True, "expires_at": "2025-02-01"})
    client.get_referral = AsyncMock(return_value={"referral_count": 0, "bonus_requests": 0})
    client.save_referral = AsyncMock(return_value={"ok": True})
    client.onboarding_with_sync = AsyncMock(return_value={"ok": True})
    client.compare_regimes = AsyncMock(return_value={"rendered": "Результат сравнения"})
    client.parse_and_calculate_tax = AsyncMock(return_value={"ok": False})
    client.match_template = AsyncMock(return_value={"matched": False})
    client.event_snooze = AsyncMock(return_value={"ok": True})
    client.event_complete = AsyncMock(return_value={"ok": True})
    return client


def patch_backend_client(mock_client=None):
    mc = mock_client or make_mock_backend_client()
    return patch("bot.runtime.get_backend_client", return_value=mc), mc


# Legacy helpers kept for backward compatibility with non-bot tests
def make_db_user(user_id="u1", telegram_id=123):
    user = MagicMock()
    user.id = user_id
    user.telegram_id = telegram_id
    user.referred_by = None
    user.referral_bonus_requests = 0
    user.ai_requests_today = 0
    user.ai_requests_reset_date = None
    return user


def make_services():
    svc = MagicMock()
    svc.onboarding.ensure_user = AsyncMock(return_value=make_db_user())
    svc.onboarding.load_profile = AsyncMock(return_value=MagicMock())
    svc.onboarding.save_profile = AsyncMock()
    svc.calendar.upcoming = AsyncMock(return_value=[])
    svc.calendar.overdue = AsyncMock(return_value=[])
    svc.calendar.sync_user_events = AsyncMock()
    svc.calendar.calendar_repo = MagicMock()
    svc.calendar.calendar_repo.snooze = AsyncMock()
    svc.calendar.calendar_repo.mark_completed = AsyncMock()
    svc.finance.balance = AsyncMock(return_value={"income": 100000, "expense": 50000, "balance": 50000})
    svc.finance.report = AsyncMock(return_value={
        "totals": {"income": 100000, "expense": 50000}, "profit": 50000, "top_expenses": [],
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
