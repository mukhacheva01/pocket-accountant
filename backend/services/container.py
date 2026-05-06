from dataclasses import dataclass

from shared.config import get_settings
from backend.repositories.events import CalendarEventRepository
from backend.repositories.finance import FinanceRepository
from backend.repositories.law_updates import LawUpdateRepository
from backend.repositories.reminders import ReminderRepository
from backend.repositories.subscriptions import SubscriptionRepository
from backend.repositories.users import BusinessProfileRepository, UserRepository
from backend.services.ai_gateway import AIGateway, build_ai_provider
from backend.services.calendar import CalendarService
from backend.services.document_templates import DocumentTemplateService
from backend.services.documents import DocumentsService
from backend.services.finance import FinanceService, FinanceTextParser
from backend.services.law_updates import LawUpdateService
from backend.services.onboarding import OnboardingService
from backend.services.reminders import ReminderService
from backend.services.subscription import SubscriptionService
from backend.services.tax_engine import TaxCalculatorService


@dataclass
class Services:
    onboarding: OnboardingService
    calendar: CalendarService
    reminders: ReminderService
    laws: LawUpdateService
    finance: FinanceService
    documents: DocumentsService
    ai: AIGateway
    tax: TaxCalculatorService
    templates: DocumentTemplateService
    subscription: SubscriptionService


def build_services(session) -> Services:
    settings = get_settings()
    user_repo = UserRepository(session)
    business_repo = BusinessProfileRepository(session)
    event_repo = CalendarEventRepository(session)
    reminder_repo = ReminderRepository(session)
    law_repo = LawUpdateRepository(session)
    finance_repo = FinanceRepository(session)
    sub_repo = SubscriptionRepository(session)

    ai_provider = build_ai_provider(settings)

    calendar = CalendarService(event_repo)
    return Services(
        onboarding=OnboardingService(user_repo, business_repo),
        calendar=calendar,
        reminders=ReminderService(reminder_repo),
        laws=LawUpdateService(law_repo),
        finance=FinanceService(finance_repo, FinanceTextParser()),
        documents=DocumentsService(calendar),
        ai=AIGateway(ai_provider),
        subscription=SubscriptionService(sub_repo, user_repo, settings),
        tax=TaxCalculatorService(),
        templates=DocumentTemplateService(),
    )
