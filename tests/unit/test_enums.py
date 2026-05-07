"""Tests for shared.db.enums."""

from shared.db.enums import (
    EntityType,
    EventCategory,
    EventStatus,
    FinanceRecordType,
    LawUpdateReviewStatus,
    PaymentStatus,
    ReminderStatus,
    ReminderType,
    SubscriptionPlan,
    TaxRegime,
)


def test_entity_types():
    assert EntityType.INDIVIDUAL_ENTREPRENEUR.value == "ip"
    assert EntityType.LIMITED_COMPANY.value == "ooo"
    assert EntityType.SELF_EMPLOYED.value == "self_employed"


def test_tax_regimes():
    assert TaxRegime.USN_INCOME.value == "usn_income"
    assert TaxRegime.USN_INCOME_EXPENSE.value == "usn_income_expense"
    assert TaxRegime.OSNO.value == "osno"
    assert TaxRegime.NPD.value == "npd"


def test_event_categories():
    assert EventCategory.TAX.value == "tax"
    assert EventCategory.DECLARATION.value == "declaration"


def test_event_statuses():
    assert EventStatus.PENDING.value == "pending"
    assert EventStatus.COMPLETED.value == "completed"


def test_finance_record_types():
    assert FinanceRecordType.INCOME.value == "income"
    assert FinanceRecordType.EXPENSE.value == "expense"


def test_subscription_plans():
    assert SubscriptionPlan.FREE.value == "free"
    assert SubscriptionPlan.BASIC.value == "basic"
    assert SubscriptionPlan.PRO.value == "pro"
    assert SubscriptionPlan.ANNUAL.value == "annual"


def test_reminder_types():
    assert ReminderType.DAYS_7.value == "days_7"
    assert ReminderType.SAME_DAY.value == "same_day"
    assert ReminderType.OVERDUE.value == "overdue"


def test_reminder_statuses():
    assert ReminderStatus.PENDING.value == "pending"
    assert ReminderStatus.SENT.value == "sent"
    assert ReminderStatus.FAILED.value == "failed"


def test_payment_statuses():
    assert PaymentStatus.PENDING.value == "pending"
    assert PaymentStatus.COMPLETED.value == "completed"


def test_law_update_review_statuses():
    assert LawUpdateReviewStatus.UNREVIEWED.value == "unreviewed"
    assert LawUpdateReviewStatus.APPROVED.value == "approved"
    assert LawUpdateReviewStatus.REJECTED.value == "rejected"
