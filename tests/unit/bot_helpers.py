"""Shared helpers for bot handler tests."""

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User as TelegramUser

from shared.db.enums import (
    EntityType,
    TaxRegime,
)

# Modules that import SessionFactory / build_services / get_settings directly
_HANDLER_MODULES = [
    "bot.handlers._helpers",
    "bot.handlers.start",
    "bot.handlers.onboarding",
    "bot.handlers.finance",
    "bot.handlers.events",
    "bot.handlers.ai_consult",
    "bot.handlers.subscription",
    "bot.handlers.regime",
    "bot.handlers.navigation",
]


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


def collect_handlers(router: Router, observer_name: str) -> dict:
    """Collect handlers from *router* and all its sub-routers recursively."""
    result = {}
    observer = getattr(router, observer_name, None)
    if observer:
        for h in observer.handlers:
            result[h.callback.__name__] = h
    for sub in router.sub_routers:
        result.update(collect_handlers(sub, observer_name))
    return result


def patch_handler_deps(services=None):
    """Return (ctx, svc, session) where *ctx* is a context-manager that patches
    SessionFactory / build_services / get_settings across all handler modules."""
    svc = services or make_services()

    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    result_mock.scalar.return_value = 0
    result_mock.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result_mock)

    settings_mock = MagicMock(
        stars_price_basic=150,
        stars_price_pro=400,
        stars_price_annual=3500,
    )

    class _Ctx:
        def __enter__(self):
            self._stack = ExitStack()
            self._stack.__enter__()
            for mod in _HANDLER_MODULES:
                try:
                    self._stack.enter_context(patch(f"{mod}.SessionFactory", return_value=session))
                except AttributeError:
                    pass
                try:
                    self._stack.enter_context(patch(f"{mod}.build_services", return_value=svc))
                except AttributeError:
                    pass
                try:
                    self._stack.enter_context(patch(f"{mod}.get_settings", return_value=settings_mock))
                except AttributeError:
                    pass
            return self

        def __exit__(self, *exc):
            return self._stack.__exit__(*exc)

    return _Ctx(), svc, session


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
