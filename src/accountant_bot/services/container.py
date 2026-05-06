from dataclasses import dataclass

from accountant_bot.core.config import get_settings
from accountant_bot.repositories.events import CalendarEventRepository
from accountant_bot.repositories.finance import FinanceRepository
from accountant_bot.repositories.law_updates import LawUpdateRepository
from accountant_bot.repositories.reminders import ReminderRepository
from accountant_bot.repositories.subscriptions import SubscriptionRepository
from accountant_bot.repositories.users import BusinessProfileRepository, UserRepository
from accountant_bot.services.ai_gateway import AIGateway, build_ai_provider
from accountant_bot.services.calendar import CalendarService
from accountant_bot.services.document_templates import DocumentTemplateService
from accountant_bot.services.documents import DocumentsService
from accountant_bot.services.finance import FinanceService, FinanceTextParser
from accountant_bot.services.law_updates import LawUpdateService
from accountant_bot.services.onboarding import OnboardingService
from accountant_bot.services.reminders import ReminderService
from accountant_bot.services.subscription import SubscriptionService
from accountant_bot.services.tax_engine import TaxCalculatorService


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
