from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="Pocket Accountant Bot", alias="APP_NAME")
    app_base_url: str = Field(default="http://localhost:8080", alias="APP_BASE_URL")
    app_secret_key: str = Field(default="", alias="APP_SECRET_KEY")
    allow_insecure_secret_storage: bool = Field(default=False, alias="ALLOW_INSECURE_SECRET_STORAGE")
    expose_api_docs: bool = Field(default=False, alias="EXPOSE_API_DOCS")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8080, alias="API_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    timezone: str = Field(default="Europe/Moscow", alias="TIMEZONE")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_delivery_mode: str = Field(default="webhook", alias="TELEGRAM_DELIVERY_MODE")
    telegram_webhook_secret: str = Field(default="", alias="TELEGRAM_WEBHOOK_SECRET")
    telegram_webhook_path: str = Field(default="/telegram/webhook", alias="TELEGRAM_WEBHOOK_PATH")
    telegram_webhook_url: str = Field(default="", alias="TELEGRAM_WEBHOOK_URL")
    admin_telegram_ids_raw: str = Field(default="", alias="ADMIN_TELEGRAM_IDS")
    admin_api_token: str = Field(default="", alias="ADMIN_API_TOKEN")
    admin_allowed_ips_raw: str = Field(default="", alias="ADMIN_ALLOWED_IPS")
    admin_tokens_raw: str = Field(default="", alias="ADMIN_TOKENS")
    tester_telegram_ids_raw: str = Field(default="", alias="TESTER_TELEGRAM_IDS")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")

    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="openai/gpt-4.1-nano", alias="OPENROUTER_MODEL")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")
    openrouter_site_url: str = Field(default="", alias="OPENROUTER_SITE_URL")
    openrouter_app_name: str = Field(default="", alias="OPENROUTER_APP_NAME")
    ai_enabled: bool = Field(default=False, alias="AI_ENABLED")
    ai_max_requests_per_minute: int = Field(default=30, alias="AI_MAX_REQUESTS_PER_MINUTE")

    # Subscription / monetization
    free_ai_requests_per_day: int = Field(default=3, alias="FREE_AI_REQUESTS_PER_DAY")
    stars_price_basic: int = Field(default=150, alias="STARS_PRICE_BASIC")
    stars_price_pro: int = Field(default=400, alias="STARS_PRICE_PRO")
    stars_price_annual: int = Field(default=3500, alias="STARS_PRICE_ANNUAL")

    reminder_batch_size: int = Field(default=100, alias="REMINDER_BATCH_SIZE")
    law_min_importance_score: int = Field(default=70, alias="LAW_MIN_IMPORTANCE_SCORE")
    law_fetch_interval_minutes: int = Field(default=60, alias="LAW_FETCH_INTERVAL_MINUTES")
    reminder_dispatch_interval_minutes: int = Field(default=5, alias="REMINDER_DISPATCH_INTERVAL_MINUTES")
    user_event_sync_hour: int = Field(default=3, alias="USER_EVENT_SYNC_HOUR")

    # Ozon
    ozon_api_base_url: str = Field(default="https://api-seller.ozon.ru", alias="OZON_API_BASE_URL")
    ozon_api_timeout_seconds: float = Field(default=30.0, alias="OZON_API_TIMEOUT_SECONDS")
    ozon_ads_api_base_url: str = Field(default="https://api-performance.ozon.ru", alias="OZON_ADS_API_BASE_URL")
    ozon_ads_api_timeout_seconds: float = Field(default=30.0, alias="OZON_ADS_API_TIMEOUT_SECONDS")
    ozon_sync_interval_minutes: int = Field(default=30, alias="OZON_SYNC_INTERVAL_MINUTES")
    ozon_sync_days_back: int = Field(default=30, alias="OZON_SYNC_DAYS_BACK")
    ozon_sync_batch_limit: int = Field(default=20, alias="OZON_SYNC_BATCH_LIMIT")

    # Google Sheets
    google_sheets_enabled: bool = Field(default=False, alias="GOOGLE_SHEETS_ENABLED")
    google_sheets_spreadsheet_id: str = Field(default="", alias="GOOGLE_SHEETS_SPREADSHEET_ID")
    google_service_account_json: str = Field(default="", alias="GOOGLE_SERVICE_ACCOUNT_JSON")

    fns_source_url: str = Field(default="https://www.nalog.gov.ru/", alias="FNS_SOURCE_URL")
    minfin_source_url: str = Field(default="https://minfin.gov.ru/", alias="MINFIN_SOURCE_URL")
    gov_source_url: str = Field(default="https://government.ru/", alias="GOV_SOURCE_URL")
    duma_source_url: str = Field(default="https://sozd.duma.gov.ru/", alias="DUMA_SOURCE_URL")

    @property
    def admin_telegram_ids(self) -> List[int]:
        if not self.admin_telegram_ids_raw.strip():
            return []
        return [int(item.strip()) for item in self.admin_telegram_ids_raw.split(",") if item.strip()]

    @property
    def admin_allowed_ips(self) -> List[str]:
        if not self.admin_allowed_ips_raw.strip():
            return []
        return [item.strip() for item in self.admin_allowed_ips_raw.split(",") if item.strip()]

    @property
    def admin_tokens(self) -> dict:
        if not self.admin_tokens_raw.strip():
            return {}
        items = {}
        for pair in self.admin_tokens_raw.split(","):
            if ":" not in pair:
                continue
            role, token = pair.split(":", 1)
            role = role.strip()
            token = token.strip()
            if role and token:
                items[token] = role
        return items

    @property
    def tester_telegram_ids(self) -> List[int]:
        if not self.tester_telegram_ids_raw.strip():
            return []
        return [int(item.strip()) for item in self.tester_telegram_ids_raw.split(",") if item.strip()]

    @property
    def admin_api_enabled(self) -> bool:
        return bool(self.admin_api_token.strip())

    @property
    def telegram_bot_configured(self) -> bool:
        return bool(self.telegram_bot_token.strip())

    @property
    def telegram_uses_polling(self) -> bool:
        return self.telegram_delivery_mode.strip().lower() == "polling"

    @property
    def telegram_uses_webhook(self) -> bool:
        return not self.telegram_uses_polling

    @property
    def api_docs_enabled(self) -> bool:
        if self.expose_api_docs:
            return True
        return self.app_env.strip().lower() not in {"production", "prod", "staging"}

    @property
    def secret_fallback_allowed(self) -> bool:
        if self.allow_insecure_secret_storage:
            return True
        return self.app_env.strip().lower() in {"development", "dev", "test"}

    @property
    def resolved_llm_provider(self) -> str:
        configured = self.llm_provider.strip().lower()
        if configured and configured != "auto":
            return configured
        if self.openrouter_api_key:
            return "openrouter"
        if self.openai_api_key:
            return "openai"
        return "disabled"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
