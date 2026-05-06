from accountant_bot.contracts.payloads import ReminderPayload
from accountant_bot.services.event_policies import build_consequence_hint


class NotificationComposer:
    @staticmethod
    def build_reminder_payload(reminder, user_event, calendar_event) -> ReminderPayload:
        category = calendar_event.category.value
        return ReminderPayload(
            reminder_id=str(reminder.id),
            user_id=str(reminder.user_id),
            user_event_id=str(user_event.id),
            reminder_type=reminder.reminder_type,
            scheduled_at=reminder.scheduled_at,
            due_date=user_event.due_date,
            title=calendar_event.title,
            description=calendar_event.description,
            category=category,
            legal_basis=calendar_event.legal_basis,
            consequence_hint=reminder.delivery_payload.get(
                "consequence_hint",
                build_consequence_hint(calendar_event.category),
            ),
            action_required=reminder.delivery_payload.get("action_required", "Проверьте обязательство."),
            buttons=["mark_done", "details", "documents", "snooze"],
        )
