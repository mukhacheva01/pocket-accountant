"""Bot handlers — split into domain modules.

Each module exposes ``make_router()`` factory.  ``build_router()`` composes
them into a single parent router that the dispatcher includes.
"""

from __future__ import annotations

from aiogram import Router

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
from bot.handlers._helpers import (  # noqa: F401
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
    check_ai_limit,
    do_ai_answer,
    handle_tax_calculation,
    load_profile,
    prompt_finance_input,
    respond,
    show_ai_consult,
    show_balance,
    show_calendar,
    show_documents,
    show_events,
    show_finance,
    show_help,
    show_home,
    show_laws,
    show_overdue,
    show_profile,
    show_record_list,
    show_referral,
    show_reminders,
    show_settings,
    show_subscription,
    start_regime_picker,
    sync_profile_events_and_reminders,
)


def build_router() -> Router:
    """Compose all handler sub-routers into a single parent router."""
    parent = Router()
    parent.include_router(start.make_router())
    parent.include_router(onboarding.make_router())
    parent.include_router(help.make_router())
    parent.include_router(profile.make_router())
    parent.include_router(events.make_router())
    parent.include_router(finance.make_router())
    parent.include_router(ai_consult.make_router())
    parent.include_router(subscription.make_router())
    parent.include_router(regime.make_router())
    parent.include_router(navigation.make_router())
    return parent
