"""Tests for backend.services.event_policies."""

from shared.db.enums import EventCategory
from backend.services.event_policies import (
    build_action_hint,
    build_consequence_hint,
    event_matches_reminder_preferences,
    is_document_related,
)


# --- event_matches_reminder_preferences ---


class TestEventMatchesReminderPreferences:
    def test_tax_respects_toggle(self):
        assert event_matches_reminder_preferences(EventCategory.TAX, {"notify_taxes": True})
        assert not event_matches_reminder_preferences(EventCategory.TAX, {"notify_taxes": False})

    def test_contribution_respects_tax_toggle(self):
        assert event_matches_reminder_preferences(EventCategory.CONTRIBUTION, {"notify_taxes": True})
        assert not event_matches_reminder_preferences(EventCategory.CONTRIBUTION, {"notify_taxes": False})

    def test_declaration_respects_reporting_or_documents(self):
        assert event_matches_reminder_preferences(
            EventCategory.DECLARATION, {"notify_reporting": True, "notify_documents": False}
        )
        assert event_matches_reminder_preferences(
            EventCategory.DECLARATION, {"notify_reporting": False, "notify_documents": True}
        )
        assert not event_matches_reminder_preferences(
            EventCategory.DECLARATION, {"notify_reporting": False, "notify_documents": False}
        )

    def test_report_respects_reporting_toggle(self):
        assert event_matches_reminder_preferences(EventCategory.REPORT, {"notify_reporting": True})

    def test_hr_respects_reporting_toggle(self):
        assert event_matches_reminder_preferences(EventCategory.HR, {"notify_reporting": True})

    def test_notice_respects_documents_toggle(self):
        assert event_matches_reminder_preferences(EventCategory.NOTICE, {"notify_documents": True})
        assert not event_matches_reminder_preferences(EventCategory.NOTICE, {"notify_documents": False})

    def test_other_category_default(self):
        assert event_matches_reminder_preferences(EventCategory.OTHER, {})

    def test_other_category_all_disabled(self):
        prefs = {"notify_taxes": False, "notify_reporting": False, "notify_documents": False}
        assert not event_matches_reminder_preferences(EventCategory.OTHER, prefs)

    def test_marketplace_fallback(self):
        assert event_matches_reminder_preferences(EventCategory.MARKETPLACE, {"notify_taxes": True})


# --- is_document_related ---


class TestIsDocumentRelated:
    def test_declaration_is_document(self):
        assert is_document_related(EventCategory.DECLARATION) is True

    def test_notice_is_document(self):
        assert is_document_related(EventCategory.NOTICE) is True

    def test_report_is_document(self):
        assert is_document_related(EventCategory.REPORT) is True

    def test_tax_not_document(self):
        assert is_document_related(EventCategory.TAX) is False

    def test_other_not_document(self):
        assert is_document_related(EventCategory.OTHER) is False


# --- build_action_hint ---


class TestBuildActionHint:
    def test_tax(self):
        hint = build_action_hint(EventCategory.TAX)
        assert "платеж" in hint.lower() or "проверь" in hint.lower()

    def test_notice(self):
        hint = build_action_hint(EventCategory.NOTICE)
        assert "уведомление" in hint.lower()

    def test_declaration(self):
        hint = build_action_hint(EventCategory.DECLARATION)
        assert "отчетность" in hint.lower() or "документы" in hint.lower()

    def test_other(self):
        hint = build_action_hint(EventCategory.OTHER)
        assert "обязательство" in hint.lower()


# --- build_consequence_hint ---


class TestBuildConsequenceHint:
    def test_tax(self):
        hint = build_consequence_hint(EventCategory.TAX)
        assert "пен" in hint.lower()

    def test_notice(self):
        hint = build_consequence_hint(EventCategory.NOTICE)
        assert "уведомлени" in hint.lower()

    def test_declaration(self):
        hint = build_consequence_hint(EventCategory.DECLARATION)
        assert "штраф" in hint.lower()

    def test_other(self):
        hint = build_consequence_hint(EventCategory.OTHER)
        assert "штраф" in hint.lower() or "блокирующ" in hint.lower()
