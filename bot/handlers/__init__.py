"""Bot handlers package — modular split.

Each domain lives in its own module. This file re-exports ``build_router``
for backwards compatibility so the rest of the codebase can keep doing::

    from bot.handlers import build_router
"""

from __future__ import annotations

from aiogram import Router

from bot.backend_client import BackendClient
from bot.handlers import (
    ai_consult,
    events,
    finance,
    help,
    navigation,
    onboarding,
    profile,
    regime,
    start,
    subscription,
)
from bot.handlers._helpers import (  # noqa: F401 — backward compat re-exports
    AI_TOPIC_PROMPTS,
    COUNTERPARTIES_MAP,
    ENTITY_TYPE_MAP,
    MAIN_MENU_BUTTONS,
    PLANNED_ENTITY_TEXT,
    REGIME_ACTIVITY_MAP,
    TAX_REGIME_MAP,
    category_label as _category_label,
    contains_hint as _contains_hint,
    entity_label as _entity_label,
    format_records as _format_records,
    normalize_finance_text as _normalize_finance_text,
    planned_entity_label as _planned_entity_label,
    tax_regime_label as _tax_regime_label,
)
from shared.config import get_settings


def build_router() -> Router:
    router = Router()
    settings = get_settings()
    base_url = getattr(settings, "backend_base_url", "http://backend:8080")
    client = BackendClient(base_url=base_url)

    # Register sub-modules (order matters — first match wins for FSM states)
    start.register(router, client)
    onboarding.register(router, client)
    help.register(router, client)
    profile.register(router, client)
    events.register(router, client)
    finance.register(router, client)
    ai_consult.register(router, client)
    subscription.register(router, client)
    regime.register(router, client)
    # Navigation callbacks & catch-all MUST be last
    navigation.register(router, client)

    return router
