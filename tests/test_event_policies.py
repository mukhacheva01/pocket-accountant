import unittest

from accountant_bot.db.enums import EventCategory
from accountant_bot.services.event_policies import (
    build_action_hint,
    build_consequence_hint,
    event_matches_reminder_preferences,
    is_document_related,
)

class EventPoliciesTests(unittest.TestCase):
    def test_reporting_events_respect_reporting_or_document_toggle(self) -> None:
        self.assertTrue(
            event_matches_reminder_preferences(
                EventCategory.DECLARATION,
                {"notify_reporting": True, "notify_documents": False},
            )
        )
        self.assertTrue(
            event_matches_reminder_preferences(
                EventCategory.DECLARATION,
                {"notify_reporting": False, "notify_documents": True},
            )
        )
        self.assertFalse(
            event_matches_reminder_preferences(
                EventCategory.DECLARATION,
                {"notify_reporting": False, "notify_documents": False},
            )
        )

    def test_tax_events_respect_tax_toggle(self) -> None:
        self.assertFalse(event_matches_reminder_preferences(EventCategory.TAX, {"notify_taxes": False}))
        self.assertTrue(event_matches_reminder_preferences(EventCategory.TAX, {"notify_taxes": True}))

    def test_document_helpers_filter_and_explain_reporting_events(self) -> None:
        self.assertTrue(is_document_related(EventCategory.DECLARATION))
        self.assertFalse(is_document_related(EventCategory.TAX))
        self.assertIn("Подготовь", build_action_hint(EventCategory.DECLARATION))
        self.assertIn("штраф", build_consequence_hint(EventCategory.DECLARATION).lower())


if __name__ == "__main__":
    unittest.main()
