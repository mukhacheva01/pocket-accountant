from shared.db.enums import EventCategory


TAX_CATEGORIES = {
    EventCategory.TAX,
    EventCategory.CONTRIBUTION,
}

REPORTING_CATEGORIES = {
    EventCategory.DECLARATION,
    EventCategory.REPORT,
    EventCategory.HR,
    EventCategory.EMPLOYEE,
}

DOCUMENT_CATEGORIES = {
    EventCategory.DECLARATION,
    EventCategory.NOTICE,
    EventCategory.REPORT,
    EventCategory.HR,
    EventCategory.EMPLOYEE,
}


def event_matches_reminder_preferences(category: EventCategory, settings: dict[str, object]) -> bool:
    if category in TAX_CATEGORIES:
        return bool(settings.get("notify_taxes", True))
    if category in REPORTING_CATEGORIES:
        return bool(settings.get("notify_reporting", True) or settings.get("notify_documents", True))
    if category in DOCUMENT_CATEGORIES:
        return bool(settings.get("notify_documents", True))
    return bool(
        settings.get("notify_taxes", True)
        or settings.get("notify_reporting", True)
        or settings.get("notify_documents", True)
    )


def is_document_related(category: EventCategory) -> bool:
    return category in DOCUMENT_CATEGORIES


def build_action_hint(category: EventCategory) -> str:
    if category in TAX_CATEGORIES:
        return "Проверь сумму и подготовь платеж до дедлайна."
    if category == EventCategory.NOTICE:
        return "Подготовь уведомление и отправь его до срока."
    if category in REPORTING_CATEGORIES:
        return "Подготовь и отправь отчетность или кадровые документы до дедлайна."
    return "Проверь обязательство и закрой его до срока."


def build_consequence_hint(category: EventCategory) -> str:
    if category in TAX_CATEGORIES:
        return "Просрочка может привести к пеням и проблемам с учетом платежа."
    if category == EventCategory.NOTICE:
        return "Без уведомления платеж может быть учтен некорректно."
    if category in REPORTING_CATEGORIES:
        return "Просрочка может привести к штрафу и запросам от контролирующих органов."
    return "Просрочка может привести к штрафу или блокирующим последствиям."
