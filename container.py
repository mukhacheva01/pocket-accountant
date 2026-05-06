from dataclasses import dataclass

from accountant_bot.core.config import get_settings
from accountant_bot.core.secrets import SecretBox
from accountant_bot.repositories.events import CalendarEventRepository
from accountant_bot.repositories.finance import FinanceRepository
from accountant_bot.repositories.law_updates import LawUpdateRepository
from accountant_bot.repositories.marketplace_connections import MarketplaceConnectionRepository
from accountant_bot.repositories.ozon_data import OzonDataRepository
from accountant_bot.repositories.ozon_insights import OzonInsightsRepository
from accountant_bot.repositories.reminders import ReminderRepository
from accountant_bot.repositories.users import BusinessProfileRepository, UserRepository
from accountant_bot.services.ai_gateway import AIGateway, build_ai_provider
from accountant_bot.services.calendar import CalendarService
from accountant_bot.services.document_templates import DocumentTemplateService
from accountant_bot.services.documents import DocumentsService
from accountant_bot.services.finance import FinanceService, FinanceTextParser
from accountant_bot.services.google_sheets_export import GoogleSheetsExportService
from accountant_bot.services.law_updates import LawUpdateService
from accountant_bot.services.marketplace_connections import MarketplaceConnectionService
from accountant_bot.services.onboarding import OnboardingService
from accountant_bot.services.ozon_content import OzonContentService
from accountant_bot.services.ozon_feedback import OzonFeedbackService
from accountant_bot.services.ozon_insights import OzonInsightsService
from accountant_bot.services.ozon_sync import OzonSyncService
from accountant_bot.services.reminders import ReminderService
from accountant_bot.services.tax_engine import TaxCalculatorService
from accountant_bot.integrations.ozon_performance import OzonPerformanceClient
from accountant_bot.integrations.ozon_seller import OzonSellerClient


@dataclass
class Services:
    onboarding: OnboardingService
    marketplace_connections: MarketplaceConnectionService
    ozon_sync: OzonSyncService
    ozon_insights: OzonInsightsService
    ozon_content: OzonContentService
    ozon_feedback: OzonFeedbackService
    calendar: CalendarService
    reminders: ReminderService
    laws: LawUpdateService
    finance: FinanceService
    documents: DocumentsService
    google_sheets: GoogleSheetsExportService
    ai: AIGateway
    tax: TaxCalculatorService
    templates: DocumentTemplateService
def build_services(session) -> Services:
    settings = get_settings()
    user_repo = UserRepository(session)
    business_repo = BusinessProfileRepository(session)
    marketplace_repo = MarketplaceConnectionRepository(session)
    ozon_data_repo = OzonDataRepository(session)
    ozon_insights_repo = OzonInsightsRepository(session)
    event_repo = CalendarEventRepository(session)
    reminder_repo = ReminderRepository(session)
    law_repo = LawUpdateRepository(session)
    finance_repo = FinanceRepository(session)

    ai_gateway = AIGateway(build_ai_provider(settings))

    calendar = CalendarService(event_repo)
    secret_box = SecretBox(
        settings.app_secret_key,
        allow_insecure_fallback=settings.secret_fallback_allowed,
    )
    ozon_client = OzonSellerClient(
        base_url=settings.ozon_api_base_url,
        timeout=settings.ozon_api_timeout_seconds,
    )
    performance_client = OzonPerformanceClient(
        base_url=settings.ozon_ads_api_base_url,
        timeout=settings.ozon_ads_api_timeout_seconds,
    )
    google_sheets = GoogleSheetsExportService(
        enabled=settings.google_sheets_enabled,
        spreadsheet_id=settings.google_sheets_spreadsheet_id,
        service_account_json=settings.google_service_account_json,
    )
    return Services(
        onboarding=OnboardingService(user_repo, business_repo),
        marketplace_connections=MarketplaceConnectionService(marketplace_repo, secret_box),
        ozon_sync=OzonSyncService(
            marketplace_repo,
            ozon_data_repo,
            ozon_client,
            performance_client,
            secret_box,
            days_back=settings.ozon_sync_days_back,
        ),
        ozon_insights=OzonInsightsService(ozon_insights_repo),
        ozon_content=OzonContentService(ai_gateway),
        ozon_feedback=OzonFeedbackService(
            marketplace_repo,
            ozon_insights_repo,
            ozon_client,
            secret_box,
        ),
        calendar=calendar,
        reminders=ReminderService(reminder_repo),
        laws=LawUpdateService(law_repo),
        finance=FinanceService(finance_repo, FinanceTextParser()),
        documents=DocumentsService(calendar),
        google_sheets=google_sheets,
        ai=ai_gateway,
        tax=TaxCalculatorService(),
        templates=DocumentTemplateService(),
    )
