"""Bot handlers package — assembles the Router from sub-modules.

Re-exports constants and helpers for backward compatibility with tests.
"""

from aiogram import Router

from bot.handlers.helpers import (  # noqa: F401 — re-exports for tests
    AI_TOPIC_PROMPTS,
    COUNTERPARTIES_MAP,
    ENTITY_TYPE_LABELS,
    ENTITY_TYPE_MAP,
    MAIN_MENU_BUTTONS,
    PLANNED_ENTITY_TEXT,
    REGIME_ACTIVITY_MAP,
    TAX_REGIME_LABELS,
    TAX_REGIME_MAP,
    _category_label,
    _contains_hint,
    _entity_label,
    _format_money,
    _format_records,
    _normalize_finance_text,
    _planned_entity_label,
    _tax_regime_label,
    load_profile,
    respond,
    show_home,
    sync_profile_events_and_reminders,
)

# Re-export dependencies that existing tests patch via "bot.handlers.<name>"
from shared.config import get_settings as get_settings  # noqa: F401
from shared.db.enums import (  # noqa: F401
    EntityType as EntityType,
    FinanceRecordType as FinanceRecordType,
    PaymentStatus as PaymentStatus,
    SubscriptionPlan as SubscriptionPlan,
    TaxRegime as TaxRegime,
)
from shared.db.session import SessionFactory as SessionFactory  # noqa: F401
from backend.services.container import build_services as build_services  # noqa: F401
from backend.services.finance_parser import (  # noqa: F401
    EXPENSE_CATEGORY_LABELS as EXPENSE_CATEGORY_LABELS,
    INCOME_CATEGORY_LABELS as INCOME_CATEGORY_LABELS,
)
from backend.services.onboarding import OnboardingDraft as OnboardingDraft  # noqa: F401
from backend.services.profile_matching import ProfileContext as ProfileContext  # noqa: F401
from backend.services.subscription import PLAN_DETAILS as PLAN_DETAILS  # noqa: F401
from backend.services.tax_engine import TaxQueryParser as TaxQueryParser  # noqa: F401
from backend.services.rate_limit import allow_ai_request as allow_ai_request  # noqa: F401

from bot.handlers.start import register_start_handlers
from bot.handlers.onboarding import register_onboarding_handlers
from bot.handlers.finance import register_finance_handlers
from bot.handlers.events import register_events_handlers
from bot.handlers.ai_consult import register_ai_consult_handlers, do_ai_answer, show_ai_consult  # noqa: F401
from bot.handlers.subscription import register_subscription_handlers
from bot.handlers.profile import register_profile_handlers
from bot.handlers.help import register_help_handlers
from bot.handlers.regime import register_regime_handlers, handle_tax_calculation  # noqa: F401
from bot.handlers.navigation import register_navigation_handlers


def build_router() -> Router:
    router = Router()

    # Order matters: FSM state handlers must be registered before catch-all.
    register_start_handlers(router)
    register_help_handlers(router)
    register_profile_handlers(router)
    register_events_handlers(router)
    register_subscription_handlers(router)
    register_ai_consult_handlers(router)
    register_finance_handlers(router)
    register_regime_handlers(router)
    register_onboarding_handlers(router)
    # Navigation callbacks and catch-all MUST be last.
    register_navigation_handlers(router)

    return router
