"""Tests for bot.messages — message text formatters."""

from bot.messages import (
    ai_consult_exit_text,
    ai_consult_welcome_text,
    help_text,
    onboarding_complete_text,
    payment_success_text,
    paywall_text,
    referral_text,
    subscription_status_text,
    welcome_text,
)


def test_welcome_with_name():
    assert "Вася" in welcome_text("Вася")


def test_welcome_default_name():
    assert "друг" in welcome_text()


def test_onboarding_complete():
    assert "Профиль" in onboarding_complete_text()


def test_help():
    text = help_text()
    assert "Что я умею" in text


def test_ai_consult_welcome_free():
    text = ai_consult_welcome_text(3, False)
    assert "3" in text
    assert "бесплатных" in text


def test_ai_consult_welcome_subscribed():
    text = ai_consult_welcome_text(0, True)
    assert "безлимит" in text


def test_ai_consult_exit():
    assert "Консультация завершена" in ai_consult_exit_text()


def test_paywall_zero():
    text = paywall_text(0)
    assert "закончились" in text


def test_paywall_remaining():
    text = paywall_text(2)
    assert "2" in text


def test_subscription_active():
    text = subscription_status_text("Базовый", "2026-07-01", True)
    assert "Базовый" in text
    assert "2026-07-01" in text


def test_subscription_inactive():
    text = subscription_status_text("Бесплатный", "", False)
    assert "Бесплатный" in text
    assert "3 AI-запроса" in text


def test_payment_success():
    text = payment_success_text("Про", "2026-08-01")
    assert "Оплата" in text
    assert "Про" in text


def test_referral():
    text = referral_text("mybot", 123, 5, 15)
    assert "ref_123" in text
    assert "5" in text
    assert "15" in text
