"""Tests for shared.config.Settings properties."""

from shared.config import Settings


def _make(overrides: dict) -> Settings:
    base = {
        "DATABASE_URL": "sqlite+aiosqlite:///test.db",
        "REDIS_URL": "redis://localhost:6379/0",
        "EXPOSE_API_DOCS": False,
    }
    base.update(overrides)
    return Settings(**base)


# --- admin_telegram_ids ---


def test_admin_telegram_ids_empty():
    s = _make({"ADMIN_TELEGRAM_IDS": ""})
    assert s.admin_telegram_ids == []


def test_admin_telegram_ids_parses_comma_separated():
    s = _make({"ADMIN_TELEGRAM_IDS": "111, 222,333"})
    assert s.admin_telegram_ids == [111, 222, 333]


# --- admin_allowed_ips ---


def test_admin_allowed_ips_empty():
    s = _make({"ADMIN_ALLOWED_IPS": ""})
    assert s.admin_allowed_ips == []


def test_admin_allowed_ips_parses():
    s = _make({"ADMIN_ALLOWED_IPS": "1.2.3.4, 5.6.7.8"})
    assert s.admin_allowed_ips == ["1.2.3.4", "5.6.7.8"]


# --- admin_tokens ---


def test_admin_tokens_empty():
    s = _make({"ADMIN_TOKENS": ""})
    assert s.admin_tokens == {}


def test_admin_tokens_parses_role_colon_token():
    s = _make({"ADMIN_TOKENS": "admin:tok1, viewer:tok2"})
    assert s.admin_tokens == {"tok1": "admin", "tok2": "viewer"}


def test_admin_tokens_skips_invalid_entries():
    s = _make({"ADMIN_TOKENS": "admin:tok1,bad_no_colon,viewer:tok2"})
    assert s.admin_tokens == {"tok1": "admin", "tok2": "viewer"}


# --- tester_telegram_ids ---


def test_tester_telegram_ids_empty():
    s = _make({"TESTER_TELEGRAM_IDS": ""})
    assert s.tester_telegram_ids == []


def test_tester_telegram_ids_parses():
    s = _make({"TESTER_TELEGRAM_IDS": "100, 200"})
    assert s.tester_telegram_ids == [100, 200]


# --- boolean properties ---


def test_admin_api_enabled_false():
    s = _make({"ADMIN_API_TOKEN": ""})
    assert s.admin_api_enabled is False


def test_admin_api_enabled_true():
    s = _make({"ADMIN_API_TOKEN": "tok"})
    assert s.admin_api_enabled is True


def test_telegram_bot_configured():
    assert _make({"TELEGRAM_BOT_TOKEN": ""}).telegram_bot_configured is False
    assert _make({"TELEGRAM_BOT_TOKEN": "token"}).telegram_bot_configured is True


def test_telegram_uses_polling():
    assert _make({"TELEGRAM_DELIVERY_MODE": "polling"}).telegram_uses_polling is True
    assert _make({"TELEGRAM_DELIVERY_MODE": "webhook"}).telegram_uses_polling is False
    assert _make({"TELEGRAM_DELIVERY_MODE": "webhook"}).telegram_uses_webhook is True


def test_api_docs_enabled_by_flag():
    s = _make({"EXPOSE_API_DOCS": True, "APP_ENV": "production"})
    assert s.api_docs_enabled is True


def test_api_docs_enabled_by_env():
    s = _make({"APP_ENV": "development"})
    assert s.api_docs_enabled is True
    s2 = _make({"APP_ENV": "production"})
    assert s2.api_docs_enabled is False


def test_secret_fallback_allowed_by_flag():
    s = _make({"ALLOW_INSECURE_SECRET_STORAGE": True, "APP_ENV": "production"})
    assert s.secret_fallback_allowed is True


def test_secret_fallback_allowed_by_dev_env():
    s = _make({"APP_ENV": "development"})
    assert s.secret_fallback_allowed is True
    s2 = _make({"APP_ENV": "production"})
    assert s2.secret_fallback_allowed is False


# --- resolved_llm_provider ---


def test_resolved_llm_provider_explicit():
    s = _make({"LLM_PROVIDER": "openai"})
    assert s.resolved_llm_provider == "openai"


def test_resolved_llm_provider_auto_openrouter():
    s = _make({"LLM_PROVIDER": "auto", "OPENROUTER_API_KEY": "key"})
    assert s.resolved_llm_provider == "openrouter"


def test_resolved_llm_provider_auto_openai():
    s = _make({"LLM_PROVIDER": "auto", "OPENAI_API_KEY": "key"})
    assert s.resolved_llm_provider == "openai"


def test_resolved_llm_provider_auto_disabled():
    s = _make({"LLM_PROVIDER": "auto"})
    assert s.resolved_llm_provider == "disabled"
